"""CLI interface for wallabag-to-karakeep converter.

Uses Typer for argument parsing and Rich for progress output.
Provides ``convert`` (default) and ``validate`` commands.
"""

from __future__ import annotations

import json
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from wallabag_to_karakeep.converter import (
    convert_to_api,
    convert_to_omnivore,
)
from wallabag_to_karakeep.io import (
    deduplicate_entries,
    read_wallabag_json,
    write_json,
)

app = typer.Typer(
    name="wallabag2karakeep",
    help="Convert Wallabag JSON exports to Karakeep import formats.",
    add_completion=False,
)
console = Console(stderr=True)

logger = logging.getLogger("wallabag_to_karakeep")


# ---------------------------------------------------------------------------
# Enums for CLI options
# ---------------------------------------------------------------------------


class OutputFormat(str, Enum):
    """Supported output formats."""

    omnivore = "omnivore"
    api_json = "api-json"


class DedupMode(str, Enum):
    """Deduplication strategies."""

    url = "url"
    none = "none"
    wallabag_id = "wallabag-id"


class TagsMode(str, Enum):
    """Tag processing modes."""

    preserve = "preserve"
    lowercase = "lowercase"
    strip_all = "strip"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_logging(verbose: int) -> None:
    """Set up logging based on verbosity level."""
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def convert(
    input_file: Annotated[
        Path,
        typer.Option("--input", "-i", help="Input wallabag JSON file."),
    ],
    output_file: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file path."),
    ],
    fmt: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format."),
    ] = OutputFormat.omnivore,
    dedup: Annotated[
        DedupMode,
        typer.Option("--dedup", help="Deduplication mode."),
    ] = DedupMode.url,
    tags_mode: Annotated[
        TagsMode,
        typer.Option("--tags-mode", help="Tag processing mode."),
    ] = TagsMode.preserve,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show plan without writing output."),
    ] = False,
    include_notes: Annotated[
        bool,
        typer.Option(
            "--include-notes/--no-notes",
            help="Include annotations and metadata as notes.",
        ),
    ] = True,
    max_note_length: Annotated[
        int,
        typer.Option("--max-note-length", help="Maximum note length."),
    ] = 5000,
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True, help="Increase verbosity."),
    ] = 0,
) -> None:
    """Convert a wallabag JSON export to a Karakeep-compatible format."""
    _configure_logging(verbose)

    # --- Read ---
    if not input_file.exists():
        console.print(f"[red]Error:[/red] File not found: {input_file}")
        raise typer.Exit(code=1)

    try:
        entries = read_wallabag_json(input_file)
    except (json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] Failed to read input: {exc}")
        raise typer.Exit(code=1)  # noqa: B904

    console.print(f"Read [bold]{len(entries)}[/bold] entries from {input_file}")

    # --- Deduplicate ---
    entries = deduplicate_entries(entries, mode=dedup.value)
    console.print(
        f"After dedup ([bold]{dedup.value}[/bold]): "
        f"[bold]{len(entries)}[/bold] entries"
    )

    # --- Convert ---
    skipped = 0
    output_items: list[dict[str, object]] = []

    if fmt == OutputFormat.omnivore:
        for entry in entries:
            result = convert_to_omnivore(entry, tags_mode=tags_mode.value)
            if result is None:
                skipped += 1
                logger.warning(
                    "Skipped entry id=%s (invalid URL: %s)",
                    entry.id,
                    entry.url,
                )
                continue
            output_items.append(result.model_dump())

    elif fmt == OutputFormat.api_json:
        for entry in entries:
            result_pair = convert_to_api(
                entry,
                tags_mode=tags_mode.value,
                include_notes=include_notes,
                max_note_length=max_note_length,
            )
            if result_pair is None:
                skipped += 1
                logger.warning(
                    "Skipped entry id=%s (invalid URL: %s)",
                    entry.id,
                    entry.url,
                )
                continue
            bookmark_req, tag_req = result_pair
            item: dict[str, object] = bookmark_req.model_dump(exclude_none=True)
            if tag_req:
                item["_tags"] = tag_req.model_dump()
            output_items.append(item)

    console.print(
        f"Converted: [bold green]{len(output_items)}[/bold green]  "
        f"Skipped: [bold yellow]{skipped}[/bold yellow]"
    )

    # --- Write ---
    if dry_run:
        console.print("[yellow]Dry-run mode:[/yellow] no output written.")
        if verbose >= 1 and output_items:
            console.print_json(json.dumps(output_items[:3], default=str))
    else:
        write_json(output_items, output_file)
        console.print(f"Written to [bold]{output_file}[/bold]")


@app.command()
def validate(
    input_file: Annotated[
        Path,
        typer.Option("--input", "-i", help="Input wallabag JSON file."),
    ],
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True, help="Increase verbosity."),
    ] = 0,
) -> None:
    """Validate a wallabag JSON export file.

    Reports the number of valid and invalid entries without producing
    any output file.
    """
    _configure_logging(verbose)

    if not input_file.exists():
        console.print(f"[red]Error:[/red] File not found: {input_file}")
        raise typer.Exit(code=1)

    try:
        entries = read_wallabag_json(input_file)
    except (json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] Failed to read input: {exc}")
        raise typer.Exit(code=1)  # noqa: B904

    # Build summary
    valid_urls = sum(1 for e in entries if e.url)
    with_tags = sum(1 for e in entries if e.tags)
    with_annotations = sum(1 for e in entries if e.annotations)
    archived = sum(1 for e in entries if e.is_archived)
    starred = sum(1 for e in entries if e.is_starred)

    table = Table(title="Wallabag Export Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Total entries", str(len(entries)))
    table.add_row("Valid URLs", str(valid_urls))
    table.add_row("With tags", str(with_tags))
    table.add_row("With annotations", str(with_annotations))
    table.add_row("Archived", str(archived))
    table.add_row("Starred", str(starred))
    console.print(table)

    if len(entries) > 0 and valid_urls == len(entries):
        console.print("[green]All entries are valid.[/green]")
    elif valid_urls < len(entries):
        console.print(
            f"[yellow]Warning:[/yellow] {len(entries) - valid_urls} "
            "entries have missing or empty URLs."
        )


if __name__ == "__main__":
    app()
