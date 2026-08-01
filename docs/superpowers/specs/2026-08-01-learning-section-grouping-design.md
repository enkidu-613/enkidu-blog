# Learning Section Grouping Design

## Goal

Separate the blog's main course, prerequisite knowledge, and supplementary material on the homepage without changing source Markdown locations, post slugs, RSS ordering, archive ordering, or article navigation.

## Content model

Add a required `section` frontmatter field with exactly three values:

- `main`: `course-*`
- `prerequisite`: `prereq-*`
- `supplement`: `tools-*`, `math-*`, and `language-*`

`scripts/sync-docs.py` is the authority for mapped teaching posts. Every sync must upsert both the source-mtime-derived `published` value and the mapped `section`, remove obsolete `updated`, preserve other frontmatter, and remain idempotent. `scripts/new-post.js` defaults manually created posts to `supplement`.

## Homepage behavior

Homepage ordering is section-first:

1. `main`
2. `prerequisite`
3. `supplement`

Within each section, retain the existing numbered ordering contract: terminal slug number descending, then `published` descending, then slug ascending; unnumbered posts follow numbered posts by `published` descending and slug ascending.

The existing pagination remains. `PostPage.astro` renders a visible Chinese heading at the start of every page and whenever the section changes:

- 主线课程
- 前置知识
- 补充内容

Repeating the heading at a page boundary prevents a page that begins mid-section from losing context.

## Preserved boundaries

- Keep RSS, archive, and article `prev/next` date-first.
- Keep all existing `/posts/<slug>/` URLs.
- Do not move Markdown files into new directories.
- Do not create new section routes or client-side filtering.
- Keep Saber banner behavior unchanged.

## Validation

- Extend Python sync tests for section upsert, preservation, and idempotence.
- Extend Node sorting tests for section priority and within-section ordering.
- Test new-post generation in a temporary directory.
- Run source sync twice and confirm the second run is clean.
- Run focused tests, Astro check, production build, Biome, and `git diff --check`.
- Inspect generated homepage pagination for the three section headings and verify RSS remains date-first.
