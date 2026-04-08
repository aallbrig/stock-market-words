# i18n Architecture

**Status:** Design / Foundation
**Last updated:** 2026-04-08

How multilingual content is structured today, what's broken, and the
conventions to follow when adding new content or a new language. Builds on
the earlier research note in
[`docs/research/20260403_035343_UTC_zh-cn_i18n_evaluation.md`](../research/20260403_035343_UTC_zh-cn_i18n_evaluation.md)
— promoted from "research" to "architecture" because the choices have been
made.

---

## Decisions

1. **Hugo's built-in multilingual system is the only i18n mechanism.** No
   runtime JS i18n library. Approved in the research note above.
2. **Languages today:** English (`en`, default) and Simplified Chinese
   (`zh-cn`). Configured in `hugo/site/hugo.toml` under `[languages]`.
3. **URL strategy:** English at the root (`/about/`), Chinese under
   `/zh-cn/` (`/zh-cn/about/`). `defaultContentLanguageInSubdir = false`.
4. **Filename strategy:** for any prose page `foo.md`, the Chinese
   translation lives next to it as `foo.zh-cn.md`. Hugo links them
   automatically via the language switcher.
5. **Template strings live in `hugo/site/i18n/{en,zh-cn}.toml`** — both files
   currently have **754 keys, fully translated**. Use `{{ i18n "key" }}` in
   layouts; never hardcode user-facing English in a template.
6. **JS strings ride along** via `hugo/site/layouts/partials/i18n-js.html`,
   which injects a `window.I18N` object built from the same TOML files. JS
   should read `window.I18N.foo`, never inline strings.

## Current state — what works

- Site config, language switcher, navigation, footer, all hard-coded
  template strings.
- Home page (`/` and `/zh-cn/`) including the Extract Tickers tool — all
  labels and the JavaScript-driven UI translate correctly.
- Root prose pages: about, contact, methodology, privacy-policy, data,
  filtered-data (page chrome only), strategies (overview), articles index,
  glossary index. All have full `.zh-cn.md` siblings.
- DataTables localization (zh-HANS plugin loaded conditionally).

## Current state — what's broken

| Page set | Symptom | Root cause |
|---|---|---|
| `/zh-cn/articles/<slug>/` (7 pages) | 404 | No `.zh-cn.md` files exist for individual articles. Only `_index.zh-cn.md` exists. |
| `/zh-cn/glossary/<term>/` (14 pages) | 404 | Same — only `_index.zh-cn.md` exists. |
| `/zh-cn/strategy-dividend-daddy/`, etc. (5 pages) | Renders empty body | `.zh-cn.md` files exist but contain only frontmatter, no body. |
| `/zh-cn/raw-ftp-data/`, `/zh-cn/filtered-data/` | Renders empty body | Same — frontmatter-only. |
| `/zh-cn/tickers/<symbol>/` | 404 | The content adapter `hugo/site/content/tickers/_content.gotmpl` reads `Site.Data.all_tickers.tickers` and calls `$.AddPage`, but does not appear to materialize routes for the zh-cn language site. **Investigation pending — see [zhcn_ticker_pages spec](../specs/20260408_013203_UTC_zhcn_ticker_pages.md).** |

The fix tracks for these are documented in:

- [`docs/specs/20260408_013203_UTC_zhcn_content_backfill.md`](../specs/20260408_013203_UTC_zhcn_content_backfill.md)
- [`docs/specs/20260408_013203_UTC_zhcn_ticker_pages.md`](../specs/20260408_013203_UTC_zhcn_ticker_pages.md)

## Conventions for new content

### Adding a new prose page

1. Write `hugo/site/content/foo.md` (English).
2. Write `hugo/site/content/foo.zh-cn.md` with the same frontmatter and
   translated body. **Both files must exist** — there is no automatic
   fallback to English.
3. If the layout uses any new strings, add them to
   `hugo/site/i18n/en.toml` and `hugo/site/i18n/zh-cn.toml`.
4. Add the path to the `PAGES` array in
   `tests/puppeteer/website-pages.e2e.test.js` (per
   `.github/copilot-instructions.md`).

### Adding a new template string

1. Add a key to `hugo/site/i18n/en.toml`.
2. Add the same key to `hugo/site/i18n/zh-cn.toml` with the translation.
3. Reference it in the template as `{{ i18n "key" }}`.
4. If the string is consumed by JS, also add it to
   `hugo/site/layouts/partials/i18n-js.html` so it ends up in `window.I18N`.

### Adding a new language (e.g. Korean)

1. Add a `[languages.ko]` block to `hugo/site/hugo.toml`.
2. Create `hugo/site/i18n/ko.toml` with all 754 keys translated.
3. Create `*.ko.md` siblings for every translated content file.
4. Add a DataTables language plugin script tag for `ko`.
5. Update the language switcher partial.

### Translating CLI-generated content

`ticker-cli hugo pages` writes `raw-ftp-data.md` and `filtered-data.md`. It
does **not** write the `.zh-cn.md` siblings today. The content backfill spec
proposes a `ticker-cli translate` command to fill this gap with a model-
agnostic local LLM (default: `qwen2.5:7b` via Ollama). See the spec for
details.

### Translating ticker detail pages

The ticker template `hugo/site/layouts/tickers/single.html` already uses
`{{ i18n }}` for every label. Once the routes exist for `/zh-cn/tickers/`,
the labels render in Chinese automatically. The numerical data
(price, volume, market cap) is language-agnostic. The two fields that *could*
be translated — `sector` and `industry` — are currently passed through as
English and acceptable as-is.

## Anti-patterns to avoid

- **Don't** hardcode English in a layout — even if "the Chinese translation
  doesn't matter for this string." It always becomes a 404 in QA later.
- **Don't** add a runtime JavaScript i18n library. Hugo + `window.I18N` is
  enough.
- **Don't** rely on Hugo falling back to English when a translated content
  file is missing — Hugo does not do this by default with our config; the
  page 404s.
- **Don't** translate ticker symbols or company names. Symbols are universal;
  company names are proper nouns and stay in their original form.
