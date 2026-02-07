# wallabag-to-karakeep

Convert [Wallabag](https://wallabag.org) JSON exports into [Karakeep](https://github.com/karakeep-app/karakeep)-compatible formats.

Supports two output formats:

- **Omnivore JSON** -- for import via the Karakeep web UI
- **Karakeep API JSON** -- for direct push via the Karakeep REST API

Features include URL-based deduplication, tag processing (preserve / lowercase / strip), annotation-to-note conversion, and dry-run mode.

## Quickstart

### Prerequisites

Set the Python version with [asdf](https://asdf-vm.com):

```bash
asdf plugin add python
asdf plugin add uv
asdf install       # installs Python 3.12 from .tool-versions
```

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

### Usage

The CLI is exposed as `wallabag2karakeep`. Run it through `uv run`:

```bash
# Validate an export file
uv run wallabag2karakeep validate -i wallabag-export.json

# Convert to Omnivore format (default)
uv run wallabag2karakeep convert -i wallabag-export.json -o output.json

# Convert to Karakeep API format
uv run wallabag2karakeep convert -i wallabag-export.json -o output.json -f api-json

# Dry run -- preview without writing
uv run wallabag2karakeep convert -i wallabag-export.json -o output.json --dry-run -v
```

### Options

| Flag | Description | Default |
|---|---|---|
| `-f`, `--format` | Output format: `omnivore` or `api-json` | `omnivore` |
| `--dedup` | Dedup mode: `url`, `wallabag-id`, or `none` | `url` |
| `--tags-mode` | Tag handling: `preserve`, `lowercase`, or `strip` | `preserve` |
| `--include-notes / --no-notes` | Include annotations as notes (api-json only) | `--include-notes` |
| `--max-note-length` | Truncate notes beyond this length | `5000` |
| `--dry-run` | Show conversion plan without writing output | off |
| `-v` | Increase verbosity (`-vv` for debug) | warning |

## License

MIT
