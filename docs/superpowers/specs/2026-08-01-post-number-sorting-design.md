# Post Number Sorting Design

## Goal

Show numbered learning posts first on the homepage, ordered by chapter number descending. Show posts without a stable number afterward, ordered by their real source-mtime-derived publication date descending.

## Sorting Contract

- Read the stable chapter number from the numeric suffix of the post slug, such as `course-32`, `prereq-27`, `tools-03`, or `math-01`.
- Do not parse titles because synchronized titles can be missing or malformed; current course 21 and course 28 demonstrate that risk.
- A numbered post always precedes an unnumbered post.
- Two numbered posts compare by numeric suffix descending; equal numbers compare by `published` descending.
- Two unnumbered posts compare by `published` descending.
- Final ties compare by slug for deterministic builds.

## Scope and Verification

Extract a pure comparator into a focused utility, use it in the existing collection sorter, add Node tests for every branch of the contract, then run the test, Astro check, and production build. Push `main` after verification so GitHub Actions deploys the ordering change.
