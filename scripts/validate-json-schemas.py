#!/usr/bin/env python3
"""Validate staged generated-JSON files against their JSON Schema definitions.

Run by the pre-commit hook. Exits 0 if all staged files pass (or no relevant
files are staged). Exits 1 on first schema violation.
"""
import fnmatch
import json
import os
import subprocess
import sys
import time

try:
    import jsonschema
except ImportError:
    print("[schema-check] WARNING: jsonschema not installed — skipping validation.")
    print("  Install it: python3/venv/bin/pip install jsonschema>=4.0")
    sys.exit(0)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(REPO_ROOT, "hugo", "site", "static", "schemas")

# Map filename patterns (fnmatch style, basename only) to schema filenames.
SCHEMA_MAP = [
    ("all_tickers.json",       "all_tickers.schema.json"),
    ("filtered_tickers.json",  "filtered_tickers.schema.json"),
    ("pass1_results.json",     "pass1_results.schema.json"),
    ("raw_nasdaq.json",        "raw_ftp.schema.json"),
    ("raw_otherlisted.json",   "raw_ftp.schema.json"),
    ("strategy_*.json",        "strategy.schema.json"),
    ("ticker-lookup.json",     "ticker_lookup.schema.json"),
    ("metadata.json",          "metadata.schema.json"),
    ("trie.json",              "trie.schema.json"),
]


def schema_for(basename: str) -> str | None:
    for pattern, schema_file in SCHEMA_MAP:
        if fnmatch.fnmatch(basename, pattern):
            return schema_file
    return None


def staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=True,
    )
    return [p.strip() for p in result.stdout.splitlines() if p.strip()]


def main() -> int:
    files = staged_files()
    to_validate = [(f, schema_for(os.path.basename(f))) for f in files]
    to_validate = [(f, s) for f, s in to_validate if s is not None]

    if not to_validate:
        return 0

    schemas: dict[str, dict] = {}
    errors = 0

    for rel_path, schema_name in to_validate:
        abs_path = os.path.join(REPO_ROOT, rel_path)
        if not os.path.exists(abs_path):
            continue

        if schema_name not in schemas:
            schema_path = os.path.join(SCHEMA_DIR, schema_name)
            if not os.path.exists(schema_path):
                print(f"[schema-check] WARNING: schema not found: {schema_path} — skipping {rel_path}")
                continue
            with open(schema_path) as f:
                schemas[schema_name] = json.load(f)

        schema = schemas[schema_name]
        print(f"[schema-check] Validating {rel_path} ...", end=" ", flush=True)
        t0 = time.monotonic()

        try:
            with open(abs_path) as f:
                data = json.load(f)
            jsonschema.validate(instance=data, schema=schema)
            elapsed = time.monotonic() - t0
            print(f"OK ({elapsed:.1f}s)")
        except json.JSONDecodeError as e:
            print(f"FAIL\n  Invalid JSON: {e}")
            errors += 1
        except jsonschema.ValidationError as e:
            elapsed = time.monotonic() - t0
            path = " > ".join(str(p) for p in e.absolute_path) or "(root)"
            print(f"FAIL ({elapsed:.1f}s)")
            print(f"  Schema: {schema_name}")
            print(f"  Path:   {path}")
            print(f"  Error:  {e.message}")
            errors += 1

    if errors:
        print(f"\n[schema-check] {errors} file(s) failed schema validation. Commit blocked.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
