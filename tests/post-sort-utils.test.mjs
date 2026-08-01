import assert from "node:assert/strict";
import test from "node:test";

import {
	comparePostsByNumberThenDate,
	extractPostNumber,
} from "../src/utils/post-sort-utils.ts";

const post = (slug, published) => ({
	slug,
	data: { published: new Date(published) },
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
