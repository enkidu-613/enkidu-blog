# Source Mtime Updated Dates Design

## Goal

Display each synced blog post's real source-document update date without changing its original publication date or homepage ordering.

## Design

- Treat the mapped Markdown files under `/Users/enkidu/PyCharmMiscProject/md` as the source of truth for `updated`.
- Preserve every post's existing `published` value and all non-date frontmatter.
- Add or refresh `updated` as the source file mtime converted to an `Asia/Shanghai` `YYYY-MM-DD` date.
- Cover all existing mapped blog groups: courses, prerequisites, mathematics, tools, and Schema.
- Make the synchronizer idempotent: write a destination only when its source body or `updated` date differs.

## Verification and Delivery

- Add focused tests using temporary source and destination files.
- Run the date synchronization, then confirm a second check reports no pending date changes.
- Run `mise exec -- pnpm check` and `mise exec -- pnpm build`.
- Commit and push `main`; the existing GitHub Actions workflows will check, build, and deploy the site.
