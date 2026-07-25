# Saber Banner Top-Crop Design

## Goal

Show Saber’s face within the visible homepage banner while retaining the Fuwari theme's existing banner layout and responsive image behavior.

## Design

- Change only `siteConfig.banner.position` in `src/config.ts` from `"center"` to `"top"`.
- Reuse the theme's existing `object-fit: cover` and `object-position` behavior; no image editing, CSS overrides, or component changes are required.
- Keep the existing image asset, enabled banner state, and disabled credit fields unchanged.

## Verification

Run Astro's static check and production build. Start the local site and inspect the homepage banner at a desktop viewport to confirm Saber’s face is visible in the first screen.
