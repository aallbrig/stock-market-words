# zh-CN Content Backfill

**Status:** Draft
**Author:** unassigned
**Created:** 2026-04-08

> **Note (2026-04-09):** The `ticker-cli translate` command design (parallelism
> model, job-tracking schema, CLI flags, ETA heuristics) has been superseded by
> [`docs/specs/cli_translate.md`](cli_translate.md). The content inventory
> table and system prompt below remain canonical; refer to `cli_translate.md`
> for implementation details.

## Context

The Simplified Chinese version of stockmarketwords.com is structurally
configured (Hugo `[languages]` block, full 754-key i18n TOML, language
switcher, hreflang tags) but most prose content under `/zh-cn/` is missing
or empty. The audience is heavily Singaporean, and these gaps render as 404s
or empty page bodies — a poor experience that undercuts the i18n investment
already made in commit `ff5ad26`.

Background reading:

- [`docs/design/i18n_architecture.md`](../design/20260408_013203_UTC_i18n_architecture.md)
- [`docs/research/20260403_035343_UTC_zh-cn_i18n_evaluation.md`](../research/20260403_035343_UTC_zh-cn_i18n_evaluation.md)

## Goal

Every prose page that exists in English under `hugo/site/content/` has a
non-empty `.zh-cn.md` sibling that renders meaningful Chinese content (no
404, no empty body, no lorem ipsum).

## Non-goals

- Translating ticker detail pages — those are covered by the
  [zh-CN ticker pages spec](./zhcn_ticker_pages.md).
- Translating `data/market_data.db` content (sector/industry strings stay in English).
- Adding any language other than zh-CN.
- Building a translation memory or glossary cache (could come later).
- Setting up paid translation APIs (OpenAI, DeepL, Google Translate). This
  spec is **local-LLM only**.

## User stories

- As a Singaporean visitor reading `/zh-cn/articles/how-ticker-extraction-works/`,
  I want the article to actually appear in Chinese instead of returning a 404.
- As a content maintainer, I want to run one CLI command after writing a new
  English article and have a draft Chinese translation appear next to it.

## Design

### Inventory of missing content

| Source (English) | Target (zh-CN) | Currently |
|---|---|---|
| `hugo/site/content/articles/hidden-tickers-in-earnings-transcripts.md` | `*.zh-cn.md` | missing |
| `hugo/site/content/articles/how-ticker-extraction-works.md` | `*.zh-cn.md` | missing |
| `hugo/site/content/articles/how-to-extract-tickers-from-financial-news.md` | `*.zh-cn.md` | missing |
| `hugo/site/content/articles/how-to-read-the-five-strategies.md` | `*.zh-cn.md` | missing |
| `hugo/site/content/articles/practical-guide-to-stock-indicators.md` | `*.zh-cn.md` | missing |
| `hugo/site/content/articles/top-stocks-by-strategy-march-2026.md` | `*.zh-cn.md` | missing |
| `hugo/site/content/articles/why-some-tickers-have-no-scores.md` | `*.zh-cn.md` | missing |
| `hugo/site/content/glossary/52-week-high.md` (and 13 other terms) | `*.zh-cn.md` | missing (14 files) |
| `hugo/site/content/strategy-dividend-daddy.md` | `*.zh-cn.md` | exists but body is empty |
| `hugo/site/content/strategy-falling-knife.md` | `*.zh-cn.md` | exists but body is empty |
| `hugo/site/content/strategy-institutional-whale.md` | `*.zh-cn.md` | exists but body is empty |
| `hugo/site/content/strategy-moon-shot.md` | `*.zh-cn.md` | exists but body is empty |
| `hugo/site/content/strategy-over-hyped.md` | `*.zh-cn.md` | exists but body is empty |
| `hugo/site/content/raw-ftp-data.md` (CLI-generated) | `*.zh-cn.md` | exists but body is empty |
| `hugo/site/content/filtered-data.md` (CLI-generated) | `*.zh-cn.md` | exists but body is empty |

Total: ~28 files needing non-empty Chinese bodies.

### New CLI command: `ticker-cli translate`

Add a new Click command in `python3/src/stock_ticker/cli.py` plus a new
module `python3/src/stock_ticker/translate.py`:

```
ticker-cli translate                        # translate everything missing/empty
ticker-cli translate --path content/articles/foo.md   # one file
ticker-cli translate --dry-run              # report what would be translated, don't write
ticker-cli translate --force                # re-translate even if .zh-cn.md has body
```

Behavior:

1. Walk `hugo/site/content/` looking for English `.md` files (anything not
   matching `*.zh-cn.md`).
2. For each, check if a `.zh-cn.md` sibling exists with a non-empty body
   (count non-frontmatter lines after stripping whitespace).
3. If missing or empty, translate and write the sibling.

### Translation pipeline (in `translate.py`)

The script is **model-agnostic** via a small backend dispatch. Configuration
via env vars or CLI flags:

| Var | Default | Purpose |
|---|---|---|
| `STOCK_TRANSLATE_BACKEND` | `ollama` | `ollama` or `huggingface` |
| `STOCK_TRANSLATE_MODEL` | `qwen2.5:7b` | model name passed to the backend |
| `STOCK_TRANSLATE_TIMEOUT` | `300` | per-file timeout in seconds |

**Ollama backend** — shells out to `ollama run <model>` over stdin. Requires
Ollama installed locally (`curl -fsSL https://ollama.com/install.sh | sh`)
and the model pulled (`ollama pull qwen2.5:7b`). No Python deps beyond what
the project already has.

