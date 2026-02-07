"""Tests for wallabag_to_karakeep.cli."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from wallabag_to_karakeep.cli import app

runner = CliRunner()


class TestConvertCommand:
    """Tests for the 'convert' CLI command."""

    def test_convert_omnivore(self, tmp_wallabag_json: Path, tmp_path: Path) -> None:
        """Convert wallabag JSON to Omnivore format."""
        output = tmp_path / "output.json"
        result = runner.invoke(
            app,
            [
                "convert",
                "--input",
                str(tmp_wallabag_json),
                "--output",
                str(output),
                "--format",
                "omnivore",
            ],
        )
        assert result.exit_code == 0, result.output
        assert output.exists()
        data = json.loads(output.read_text())
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["url"] == "https://docs.docker.com/compose/gettingstarted/"
        assert data[0]["state"] == "Archived"
        assert "docker" in data[0]["labels"]

    def test_convert_api_json(self, tmp_wallabag_json: Path, tmp_path: Path) -> None:
        """Convert wallabag JSON to API JSON format."""
        output = tmp_path / "api_output.json"
        result = runner.invoke(
            app,
            [
                "convert",
                "--input",
                str(tmp_wallabag_json),
                "--output",
                str(output),
                "--format",
                "api-json",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(output.read_text())
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["type"] == "link"
        assert data[0]["source"] == "import"

    def test_convert_dry_run(self, tmp_wallabag_json: Path, tmp_path: Path) -> None:
        """Dry-run mode does not write output file."""
        output = tmp_path / "should_not_exist.json"
        result = runner.invoke(
            app,
            [
                "convert",
                "--input",
                str(tmp_wallabag_json),
                "--output",
                str(output),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        assert not output.exists()

    def test_convert_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent input file produces error."""
        result = runner.invoke(
            app,
            [
                "convert",
                "--input",
                str(tmp_path / "nope.json"),
                "--output",
                str(tmp_path / "out.json"),
            ],
        )
        assert result.exit_code == 1

    def test_convert_with_dedup(self, tmp_path: Path) -> None:
        """Duplicate URLs are deduplicated."""
        entries = [
            {
                "url": "https://example.com/same",
                "is_archived": 0,
                "is_starred": 0,
                "created_at": "2025-01-01 00:00:00",
                "tags": [],
            },
            {
                "url": "https://example.com/same",
                "is_archived": 1,
                "is_starred": 0,
                "created_at": "2025-01-02 00:00:00",
                "tags": [],
            },
        ]
        input_file = tmp_path / "dupes.json"
        input_file.write_text(json.dumps(entries))
        output = tmp_path / "deduped.json"
        result = runner.invoke(
            app,
            [
                "convert",
                "--input",
                str(input_file),
                "--output",
                str(output),
                "--dedup",
                "url",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(output.read_text())
        assert len(data) == 1

    def test_convert_wrapped_json(
        self, tmp_wallabag_wrapped_json: Path, tmp_path: Path
    ) -> None:
        """Accept {entries: [...]} wrapper format."""
        output = tmp_path / "wrapped_output.json"
        result = runner.invoke(
            app,
            [
                "convert",
                "--input",
                str(tmp_wallabag_wrapped_json),
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(output.read_text())
        assert len(data) == 1


class TestValidateCommand:
    """Tests for the 'validate' CLI command."""

    def test_validate_valid_file(self, tmp_wallabag_json: Path) -> None:
        """Valid file reports entry counts."""
        result = runner.invoke(
            app,
            ["validate", "--input", str(tmp_wallabag_json)],
        )
        assert result.exit_code == 0, result.output
        assert "Total entries" in result.output

    def test_validate_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent file produces error exit."""
        result = runner.invoke(
            app,
            ["validate", "--input", str(tmp_path / "missing.json")],
        )
        assert result.exit_code == 1

    def test_validate_entries_with_missing_urls(self, tmp_path: Path) -> None:
        """Entries with missing URLs are flagged."""
        entries = [
            {
                "url": None,
                "is_archived": 0,
                "is_starred": 0,
                "tags": [],
            },
            {
                "url": "https://example.com",
                "is_archived": 0,
                "is_starred": 0,
                "tags": [],
            },
        ]
        input_file = tmp_path / "partial.json"
        input_file.write_text(json.dumps(entries))
        result = runner.invoke(
            app,
            ["validate", "--input", str(input_file)],
        )
        assert result.exit_code == 0
        assert "Warning" in result.output or "1" in result.output
