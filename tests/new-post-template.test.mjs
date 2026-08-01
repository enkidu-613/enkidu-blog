import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { copyFile, mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	"..",
);

test("new-post creates posts with the supplement section", async (t) => {
	const temporaryProjectDirectory = await mkdtemp(
		path.join(os.tmpdir(), "new-post-template-"),
	);
	t.after(() =>
		rm(temporaryProjectDirectory, { force: true, recursive: true }),
	);

	await copyFile(
		path.join(repositoryRoot, "scripts/new-post.js"),
		path.join(temporaryProjectDirectory, "new-post.js"),
	);

	execFileSync(process.execPath, ["new-post.js", "example-post"], {
		cwd: temporaryProjectDirectory,
	});

	const post = await readFile(
		path.join(temporaryProjectDirectory, "src/content/posts/example-post.md"),
		"utf8",
	);

	assert.match(post, /^section: supplement$/m);
});
