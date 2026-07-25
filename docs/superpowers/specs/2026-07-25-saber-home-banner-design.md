# Saber Homepage Banner Design

## Goal

Use the user-supplied Saber artwork as the homepage banner while preserving the Fuwari theme's existing banner presentation shown in the README.

## Design

- Copy the supplied image into `src/assets/images/saber-home-banner.jpg`.
- Enable the existing `siteConfig.banner` feature in `src/config.ts`.
- Point `siteConfig.banner.src` to the local asset and retain `position: "center"` so Fuwari's responsive `object-cover` crop keeps the character as the visual focus.
- Leave the existing credit setting disabled because no attribution text or source URL was supplied.

## Scope and Verification

No layout, component, or CSS changes are needed. Run the production build after the configuration and asset update to confirm Astro resolves the image and renders the site successfully.
