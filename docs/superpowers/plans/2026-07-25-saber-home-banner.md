# Saber Homepage Banner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure the supplied Saber artwork as the Fuwari-style homepage banner.

**Architecture:** Reuse Fuwari's built-in `siteConfig.banner` configuration. The image lives in the existing Astro asset directory and is resolved by the existing banner component; no custom CSS or component changes are required.

**Tech Stack:** Astro, TypeScript, Fuwari theme configuration, pnpm.

## Global Constraints

- Store the supplied JPEG image as `src/assets/images/saber-home-banner.jpg`.
- Set `siteConfig.banner.enable` to `true`.
- Use `assets/images/saber-home-banner.jpg` and retain the existing `"center"` crop position.
- Keep banner credit disabled because no artwork attribution was supplied.
- Validate with the repository's production build command.

---

### Task 1: Add and configure the homepage banner

**Files:**
- Create: `src/assets/images/saber-home-banner.jpg`
- Modify: `src/config.ts:18-27`
- Test: production build invoked through `pnpm build`

**Interfaces:**
- Consumes: The supplied `/Users/enkidu/Downloads/【哲风壁纸】Fate-saber.png` file, which is JPEG data.
- Produces: The existing `siteConfig.banner` object with `enable`, `src`, and `position` values consumed by `src/layouts/Layout.astro`.

- [ ] **Step 1: Establish the pre-change configuration check**

Run:

```bash
rg -n -A 9 'banner: \{' src/config.ts
```

Expected: the current banner is disabled and references `assets/images/demo-banner.png`.

- [ ] **Step 2: Copy the supplied artwork into the existing assets directory**

Run:

```bash
cp '/Users/enkidu/Downloads/【哲风壁纸】Fate-saber.png' src/assets/images/saber-home-banner.jpg
file src/assets/images/saber-home-banner.jpg
```

Expected: `file` identifies JPEG image data; the `.jpg` extension matches the actual file format.

- [ ] **Step 3: Apply the minimal banner configuration**

In `src/config.ts`, set the existing banner fields to:

```ts
banner: {
    enable: true,
    src: "assets/images/saber-home-banner.jpg",
    position: "center",
    credit: {
        enable: false,
        text: "",
        url: "",
    },
},
```

- [ ] **Step 4: Run the production build**

Run:

```bash
pnpm build
```

Expected: exit status 0 and Astro completes the production build without an unresolved image or TypeScript error.

- [ ] **Step 5: Inspect the completed change and commit it**

Run:

```bash
git diff --check
git status --short
git add src/assets/images/saber-home-banner.jpg src/config.ts
git commit -m "feat: set Saber homepage banner"
```

Expected: the commit contains only the new banner asset and its configuration change.
