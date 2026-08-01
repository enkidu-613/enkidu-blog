import assert from "node:assert/strict";
import test from "node:test";

import { getPostSectionLabel } from "../src/utils/post-section-utils.ts";

test("returns the Chinese label for every post section", () => {
	assert.equal(getPostSectionLabel("main"), "主线课程");
	assert.equal(getPostSectionLabel("prerequisite"), "前置知识");
	assert.equal(getPostSectionLabel("supplement"), "补充内容");
});
