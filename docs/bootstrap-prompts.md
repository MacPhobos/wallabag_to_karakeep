
# ChatGPT prompt

```
I want to create a python tool which will process links exported as json from wallabag into a json format usable for importing these links into karakeep. Provide a research prompt usable by claude code to analyze this problem 
```

5.2 Thinking model returned:

```
You are Claude Code running in a repo workspace. Your task is to research and design a Python conversion tool:

Goal:
Convert links exported from Wallabag (JSON export) into a JSON format that Karakeep can import.

Deliverables (must produce all of these):
1) Input analysis:
   - Identify the Wallabag JSON export structure(s) and fields commonly present (e.g., url, title, content, tags, created_at, archived/starred, annotations, reading time, language, domain, preview image, etc.).
   - Enumerate which fields are essential vs optional, and what’s missing/unstable across versions.
   - Provide at least 2–3 representative sample input objects (synthetic is fine) that match Wallabag export.

2) Output analysis:
   - Identify Karakeep’s expected import JSON schema/format (what top-level keys, what per-item fields, tags structure, timestamps, status flags).
   - If Karakeep supports multiple import formats (e.g., “bookmarks”, “items”, “entries”), list them and pick the best match for Wallabag data.
   - Provide 2–3 representative sample output objects.

3) Mapping spec:
   - Provide a field-by-field mapping table: Wallabag -> Karakeep, including transforms.
   - Explicitly define how to handle:
     * tags (array vs string; dedup; casing; whitespace)
     * timestamps (timezone, parsing, formatting)
     * archival/read status, favorites/stars
     * content/fulltext vs excerpt/summary
     * images (cover image / preview image / favicon)
     * duplicates (same URL multiple times)
     * invalid URLs
     * HTML content sanitization (if needed)
     * character encodings

4) Tool design:
   - Propose a minimal CLI interface, e.g.:
       wallabag2karakeep --in wallabag.json --out karakeep.json [--dedup] [--tags-mode ...] [--dry-run] [--verbose]
   - Propose a project structure and key modules/classes.
   - Use Python 3.12+; prefer pydantic v2 for validation; include robust error reporting.

5) Implementation plan:
   - Outline the steps to implement, test, and validate against real exports.
   - Include a unit test plan with fixtures for 3 input edge cases and expected output.

6) Provide code skeleton:
   - Generate a working skeleton with:
     * dataclasses/pydantic models for input and output
     * mapping/transform functions
     * CLI entrypoint (argparse or typer)
     * JSON read/write with UTF-8
     * logging

Research constraints:
- Do NOT guess Karakeep’s import schema. If you don’t know it, you must look it up from authoritative sources:
  * Karakeep official docs
  * Karakeep GitHub repo (import code paths / examples)
  * Issues/PRs discussing import formats
- Similarly, confirm Wallabag export JSON structure using Wallabag docs or code.
- Capture citations by pasting short quoted snippets (<= 25 words each) and file paths/URLs you found them in, to justify schema claims.
- If sources disagree, explain and pick the most likely supported current format.

Execution instructions:
- Start by locating and summarizing authoritative docs for both Wallabag JSON export and Karakeep import.
- Then produce the mapping spec, samples, and skeleton.
- Make your output a single markdown document named:
  docs/research/wallabag_to_karakeep_import.md
- Also generate a starter package under:
  wallabag2karakeep/
  with a pyproject.toml (uv-friendly), and a minimal runnable CLI.

Important:
- The goal is a converter that is resilient to slight schema variations. Prefer permissive parsing for input and strict schema for output.

```

# Use claude-mpm to bootstrap a basic project

```
bootstrap a basic python project using python 3.12, asdf, uv
```


