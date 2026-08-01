import assert from "node:assert/strict";
import test from "node:test";

import {
	comparePostsByDateThenSlug,
	comparePostsBySectionThenNumberThenDate,
	comparePostsByNumberThenDate,
	extractPostNumber,
} from "../src/utils/post-sort-utils.ts";

const post = (slug, published, section = "supplement") => ({
	slug,
	data: { published: new Date(published), section },
});

test("extracts only a terminal numeric slug suffix", () => {
	assert.equal(extractPostNumber("course-32"), 32);
	assert.equal(extractPostNumber("tools-03"), 3);
	assert.equal(extractPostNumber("language-schema"), null);
	assert.equal(extractPostNumber("course-31-notes"), null);
});

test("sorts numbered posts by number descending regardless of date", () => {
	const posts = [
		post("course-31", "2026-08-01"),
		post("course-32", "2025-01-01"),
	];
	posts.sort(comparePostsByNumberThenDate);
	assert.deepEqual(posts.map(({ slug }) => slug), ["course-32", "course-31"]);
});

test("uses publication date descending when chapter numbers match", () => {
	const posts = [
		post("course-27", "2026-07-20"),
		post("prereq-27", "2026-07-30"),
	];
	posts.sort(comparePostsByNumberThenDate);
	assert.deepEqual(posts.map(({ slug }) => slug), ["prereq-27", "course-27"]);
});

test("places numbered posts before unnumbered posts", () => {
	const posts = [
		post("language-schema", "2026-08-01"),
		post("course-01", "2025-01-01"),
	];
	posts.sort(comparePostsByNumberThenDate);
	assert.deepEqual(posts.map(({ slug }) => slug), ["course-01", "language-schema"]);
});

test("sorts unnumbered posts by date and final ties by slug", () => {
	const posts = [
		post("notes-z", "2026-07-01"),
		post("notes-b", "2026-08-01"),
		post("notes-a", "2026-08-01"),
	];
	posts.sort(comparePostsByNumberThenDate);
	assert.deepEqual(posts.map(({ slug }) => slug), [
		"notes-a",
		"notes-b",
		"notes-z",
	]);
});

test("sorts homepage posts by section before chapter number", () => {
	const posts = [
		post("prereq-32", "2026-08-01", "prerequisite"),
		post("main-01", "2025-01-01", "main"),
		post("tools-99", "2026-08-01", "supplement"),
	];

	posts.sort(comparePostsBySectionThenNumberThenDate);

	assert.deepEqual(posts.map(({ slug }) => slug), [
		"main-01",
		"prereq-32",
		"tools-99",
	]);
});

test("keeps number and date ordering within each homepage section", () => {
	const posts = [
		post("main-02", "2026-07-01", "main"),
		post("main-03", "2025-01-01", "main"),
		post("prereq-a-01", "2026-07-20", "prerequisite"),
		post("prereq-01-notes", "2026-07-30", "prerequisite"),
		post("prereq-b-01", "2026-07-25", "prerequisite"),
	];

	posts.sort(comparePostsBySectionThenNumberThenDate);

	assert.deepEqual(posts.map(({ slug }) => slug), [
		"main-03",
		"main-02",
		"prereq-b-01",
		"prereq-a-01",
		"prereq-01-notes",
	]);
});

test("keeps the shared non-homepage order strictly date-first", () => {
	const posts = [
		post("course-32", "2026-07-28T00:00:00Z"),
		post("language-schema", "2026-08-01T00:00:00Z"),
		post("course-31", "2026-07-31T00:00:00Z"),
	];

	assert.deepEqual(posts.sort(comparePostsByDateThenSlug).map(({ slug }) => slug), [
		"language-schema",
		"course-31",
		"course-32",
	]);
});
