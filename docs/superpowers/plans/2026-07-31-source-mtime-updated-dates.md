# Source Mtime Updated Dates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate each mapped blog post's updated frontmatter from the corresponding source Markdown file's real modification date, without changing published.

**Architecture:** Refactor scripts/sync-docs.py so its mapping includes prerequisites and produces an Asia/Shanghai date from a source mtime. The script updates only the source-derived body and updated frontmatter field when either differs; tests use temporary files rather than the live source directory.

**Tech Stack:** Python standard library, Astro, TypeScript, pnpm 9.14.4 through mise.

## Global Constraints

- Preserve all existing published values and homepage sort order.
- Use source-file mtime from /Users/enkidu/PyCharmMiscProject/md as the only source of updated.
- Format the update date in Asia/Shanghai as YYYY-MM-DD.
- Cover course, prerequisite, math, tool, and Schema mappings.
- Do not write a destination when its rendered content would be unchanged.
- Do not modify the unrelated untracked .reasonix/ directory.
- Validate Python logic, a completed sync, an idempotent second run, mise exec -- pnpm check, and mise exec -- pnpm build.
- Commit and push main to trigger the existing GitHub Actions workflows.

---

### Task 1: Make source dates a tested frontmatter field

**Files:**
- Modify: scripts/sync-docs.py
- Create: tests/test_sync_docs.py

**Interfaces:**
- Consumes: source path mtime and destination Markdown frontmatter.
- Produces: destination content with unchanged published and a single updated: YYYY-MM-DD line.

- [ ] **Step 1: Write failing isolated tests**

Test that a temporary source file with a fixed epoch creates updated: 2026-07-31 in Shanghai time while retaining published, and that rerunning makes no second write.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: python3 -m unittest tests.test_sync_docs -v

Expected: failure because source mtime is not yet written into frontmatter.

- [ ] **Step 3: Implement minimal sync support**

Add an mtime-to-date helper using zoneinfo.ZoneInfo("Asia/Shanghai"); update or insert the updated line without changing other frontmatter; compare rendered content before writing. Add prerequisite mapping and route every mapping through the same update operation.

- [ ] **Step 4: Run focused tests**

Run: python3 -m unittest tests.test_sync_docs -v

Expected: all tests pass.

### Task 2: Synchronize actual posts and validate the blog

**Files:**
- Modify: src/content/posts/*.md for mapped posts whose source-derived updated differs

**Interfaces:**
- Consumes: the tested synchronizer and existing source Markdown files.
- Produces: updated fields matching source mtimes while preserving published.

- [ ] **Step 1: Run the real synchronization**

Run: python3 scripts/sync-docs.py

Expected: mapped posts gain or refresh their updated dates from their actual source files.

- [ ] **Step 2: Verify source-date agreement and idempotency**

Run the sync a second time and a Python verification that each mapped destination's updated field equals the source file's Shanghai date.

Expected: the second run makes no file changes and every mapped post agrees.

- [ ] **Step 3: Run Astro validation**

Run: mise exec -- pnpm check && mise exec -- pnpm build

Expected: zero Astro-check errors and a successful static build.

- [ ] **Step 4: Inspect scope, commit, and push**

Run: git diff --check; git add scripts/sync-docs.py tests/test_sync_docs.py src/content/posts; git commit -m "fix: sync post update dates from source files"; git push origin main

Expected: only the date-sync implementation, its tests, and date frontmatter changes are committed; the push triggers GitHub Actions.
