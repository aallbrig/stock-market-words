# CLI: `ticker-cli translate` subcommand

**Status:** In progress
**Author:** Andrew Allbright
**Created:** 2026-04-09
**Supersedes:** The `ticker-cli translate` section of [`zhcn_content_backfill.md`](zhcn_content_backfill.md) (that spec's inventory and system prompt sections remain canonical; this spec governs command design, parallelism, and job tracking)

---

## Context

`zhcn_content_backfill.md` identified ~28 English markdown files that need
Simplified Chinese siblings. The backfill spec sketched a `ticker-cli translate`
command but left its parallelism model, job-tracking schema, and performance
characteristics unresolved. Running translations sequentially on a single
Ollama worker would take 2–12 hours depending on hardware — an unacceptable
operator experience. This spec designs the full command: a parallel,
hardware-aware translation job system with SQLite-backed heuristics so
operators can predict and control runtime cost.

Related:

- [`docs/specs/zhcn_content_backfill.md`](zhcn_content_backfill.md) — source inventory, system prompt, frontmatter rules, review workflow
- [`docs/design/20260408_013203_UTC_i18n_architecture.md`](../design/20260408_013203_UTC_i18n_architecture.md) — Hugo multilingual conventions

---

## Goal

`ticker-cli translate` completes a full translation run of all untranslated
content files in the minimum wall-clock time the available hardware supports,
while remaining safe to run on a developer machine without destroying it —
and prints a reliable ETA before doing any work.

---

## Non-goals

- Translating ticker detail pages (separate spec: `zhcn_ticker_pages.md`).
- Auto-committing translated files. Human review before commit is required.
- Building a translation memory or glossary cache (v2 idea).
- Supporting paid APIs (OpenAI, DeepL). Local LLM only.
- Adding languages other than zh-CN in this iteration (but the design must
  accommodate them without code changes when they arrive).
- Real-time streaming of progress to a remote dashboard.

---

## User stories

- As a content maintainer, I want to run `ticker-cli translate` and have all
  missing Chinese files appear in under 30 minutes, so I can review and commit
  them the same day.
- As a maintainer on a constrained laptop, I want to cap how much CPU the
  translation job uses so the machine stays usable while translations run in
  the background.
- As someone running translate for the first time, I want to see an ETA before
  the job starts so I know whether to wait or walk away.
- As someone debugging a failed run, I want to query past job durations to
  understand whether slowness is a regression or expected behavior.

---

## Research findings

### Queuing theory: utilization ceiling and flag naming

In M/M/c queue theory, **utilization** ρ = λ / (c · μ), where:

- λ = job arrival rate (files/second entering the queue)
- c = number of workers (servers)
- μ = per-worker service rate (files/second a single worker can complete)

The system is **stable only when ρ < 1.0**. As ρ → 1, queue length grows
without bound and mean wait time → ∞. In practice the "knee of the curve" —
where marginal throughput gains flatten while latency costs explode — sits at
**ρ ≈ 0.70–0.80**. Operating above 0.80 yields diminishing throughput per
unit of CPU at the cost of rising contention and thermal stress.

**Application to flag naming:**

The primary concurrency flag is `--workers INT`. Its default is calculated
as `max(1, floor(cpu_count × 0.75))`, which targets ρ ≈ 0.75 — just below
the knee. The 0.75 multiplier is documented in the help text so users who
know queuing theory understand the rationale, and users who don't have a
safe default.

An optional `--utilization FLOAT` flag (0.0–1.0) is provided as a
higher-level alias: it computes `workers = max(1, floor(cpu_count × utilization))`
and sets `--workers` accordingly. This lets advanced users express intent in
utilization terms without doing the arithmetic. The two flags are mutually
exclusive.

Example defaults on common hardware:

| Machine       | cpu_count | Default workers (×0.75) |
|---------------|-----------|--------------------------|
| 4-core laptop | 4         | 3                        |
| 8-core laptop | 8         | 6                        |
| 16-core desktop | 16      | 12                       |
| 2-core CI     | 2         | 1                        |

**Caveat for CPU-bound Ollama:** When Ollama runs without GPU acceleration,
it saturates all available threads during inference. Concurrent Ollama requests
queue server-side; extra workers past `--workers 2` yield minimal parallelism
gains and can cause thermal throttling. The `--workers` default is appropriate
for GPU-accelerated or API-backed backends. For CPU-only Ollama, `--workers 2`
is the practical optimum. The command detects CPU-only mode via the Ollama
`/api/tags` response and warns if `--workers > 2` is set without GPU.

### SQLite as a job metrics store (TSDB question)

**SQLite is not a TSDB.** True time-series databases (TimescaleDB, InfluxDB,
QuestDB) offer time-partitioned storage, automatic rollups, continuous
aggregates, and streaming ingestion — designed for millions of events/second
over long retention windows.

Our workload: at most a few hundred translate runs ever, with ~30 file-job
rows per run. This is a trivially small data volume. A TSDB would add an
external service dependency for zero benefit at this scale.

**Decision: append-only SQLite tables with Unix epoch timestamps.** The
heuristic queries we need (avg duration, P50 duration, failure rate) are
expressible as plain SQL against two small tables. SQLite handles this
comfortably. No TSDB, no streaming, no external dependency.

---

## Design

### Command interface

```
ticker-cli translate [OPTIONS]

Options:
  --path PATH             Translate a single file instead of the full inventory.
  --language TEXT         Target language code (default: zh-cn). Repeatable.
                          Future: --language zh-cn --language ko
  --workers INT           Number of parallel translation workers.
                          Default: max(1, floor(cpu_count × 0.75)).
  --utilization FLOAT     Alternative to --workers: target CPU utilization
                          fraction (0.0–1.0). Computes workers automatically.
                          Mutually exclusive with --workers.
  --timeout-per-file INT  Seconds to wait for a single file before marking
                          it failed. Default: 300.
  --retry INT             Number of retries on per-file failure. Default: 1.
  --model TEXT            Ollama model to use. Default: qwen2.5:7b.
  --backend TEXT          Translation backend: ollama | huggingface.
                          Default: ollama.
  --force                 Re-translate files that already have content.
  --dry-run               Print what would be translated; do not write files.
  --no-heuristics         Skip ETA estimate (useful for first run with no history).
  --help                  Show this message and exit.
```

### Startup sequence

Before submitting any jobs, the command:

1. Walks `hugo/site/content/` and builds the job list (English files with
   missing or empty target-language siblings).
2. Queries the `translate_file_jobs` table for historical `avg(duration_seconds)`
   and `count(*)` filtered by `language` and `model`. If ≥ 5 historical
   completed jobs exist, prints an ETA:
   ```
   Found 24 files to translate into zh-cn.
   Historical avg: 4m12s/file (based on 31 past jobs, model qwen2.5:7b).
   Estimated wall time with 6 workers: ~17 minutes.
   Starting…
   ```
   If history is insufficient, prints:
   ```
   Found 24 files to translate into zh-cn.
   No historical data yet — run will establish baseline timing.
   Starting…
   ```
3. Inserts a `translate_runs` row with `status = 'running'`.
4. Inserts one `translate_file_jobs` row per (file, language) pair with
   `status = 'queued'`.

### Job queue design

The unit of work is a **(source\_file, language)** pair. All pairs across all
requested languages are enqueued into a single flat pool before any worker
starts. This is the correct design because:

- It naturally parallelizes across both the file and language dimensions.
- The worker pool load-balances without needing language-specific queues.
- With one language today (zh-cn) it degenerates to a simple file list.
- When additional languages are added (e.g., `--language ko`), they are
  enqueued alongside zh-cn jobs with no code changes. The pool distributes
  them across workers by arrival order.

**Do not** serialize by language (all zh-cn then all ko). That wastes
inter-language parallelism and doubles wall time for every additional locale.

### Parallelism implementation

Use `concurrent.futures.ThreadPoolExecutor`. Threads (not processes) are the
right primitive because the bottleneck is Ollama I/O (HTTP round-trip +
inference time), not Python CPU computation. GIL is not a concern here.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=workers) as pool:
    futures = {pool.submit(translate_job, job, db, config): job for job in jobs}
    for future in as_completed(futures):
        job = futures[future]
        try:
            result = future.result()
            update_job_db(db, job, result)
            render_progress(result)
        except Exception as exc:
            handle_failure(db, job, exc, retry_queue)
