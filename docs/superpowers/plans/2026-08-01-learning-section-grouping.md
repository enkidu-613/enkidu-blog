# Learning Section Grouping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit learning-section metadata and display main, prerequisite, and supplementary posts as separate ordered homepage groups.

**Architecture:** The source-sync layer writes a required `section` enum into every mapped post. A pure TypeScript comparator applies section priority only to the homepage, while `PostPage.astro` renders localized group headings. Shared date-first consumers remain untouched.

**Tech Stack:** Python 3 standard library, Astro 5, TypeScript, Node test runner, pnpm 9.14.4 via mise.

## Global Constraints

- Treat `/Users/enkidu/PyCharmMiscProject/md` as the source and `src/content/posts/` as the mirror.
- Keep `published` equal to source Markdown mtime in `Asia/Shanghai`; never substitute the current date.
- Use `section: main | prerequisite | supplement`.
- Apply section grouping only to the homepage; preserve RSS, archive, and article navigation date-first ordering.
- Preserve existing slugs, URLs, pagination size, and Saber banner behavior.
- Run pnpm through `mise exec -- pnpm`.

---

### Task 1: Source metadata classification

**Files:**
- Modify: `tests/test_sync_docs.py`
- Modify: `scripts/sync-docs.py`
- Modify: `src/content/config.ts`

**Interfaces:**
- Produces: `sync_file(src_path, dst_path, section, create_fm=None)` that upserts `published` and `section`.
- Produces: Astro `section` data typed as `main | prerequisite | supplement`.

- [ ] **Step 1: Write failing sync tests**

Add assertions showing `sync_file(..., "main")` inserts `section: main`, replaces a stale section, preserves unrelated metadata, removes `updated`, and stays unchanged on the second run.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `mise exec -- python -m unittest tests/test_sync_docs.py`

Expected: FAIL because `sync_file` does not accept a section and does not write it.

- [ ] **Step 3: Implement metadata upsert**

Replace the date-only frontmatter updater with an updater that writes exactly one `published` and one `section` line. Pass `main`, `prerequisite`, or `supplement` from every mapping entry and include `section: supplement` in new tools frontmatter.

- [ ] **Step 4: Require the schema field**

Add `section: z.enum(["main", "prerequisite", "supplement"])` to `src/content/config.ts`.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `mise exec -- python -m unittest tests/test_sync_docs.py`

Expected: all tests pass.

### Task 2: New-post default section

**Files:**
- Create: `tests/new-post-template.test.mjs`
- Modify: `scripts/new-post.js`

**Interfaces:**
- Produces: manually generated frontmatter containing `section: supplement`.

- [ ] **Step 1: Write a failing temporary-directory test**

Copy `scripts/new-post.js` into a temporary project directory, execute it there with `example-post`, and assert the generated Markdown contains `section: supplement`.

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test tests/new-post-template.test.mjs`

Expected: FAIL because the template omits `section`.

- [ ] **Step 3: Add the minimal template field**

Insert `section: supplement` after `published` in the generated frontmatter.

- [ ] **Step 4: Run the test and verify GREEN**

Run: `node --test tests/new-post-template.test.mjs`

Expected: PASS.

### Task 3: Homepage section ordering and labels

**Files:**
- Modify: `tests/post-sort-utils.test.mjs`
- Modify: `src/utils/post-sort-utils.ts`
- Modify: `src/utils/content-utils.ts`
- Create: `src/utils/post-section-utils.ts`
- Create: `tests/post-section-utils.test.mjs`
- Modify: `src/components/PostPage.astro`

**Interfaces:**
- Produces: `comparePostsBySectionThenNumberThenDate(a, b)` for homepage use only.
- Produces: `getPostSectionLabel(section)` returning `主线课程`, `前置知识`, or `补充内容`.

- [ ] **Step 1: Write failing comparator tests**

Assert `main` precedes `prerequisite` even when its chapter number is smaller, `prerequisite` precedes `supplement`, and existing within-section number/date behavior remains.

- [ ] **Step 2: Write failing label tests**

Assert the three enum values return their exact Chinese labels.

- [ ] **Step 3: Run both tests and verify RED**

Run: `node --test tests/post-sort-utils.test.mjs tests/post-section-utils.test.mjs`

Expected: FAIL because the comparator and label utility do not exist.

- [ ] **Step 4: Implement pure utilities**

Add a fixed section priority map, compose it with `comparePostsByNumberThenDate`, and implement the exhaustive label map.

- [ ] **Step 5: Wire homepage and headings**

Use the section comparator only in `getHomepageSortedPosts()`. In `PostPage.astro`, render a heading for the first entry and whenever `entry.data.section` differs from the preceding entry.

- [ ] **Step 6: Run tests and verify GREEN**

Run: `node --test tests/post-sort-utils.test.mjs tests/post-section-utils.test.mjs`

Expected: all tests pass.

### Task 4: Synchronize content and verify production output

**Files:**
- Modify: `tests/test_sync_docs.py`
- Modify: `scripts/sync-docs.py`
- Modify: `src/content/posts/*.md`

**Interfaces:**
- Consumes: section-aware `scripts/sync-docs.py`.
- Produces: every mapped post with exactly one valid `section` line.

- [ ] **Step 1: Write and pass a worktree-safety regression test**

Assert `DST_DIR` resolves beneath the checkout containing `scripts/sync-docs.py`, then replace the hard-coded main-checkout path with a script-relative repository path.

Run: `mise exec -- python -m unittest tests/test_sync_docs.py`

Expected: the new test fails before the fix and passes afterward.

- [ ] **Step 2: Run source synchronization**

Run: `mise exec -- python scripts/sync-docs.py`

Expected: mapped posts gain the correct section while retaining source-derived dates and bodies.

- [ ] **Step 3: Prove idempotence**

Run the same sync command again and confirm `git diff` does not change between runs.

- [ ] **Step 4: Run the complete verification suite**

Run:

```bash
mise exec -- python -m unittest tests/test_sync_docs.py
node --test tests/post-sort-utils.test.mjs tests/post-section-utils.test.mjs tests/new-post-template.test.mjs
mise exec -- pnpm check
mise exec -- pnpm build
mise exec -- pnpm exec biome ci ./src --reporter=github
git diff --check
```

Expected: all commands exit 0; the existing `bashr` highlighting warning may remain during content processing.

- [ ] **Step 5: Inspect generated behavior**

Confirm generated pagination shows `主线课程`, then `前置知识`, then `补充内容` without intermixing. Confirm `dist/rss.xml` remains publication-date-first.

- [ ] **Step 6: Commit the implementation**

Stage only the specification, plan, tests, scripts, schema, utilities, component, and synchronized posts. Use focused Conventional Commits.
