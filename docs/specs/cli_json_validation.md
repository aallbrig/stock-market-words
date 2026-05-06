# CLI: JSON Schema Validation in the Test Suite

**Status:** Draft
**Author:** Andrew Allbright
**Created:** 2026-05-05
**Supersedes:** —
**Superseded by:** —
**ADR:** [`docs/design/20260505_234505_UTC_adr_cli_json_schema_requirement.md`](../design/20260505_234505_UTC_adr_cli_json_schema_requirement.md)

## Context

The ADR establishing the schema requirement ends with an explicit call-out:
_"The CI validation step is not yet implemented. That is the highest-priority follow-on from this decision."_

We have eight JSON schemas in `hugo/site/static/schemas/` and two integration test files that
already run the generators against a real test DB:

- `python3/tests/test_hugo_generators.py` — runs `generate_raw_ftp_data()`,
  `generate_filtered_data()`, `generate_strategy_filters()`
- `python3/tests/test_builders.py` — runs `build_assets()`

Both test files stop at loose checks like `assert isinstance(data, dict)` or
`if nasdaq_file.exists():`. A future agent can rename a field, change a type, drop a required
key, or add `additionalProperties` in violation of the schema and every existing test will still
pass. The Hugo build or browser JavaScript will be the first thing to break — after a deploy.

The goal of this spec is to close that gap: run the generators and validate their output against
the committed schemas, inside pytest, so that any breaking change to a generator is caught
before it merges.

## Goal

Running `pytest` after a change to `hugo_generators.py` or `builders.py` fails with a clear
schema violation message if the generated JSON no longer matches what the website expects.

## Non-goals

- A new `ticker-cli validate` CLI command. The primary enforcement mechanism is the test suite,
  not a command someone has to remember to run.
- Validating hand-authored JSON (e.g., `static/schemas/models/navigation.json`).
- Deep semantic cross-field checks (e.g., `week52Low ≤ week52High`). Those are data-quality
  assertions; JSON Schema handles type and structure.
- Changing the generators themselves. This spec only touches test infrastructure.
- Validating the duplicate copies in `hugo/site/static/data/` — they're written by the same
  `json.dump` call as the `data/` copies.

## User stories

- **As a future agent** editing `hugo_generators.py`, I want `pytest` to fail with a message
  like `$.tickers[0].scores.dividendDaddy: 'high' is not of type 'integer'` so I immediately
  know which field I broke and in which file.
- **As the CI pipeline**, I want schema validation to happen automatically on every push so a
  broken data contract never reaches the Hugo build.
- **As a developer adding a new generator**, I want a clear pattern to follow: run generator →
  load output → call `assert_conforms_to_schema(data, schema_path)` — one line in the test.

## Design

### New test helper: `assert_conforms_to_schema` in `conftest.py`

**File:** `python3/tests/conftest.py`

Add one new helper function alongside the existing `assert_valid_json_file` and
`assert_json_structure`:

```python
import jsonschema
from jsonschema import Draft7Validator

SCHEMAS_DIR = Path(__file__).parents[2] / "hugo" / "site" / "static" / "schemas"

def assert_conforms_to_schema(data: dict | list, schema_filename: str) -> None:
    """
    Validate `data` against the committed schema at
    hugo/site/static/schemas/<schema_filename>.
    Raises AssertionError with all violations listed if validation fails.
    """
    schema_path = SCHEMAS_DIR / schema_filename
    assert schema_path.exists(), f"Schema not found: {schema_path}"

    with open(schema_path) as f:
        schema = json.load(f)

    validator = Draft7Validator(schema, format_checker=Draft7Validator.FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if errors:
        lines = [f"  {'.'.join(str(p) for p in e.path) or '$'}: {e.message}" for e in errors[:20]]
        if len(errors) > 20:
            lines.append(f"  ... and {len(errors) - 20} more errors")
        raise AssertionError(
            f"{len(errors)} schema violation(s) in '{schema_filename}':\n" + "\n".join(lines)
        )
```

The helper is intentionally thin — no discovery, no file I/O. The test calls the generator,
loads the output file, passes the parsed data to `assert_conforms_to_schema`. The test controls
what gets validated; the helper just does the assertion.

### Updates to `test_hugo_generators.py`

**File:** `python3/tests/test_hugo_generators.py`

Replace the loose `isinstance` checks in the four existing integration tests with
`assert_conforms_to_schema` calls. The generator invocations stay the same — only the
assertions change.

#### `test_generate_raw_ftp_data_creates_valid_json`

```python
nasdaq_file = output_dir / "raw_nasdaq.json"
other_file  = output_dir / "raw_otherlisted.json"

assert nasdaq_file.exists()
assert other_file.exists()

with open(nasdaq_file) as f:
    assert_conforms_to_schema(json.load(f), "raw_ftp.schema.json")
with open(other_file) as f:
    assert_conforms_to_schema(json.load(f), "raw_ftp.schema.json")
```

#### `test_generate_filtered_data_creates_valid_json`

```python
filtered_file = output_dir / "filtered_tickers.json"
pass1_file    = output_dir / "pass1_results.json"

assert filtered_file.exists()
assert pass1_file.exists()

with open(filtered_file) as f:
    assert_conforms_to_schema(json.load(f), "filtered_tickers.schema.json")
with open(pass1_file) as f:
    assert_conforms_to_schema(json.load(f), "pass1_results.schema.json")
```