```

A `retry_queue` is drained after the main pool completes. Jobs that exhaust
their retry count are marked `failed` and their `error_message` is saved.

### `translate_job` function (one file, one language)

1. Update `translate_file_jobs` row: `status = 'running'`, `started_at = now()`, `worker_id = thread_id`.
2. Read source `.md`, split on first `---` pair into frontmatter + body.
3. POST body to Ollama `/api/generate` with the system prompt from
   `zhcn_content_backfill.md` (stored as `SYSTEM_PROMPT` constant in
   `translate.py`).
4. Stream the response; accumulate tokens. Apply timeout guard.
5. Parse translated frontmatter fields (`title`, `description`) from a
   second Ollama call with a shorter prompt (or regex-extract if the
   model was given the full file including frontmatter).
6. Write the `.zh-cn.md` file: translated frontmatter + translated body.
7. Update `translate_file_jobs` row: `status = 'completed'`, `completed_at`,
   `duration_seconds`, `input_chars`, `output_chars`.

### Progress display

Use `tqdm` for a live progress bar:

```
Translating: 100%|████████████| 24/24 [18:42<00:00, 46.7s/file]
✓ strategy-dividend-daddy.zh-cn.md  (4m03s)
✓ articles/how-ticker-extraction-works.zh-cn.md  (6m21s)
✗ glossary/beta.zh-cn.md  (timeout after 300s, retrying…)
```

On completion, print a summary:

```
Translation run complete.
  Completed: 23/24
  Failed:     1/24  (see temp/translate-20260409-143022.log)
  Wall time:  19m04s
  Workers:    6
  Model:      qwen2.5:7b