**Hugging Face backend** — uses `transformers.pipeline("translation",
model=...)` if `transformers` and `torch` are importable. Lazy import so
they're optional. Tested with `Helsinki-NLP/opus-mt-en-zh` and
`facebook/nllb-200-distilled-600M`.

### System prompt

Used by the Ollama backend (HF translation models don't take a prompt). Keep
this in `python3/src/stock_ticker/translate.py` as a module-level constant.

```
You are a professional financial translator. Translate the following English
markdown text into Simplified Chinese (zh-CN) suitable for a Singaporean
audience reading a stock-market educational website. Rules:

1. Preserve ALL markdown formatting exactly: headings, bullets, code blocks,
   links, tables, Hugo shortcodes ({{< ... >}} and {{% ... %}}).
2. Do NOT translate ticker symbols (AAPL, CRM, NVDA), company names, code
   snippets, URLs, or anything inside backticks.
3. Use established Chinese financial terminology:
   - RSI -> 相对强弱指标 (RSI)
   - P/E ratio -> 市盈率
   - market cap -> 市值
   - dividend yield -> 股息收益率
   - moving average -> 移动平均线
4. Keep frontmatter (the --- block at the top) entirely unchanged. Translate
   only the body.
5. Output ONLY the translated markdown. No explanations, no preamble.
```

### Frontmatter handling

The script must:

1. Parse the English file's frontmatter (TOML or YAML, both occur).
2. Pass only the body to the translator.
3. Write a new frontmatter block to the `.zh-cn.md` file with `title`,
   `description`, and any `summary` fields translated. All other fields
   (`date`, `weight`, `tags`, `layout`) copy through unchanged.
4. Any `tags` field stays in English (tags are facets, not display labels).

### Translation report

After each run, write a log file to `temp/translate-<YYYYMMDD-HHMMSS>.log`
with: which files were translated, which model was used, char counts before
and after, and any errors. The reviewer reads this to plan their review pass.

### Human review workflow

Translations are **always** human-reviewed before merging. The spec does not
auto-commit. The expected loop:

1. Run `ticker-cli translate` after writing or updating an English page.
2. Read the generated `.zh-cn.md` files.
3. Edit anything that reads awkwardly.
4. Commit both the English and Chinese files together.

## Affected files

**New:**

- `python3/src/stock_ticker/translate.py`
- `python3/tests/test_translate.py`
- `hugo/site/content/articles/*.zh-cn.md` (×7)
- `hugo/site/content/glossary/*.zh-cn.md` (×14)

**Modified:**

- `python3/src/stock_ticker/cli.py` (register `translate` Click command)
- `python3/pyproject.toml` (no new required deps; document optional `transformers` extra)
- `python3/README.md` (add `translate` to commands list)
- `hugo/site/content/strategy-*.zh-cn.md` (×5 — fill in bodies)
- `hugo/site/content/raw-ftp-data.zh-cn.md` (fill in body)
- `hugo/site/content/filtered-data.zh-cn.md` (fill in body)
- `tests/puppeteer/website-pages.e2e.test.js` (add zh-cn variants to `PAGES`)

## Verification

1. `ticker-cli translate --dry-run` lists ~28 files needing translation.
2. `ticker-cli translate` runs to completion in under 90 minutes on the
   reference machine (i7-1360P + 32 GB RAM, qwen2.5:7b via Ollama).
3. Every file in the inventory above has a `.zh-cn.md` sibling with at least
   100 non-frontmatter characters.
4. `cd hugo/site && hugo server` starts cleanly. Manually visit:
   - `http://localhost:1313/zh-cn/articles/how-ticker-extraction-works/` → 200, Chinese body
   - `http://localhost:1313/zh-cn/glossary/beta/` → 200, Chinese body
   - `http://localhost:1313/zh-cn/strategy-dividend-daddy/` → 200, Chinese body
   - `http://localhost:1313/zh-cn/raw-ftp-data/` → 200, Chinese body
5. The Playwright `website-pages.e2e.test.js` PAGES array includes `/zh-cn/`
   variants and they all pass.
6. `pytest python3/tests/test_translate.py` passes (mocks the Ollama
   subprocess; verifies frontmatter preservation, shortcode passthrough,
   ticker-symbol passthrough).

## Open questions

- **Q1:** Should `ticker-cli run-all` automatically call `translate` after
  `hugo all`? **Default: no.** Translation is human-reviewed; auto-running
  it would create unreviewed commits. Revisit after a few weeks of use.
- **Q2:** Should the translator script also re-translate existing `.zh-cn.md`
  files when their English source has changed substantially? **Default: no
  in v1.** Add a `--diff-changed` mode in v2 if churn becomes a problem.
- **Q3:** Are Hugo shortcodes (`{{< foo >}}`) actually used in any of the
  English articles? **Default: assume yes, preserve them in the prompt
  even if currently unused.** Cheap insurance.

## Alternatives considered

- **Hand-translate everything.** Highest quality, but ~28 files of finance
  prose is a significant time investment, and the user explicitly asked for
  a local-LLM-driven approach to avoid paying for translation APIs.
- **Use a paid API (OpenAI / DeepL / Google Translate).** Best quality per
  dollar, but introduces a paid dependency the user wants to avoid.
- **Use a small dedicated translation model only (`opus-mt-en-zh`).** Fast
  (~5 minutes for everything) but weak on financial jargon and tends to
  produce literal translations of headings. Kept as an opt-in backend, not
  the default.