#### `test_generate_strategy_filters_creates_valid_json`

```python
strategies = [
    "dividend_daddy", "moon_shot", "falling_knife",
    "over_hyped", "institutional_whale", "reit_radar",
]
for strategy in strategies:
    strategy_file = output_dir / f"strategy_{strategy}.json"
    assert strategy_file.exists(), f"Missing: strategy_{strategy}.json"
    with open(strategy_file) as f:
        assert_conforms_to_schema(json.load(f), "strategy.schema.json")
```

#### Add `test_generate_all_tickers_json_conforms_to_schema` (new test)

`generate_all_tickers_json` is not currently tested in integration. Add it:

```python
def test_generate_all_tickers_json_conforms_to_schema(self, populated_db,
                                                       temp_hugo_dir, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(populated_db))
    generate_all_tickers_json(db_path=populated_db, output_dir=temp_hugo_dir)

    output = temp_hugo_dir / "all_tickers.json"
    assert output.exists()
    with open(output) as f:
        assert_conforms_to_schema(json.load(f), "all_tickers.schema.json")
```

### Updates to `test_builders.py`

**File:** `python3/tests/test_builders.py`

Replace the `if trie_path.exists():` guards (which silently skip on missing files) with hard
`assert` + schema validation:

```python
def test_build_assets_with_sample_data(self, populated_db, temp_dir, monkeypatch):
    api_dir = temp_dir / "api"
    api_dir.mkdir(parents=True)
    monkeypatch.setenv('DB_PATH', str(populated_db))
    monkeypatch.setenv('API_DIR', str(api_dir))

    build_assets(db_path=populated_db, output_dir=api_dir)

    trie_path     = api_dir / "trie.json"
    metadata_path = api_dir / "metadata.json"

    assert trie_path.exists(),     "build_assets did not produce trie.json"
    assert metadata_path.exists(), "build_assets did not produce metadata.json"

    with open(trie_path) as f:
        assert_conforms_to_schema(json.load(f), "trie.schema.json")
    with open(metadata_path) as f:
        assert_conforms_to_schema(json.load(f), "metadata.schema.json")
```

### New test: `test_generate_ticker_lookup_json_conforms_to_schema`

`generate_ticker_lookup_json` is also not yet integration-tested. Add it alongside the others in
`test_hugo_generators.py`:

```python
def test_generate_ticker_lookup_json_conforms_to_schema(self, populated_db,
                                                         temp_hugo_dir, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(populated_db))
    generate_ticker_lookup_json(db_path=populated_db, output_dir=temp_hugo_dir)

    output = temp_hugo_dir / "ticker-lookup.json"
    assert output.exists()
    with open(output) as f:
        assert_conforms_to_schema(json.load(f), "ticker_lookup.schema.json")
```

### Dependency

Add `jsonschema>=4.23` to `python3/requirements.txt`. This is a test-time dependency only;
nothing in the production path imports it. `jsonschema` 4.x ships `Draft7Validator` and the
`format` checker needed for `"format": "date"` and `"format": "date-time"` fields in the
schemas.

## Affected files

| File | Change |
|---|---|
| `python3/tests/conftest.py` | Add `assert_conforms_to_schema` helper + `SCHEMAS_DIR` constant |
| `python3/tests/test_hugo_generators.py` | Replace loose `isinstance` checks with schema assertions; add two new integration tests |
| `python3/tests/test_builders.py` | Replace `if file.exists():` guards with hard asserts + schema assertions |
| `python3/requirements.txt` | Add `jsonschema>=4.23` |
| `docs/specs/README.md` | Add this spec to the existing specs list |

## Verification

- **Regression catch:** Temporarily rename `dividendDaddy` to `dividend_daddy` in
  `generate_strategy_filters()`. Run `pytest python3/tests/test_hugo_generators.py`. Confirm
  it fails with a message naming `dividendDaddy` as the missing required property and
  `dividend_daddy` as an unexpected additional property.
- **Green on clean run:** After `ticker-cli run-all` with no changes, `pytest python3/tests/`
  exits 0.
- **Missing file caught:** Remove the `assert output.exists()` guard temporarily and confirm
  that if `build_assets` fails silently, the test now fails with `"build_assets did not produce
  trie.json"` rather than silently passing.
- **Schema path resolution:** Confirm `SCHEMAS_DIR` resolves to the correct absolute path
  regardless of what directory pytest is invoked from.

## Open questions

1. **`conftest.py` imports `jsonschema` at module level.** If the package isn't installed the
   entire test suite will fail to collect. Default: add `jsonschema` to `requirements.txt` so
   it's always present in the test environment. A conditional import would mask the missing dep
   rather than surface it clearly.

2. **The `format` checker.** Draft-07's `format` keyword is advisory unless explicitly enabled.
   With the checker on, a `"format": "date"` field containing `"2026-13-99"` fails. Default:
   enable it. If a generator emits a datetime string in a valid-but-unusual ISO 8601 form that
   the checker rejects, relax that specific schema field rather than disabling the checker.

3. **Error cap.** The helper caps at 20 errors per call. On a large file like `all_tickers.json`
   a systematic bug (e.g., a type change on every ticker) will produce 3,000+ errors. The cap
   makes the failure message readable. Default: 20. Revisit if the truncation hides the root
   cause in practice.