```

### SQLite schema

Add to `data/market_data.db` via a new migration in `migrations.py`.

```sql
-- One row per translate command invocation
CREATE TABLE IF NOT EXISTS translate_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT    NOT NULL UNIQUE,       -- UUID v4
    started_at      REAL    NOT NULL,              -- Unix epoch (float)
    completed_at    REAL,                          -- NULL while running
    status          TEXT    NOT NULL DEFAULT 'running',
                                                  -- running|completed|partial|failed
    languages       TEXT    NOT NULL,              -- JSON array: '["zh-cn"]'
    model           TEXT    NOT NULL,
    backend         TEXT    NOT NULL,
    workers         INTEGER NOT NULL,
    total_files     INTEGER NOT NULL,
    completed_files INTEGER NOT NULL DEFAULT 0,
    failed_files    INTEGER NOT NULL DEFAULT 0,
    skipped_files   INTEGER NOT NULL DEFAULT 0
);

-- One row per (source_file, language) job attempt
CREATE TABLE IF NOT EXISTS translate_file_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT    NOT NULL REFERENCES translate_runs(run_id),
    source_path      TEXT    NOT NULL,  -- relative: hugo/site/content/articles/foo.md
    target_path      TEXT    NOT NULL,  -- relative: hugo/site/content/articles/foo.zh-cn.md
    language         TEXT    NOT NULL,
    model            TEXT    NOT NULL,
    worker_id        INTEGER,           -- thread ident
    queued_at        REAL    NOT NULL,
    started_at       REAL,
    completed_at     REAL,
    status           TEXT    NOT NULL DEFAULT 'queued',
                                       -- queued|running|completed|failed|skipped
    duration_seconds REAL,
    input_chars      INTEGER,
    output_chars     INTEGER,
    attempt          INTEGER NOT NULL DEFAULT 1,
    error_message    TEXT
);

CREATE INDEX IF NOT EXISTS idx_translate_file_jobs_language_model
    ON translate_file_jobs (language, model, status);
```

**No TSDB.** These two tables are sufficient. Heuristic queries are plain SQL:

```sql
-- ETA estimate for a new run
SELECT
    AVG(duration_seconds)  AS avg_seconds,
    MIN(duration_seconds)  AS min_seconds,
    MAX(duration_seconds)  AS max_seconds,
    COUNT(*)               AS sample_size
FROM translate_file_jobs
WHERE status = 'completed'
  AND language = 'zh-cn'
  AND model = 'qwen2.5:7b';

-- P50 approximation (SQLite has no PERCENTILE_CONT)
SELECT duration_seconds AS p50
FROM translate_file_jobs
WHERE status = 'completed' AND language = 'zh-cn' AND model = 'qwen2.5:7b'
ORDER BY duration_seconds
LIMIT 1 OFFSET (
    SELECT COUNT(*) / 2
    FROM translate_file_jobs
    WHERE status = 'completed' AND language = 'zh-cn' AND model = 'qwen2.5:7b'
);

-- Failure rate by model
SELECT model, COUNT(*) AS total,
       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
       ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS failure_pct
