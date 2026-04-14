# ADR: English Fallback for Untranslated Articles

**Status:** Accepted
**Author:** Andrew Allbright
**Created:** 2026-04-14

## Context

stockmarketwords.com is multilingual (English + Simplified Chinese). Hugo's
default behavior for multilingual sites is to show a 404 or redirect to the
language root when a page has no translation. This means zh-CN visitors
navigating to an article that only exists in English would see no content.

Articles are the most labor-intensive content to translate — a 4,000-word
editorial with tables, shortcodes, and ticker links cannot be machine-translated
without quality review. Meanwhile, our zh-CN audience can generally read English
technical/financial content, and getting *some* content is always better than a
404.

The language switcher already shows a 🚧 construction icon next to 简体中文 to
signal that Chinese content is incomplete.

## Decision

**When an article does not have a zh-CN translation, serve the English version
as the fallback.** Do not let zh-CN visitors hit a 404 for content that exists
in English.

### Implementation

For each new article, if a zh-CN translation is not yet available, create a
minimal `.zh-cn.md` file that simply includes the English content via Hugo's
built-in cascade or by duplicating the English frontmatter with a note:

```markdown
---
title: "English title here"
author: "Andrew Allbright"
date: 2026-04-14
description: "English description here"
lastmod: 2026-04-14
draft: false
---

{{%/* include "articles/slug.md" */%}}
```

If Hugo's `include` shortcode is not available, the simplest approach is:

1. Copy the English `.md` file to a `.zh-cn.md` variant.
2. Prepend a visible notice in the content:

```markdown
> **注意：** 本文暂无中文翻译。以下为英文原文。
> (*Notice: This article is not yet translated into Chinese. The English
> original is shown below.*)
```

This ensures:
- zh-CN visitors see the article (not a 404)
- The notice sets expectations about the language
- When a translation is eventually created, the `.zh-cn.md` file is simply
  replaced with the translated version
- The 🚧 icon in the language switcher provides global-level signaling

### Checklist for new articles

- [ ] Create the English article `.md` file
- [ ] Create a `.zh-cn.md` fallback with the English content + notice banner
- [ ] When a proper translation is available, replace the fallback

## Consequences

- zh-CN visitors always see article content (never a 404)
- The notice banner is honest about the language gap
- Translation can happen asynchronously without blocking publication
- The `.zh-cn.md` file exists in the content directory, so Hugo's i18n
  link-building works correctly (language switcher links to a real page)

## Status

Accepted — applies to all articles published after this date.
