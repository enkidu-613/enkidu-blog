# Saber Banner Top-Crop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Saber homepage banner crop to the top so the character's face is visible in the initial desktop viewport.

**Architecture:** Reuse the Fuwari theme's existing `siteConfig.banner.position` field, which passes its value to the banner image's `object-position` style. This is a configuration-only change; the image asset, components, and CSS remain unchanged.

**Tech Stack:** Astro, TypeScript, Fuwari, pnpm 9.14.4 through mise.

## Global Constraints

- Change only `siteConfig.banner.position` from `"center"` to `"top"`.
- Preserve the Saber asset path, enabled banner state, and disabled empty credit fields.
- Do not modify images, components, or CSS.
- Verify with `mise exec -- pnpm check` and `mise exec -- pnpm build`.
- Start the local site and inspect the desktop homepage banner to confirm the face is visible.

---

### Task 1: Set and visually verify the top crop

**Files:**
- Modify: `src/config.ts:18-27`
- Test: Astro static check, production build, and local desktop-browser inspection

**Interfaces:**
- Consumes: `siteConfig.banner.position` in `src/config.ts`.
- Produces: the `"top"` value consumed by `ImageWrapper.astro` as CSS `object-position`.

- [ ] **Step 1: Capture the current crop configuration**

Run:

```bash
rg -n -A 9 'banner: \{' src/config.ts
```

Expected: `position: "center"` is configured.

- [ ] **Step 2: Apply the minimal configuration change**

In `src/config.ts`, change only:

```ts
position: "top",
```

Keep the surrounding source path and credit fields unchanged.

- [ ] **Step 3: Run static and production checks**

Run:

```bash
mise exec -- pnpm check
mise exec -- pnpm build
```

Expected: Astro check reports zero errors and the production build completes.

- [ ] **Step 4: Inspect the rendered homepage**

Run:

```bash
mise exec -- pnpm dev --host 127.0.0.1
```

Open the local homepage at a desktop viewport and confirm the banner shows Saber’s face without altering the page layout.

- [ ] **Step 5: Inspect and commit the completed change**

Run:

```bash
git diff --check
git status --short
git add src/config.ts
git commit -m "fix: show Saber face in homepage banner"
```

Expected: the commit changes only the configured crop position.