FROM translate_file_jobs
GROUP BY model;
```

### User-friendly defaults rationale

| Flag | Default | Rationale |
|---|---|---|
| `--workers` | `max(1, floor(cpu_count × 0.75))` | Targets ρ ≈ 0.75, below the queuing theory knee. Leaves headroom for OS and Ollama's own threads. |
| `--utilization` | _(not set)_ | Optional alias; mutually exclusive with `--workers`. |
| `--timeout-per-file` | `300` (5 min) | qwen2.5:7b on CPU generates ~1–5 tok/s; a 1000-word article is ~1500 output tokens = up to 25 min worst case. 5 min is a reasonable p95 bound for most content files in this project. Increase with `--timeout-per-file 600` on slow hardware. |
| `--retry` | `1` | One retry catches transient Ollama errors (OOM, temp context overflow) without masking real failures. |
| `--model` | `qwen2.5:7b` | Strong Chinese language understanding. Benchmarks show better financial terminology handling than opus-mt-en-zh. |
| `--backend` | `ollama` | Local, free, no key required. |
| `--force` | off | Safe by default: skip files with existing content. Re-running after adding a new English file won't accidentally clobber existing Chinese translations. |

### Side effects (complete list)

Explicitly what `ticker-cli translate` does to the system:

| Side effect | Scope | Reversible? |
|---|---|---|
| Writes `.zh-cn.md` files | `hugo/site/content/**` | Yes — git checkout restores them |
| Inserts rows into `translate_runs` | `data/market_data.db` | Yes — DELETE by run_id |
| Inserts rows into `translate_file_jobs` | `data/market_data.db` | Yes — DELETE by run_id |
| Writes log file | `temp/translate-<timestamp>.log` | Yes — delete the file |
| HTTP POST to Ollama API | `localhost:11434` | N/A (no persistent external state) |
| CPU/GPU utilization: up to `workers × per-worker load` | System | N/A (released on completion) |
| Memory: Ollama model loaded into RAM/VRAM | System | Released when Ollama unloads the model |

**No network calls beyond localhost.** No paid API keys. No files written
outside the repo root and `temp/`.

### New files to create

- `python3/src/stock_ticker/translate.py` — `TranslateConfig`, `translate_job()`,
  `build_job_list()`, `run_translate()`, `fetch_heuristics()`, `SYSTEM_PROMPT`
- `python3/tests/test_translate.py` — unit tests (mock Ollama subprocess;
  assert frontmatter preservation, shortcode passthrough, ticker passthrough,
  DB row creation)

### Existing files to modify

- `python3/src/stock_ticker/cli.py` — register `translate` Click command group
- `python3/src/stock_ticker/migrations.py` — add migration for `translate_runs`
  and `translate_file_jobs` tables
- `python3/pyproject.toml` — add `tqdm` to dependencies; document
  `transformers` and `torch` as optional extras for the HuggingFace backend
- `docs/specs/zhcn_content_backfill.md` — note that the command design is
  superseded by this spec; keep the inventory and system prompt sections

---

## Behavioral guarantees

These three properties are explicitly tested in `python3/tests/test_translate.py`
(class `TestIdempotencyAndSkipSemantics`). They are first-class requirements,
not implementation details.

### Idempotency

Running `ticker-cli translate` N times without `--force` produces the same
final filesystem state as running it once. Formally:

- After a successful first run, every source file has a non-empty sibling
  translation file.
- On subsequent runs, `build_job_list()` marks those siblings as
  `action = 'skip'`. No translation call is made; no files are overwritten.
- The content of an already-translated file is **unchanged** by a re-run
  without `--force`. Specifically, Ollama is never contacted for those files.

### Skip predicate

A target translation file is considered **already-translated** if and only if
`_has_non_empty_body(target_path)` returns `True`: the file exists **and**
has non-whitespace content beyond its frontmatter.

A file that exists but contains only frontmatter (or is entirely empty) is
treated as *not yet translated* and will be included in the job list and in
`--dry-run` output. This handles stub files that were created but never
populated.

### Dry-run completeness

`--dry-run` is a read-only pre-flight. It must:

1. **List** every `source_path -> target_path` pair that `build_job_list()`
   classified as `action = 'translate'`, one per line in stdout.
2. **Report** the count of already-translated files that would be skipped.
3. **Write zero files** to disk.
4. **Insert zero rows** into SQLite (no `translate_runs` or
   `translate_file_jobs` entries).
5. **Print an ETA** (size-based or historical) so the operator can decide
   whether to proceed.

Running `--dry-run` twice in a row must produce identical file listing output
(subject only to ETA variance if historical data was added in between).

---

## Affected files

```
python3/src/stock_ticker/translate.py      (new)
python3/src/stock_ticker/cli.py            (modified — register command)
python3/src/stock_ticker/migrations.py     (modified — new tables)
python3/tests/test_translate.py            (new)
python3/pyproject.toml                     (modified — tqdm dep)
docs/specs/zhcn_content_backfill.md       (modified — cross-reference note)
```

---

## Verification

1. `ticker-cli translate --dry-run` lists ~28 files, prints ETA "No historical
   data yet" (first run), exits without writing files or DB rows.

2. `ticker-cli translate --workers 2 --timeout-per-file 30 --model qwen2.5:7b`
   runs against a single small test file. Confirm:
   - One row in `translate_runs`, `status = 'completed'`.
   - One row in `translate_file_jobs`, `status = 'completed'`, `duration_seconds` populated.
   - `.zh-cn.md` file written with non-empty body.
   - Frontmatter fields (`date`, `layout`, `strategy_key`) are identical to the
     source; `title` is in Chinese.

3. A second run without `--force` skips the already-translated file. Confirm
   `translate_file_jobs` row has `status = 'skipped'`.

4. Run `ticker-cli translate --dry-run` again after step 2. ETA estimate now
   prints, referencing ≥ 1 historical job.

5. Kill Ollama mid-run. Confirm the timed-out job is retried once, then marked
   `failed` with `error_message` populated. `translate_runs.status = 'partial'`.

6. Full run: `ticker-cli translate` completes all ~28 files. Run
   `cd hugo/site && hugo server`. Manually verify:
   - `http://localhost:1313/zh-cn/strategy-dividend-daddy/` → body in Chinese
   - `http://localhost:1313/zh-cn/articles/how-ticker-extraction-works/` → 200, body in Chinese
   - `http://localhost:1313/zh-cn/glossary/beta/` → 200, body in Chinese

7. `pytest python3/tests/test_translate.py` passes with Ollama mocked.

---

## Open questions

**Q1:** Should `ticker-cli translate` detect CPU-only Ollama and warn when
`--workers > 2`? **Default: yes** — call `/api/tags` and check for GPU fields.
Print a warning, not an error. Let the user override.

**Q2:** Should the ETA use a simple mean or a more robust estimator
(trimmed mean, P75)? **Default: mean.** P50 is more robust but requires more
history. Add a note to reconsider after 50+ jobs are recorded.

**Q3:** Should `ticker-cli run-all` automatically invoke `translate`?
**Default: no.** Translations require human review; auto-running would create
unreviewed content on every trading-day data refresh. Add an explicit
`--with-translate` flag to `run-all` if operators want it integrated.

**Q4:** Should `--utilization` accept values > 1.0 (overclocking intent)?
**Default: no.** Clamp to 1.0 with a warning. Allowing > 1.0 would confuse
the queuing theory framing.

**Q5:** When multiple `--language` flags are passed, should workers prefer
to finish all jobs for one language before starting the next, to produce
a reviewable batch sooner? **Default: no** — uniform interleaving maximizes
throughput and the reviewer can filter by language in the log file. Revisit
when a second language is actually added.

**Q6:** Should `translate_file_jobs` be pruned after N days to prevent
unbounded DB growth? **Default: no pruning in v1.** Volume is negligible
(~28 rows × translate frequency) and historical data improves ETA accuracy.

---

## Alternatives considered

**Sequential execution (one file at a time).**
Simple to implement, zero concurrency bugs. Rejected: 28 files × 5 min/file =
140 minutes minimum. Operator time cost is unacceptable.

**`multiprocessing.Pool` instead of `ThreadPoolExecutor`.**
Avoids the GIL. Rejected: the bottleneck is Ollama I/O, not Python CPU.
Process overhead (pickling, IPC) adds complexity without benefit.

**One language at a time (zh-cn fully done, then ko, then ja).**
Simpler mental model. Rejected: doubles wall time for every additional locale.
Uniform job queue with `(file, language)` pairs is not meaningfully more
complex and supports future locales for free.

**External job queue (Celery, RQ, Redis).**
Scales to distributed workers. Rejected: massive operational overhead for a
CLI tool that runs on one machine. SQLite + `ThreadPoolExecutor` is sufficient.

**TimescaleDB or InfluxDB for job metrics.**
Native TSDB capabilities. Rejected: requires an external database service for
a data volume of hundreds of rows. SQLite append-only tables are equivalent
for this workload.

**`asyncio` + `aiohttp` for Ollama calls.**
Elegant async I/O. Rejected: Ollama's Python client and subprocess interface
are synchronous; mixing async with subprocess management adds complexity.
Threads are simpler and functionally equivalent here.
