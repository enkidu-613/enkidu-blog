# Post Number Sorting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sort homepage posts by stable chapter number descending, followed by unnumbered posts by publication date descending.

**Architecture:** Add a pure comparator in `src/utils/post-sort-utils.ts` that reads a numeric slug suffix and applies deterministic fallback rules. Keep Astro collection loading and navigation-link generation in `content-utils.ts`.

**Tech Stack:** TypeScript, Node test runner, Astro, pnpm through mise.

## Global Constraints

- Parse only a terminal `-NN` slug suffix; do not parse titles.
- Numbered posts precede unnumbered posts.
- Sort number descending, equal numbers by `published` descending, final ties by slug.
- Sort unnumbered posts by `published` descending, final ties by slug.
- Preserve unrelated `.reasonix/` and Python cache files.
- Verify with `node --test tests/post-sort-utils.test.mjs`, `mise exec -- pnpm check`, and `mise exec -- pnpm build`.

---

### Task 1: Implement and integrate the post comparator

**Files:**
- Create: `src/utils/post-sort-utils.ts`
- Create: `tests/post-sort-utils.test.mjs`
- Modify: `src/utils/content-utils.ts`

**Interfaces:**
- `extractPostNumber(slug: string): number | null`
- `comparePostsByNumberThenDate(a, b): number` for objects with `slug` and `data.published`.

- [ ] **Step 1: Write failing Node tests** covering descending numbers, equal-number date fallback, numbered-before-unnumbered, unnumbered date order, and deterministic slug ties.
- [ ] **Step 2: Run `node --test tests/post-sort-utils.test.mjs` and confirm failure because the utility does not exist.**
- [ ] **Step 3: Implement the smallest pure comparator matching the exact contract.**
- [ ] **Step 4: Replace the publication-date-only comparator in `getRawSortedPosts()` with the new comparator.**
- [ ] **Step 5: Run the Node test, `mise exec -- pnpm check`, `mise exec -- pnpm build`, and inspect the generated first page ordering.**
- [ ] **Step 6: Commit the scoped files, merge to `main`, verify again, and push `main`.**
