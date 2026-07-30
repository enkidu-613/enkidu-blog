"""Regression tests for source mtime frontmatter synchronization."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync-docs.py"
SPEC = importlib.util.spec_from_file_location("sync_docs", SCRIPT_PATH)
sync_docs = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sync_docs)

SHANGHAI_2026_07_31_EPOCH = 1785427200


class SyncFileUpdatedDateTests(unittest.TestCase):
    """Ensure source modification dates become stable updated frontmatter."""

    def write_source(self, directory):
        source_path = directory / "source.md"
        source_path.write_text("# Source title\n\nSource body.\n", encoding="utf-8")
        os.utime(source_path, (SHANGHAI_2026_07_31_EPOCH, SHANGHAI_2026_07_31_EPOCH))
        return source_path

    def test_inserts_source_mtime_as_updated_and_keeps_existing_frontmatter(self):
        """Removing mtime-to-date frontmatter synchronization breaks this test."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = self.write_source(directory)
            destination_path = directory / "destination.md"
            destination_path.write_text(
                "---\n"
                'title: "Destination title"\n'
                "published: 2024-01-02\n"
                "draft: false\n"
                "---\n"
                "Old body.\n",
                encoding="utf-8",
            )

            did_write = sync_docs.sync_file(source_path, destination_path)

            self.assertTrue(did_write)
            content = destination_path.read_text(encoding="utf-8")
            self.assertIn("published: 2024-01-02\n", content)
            self.assertIn("updated: 2026-07-31\n", content)
            self.assertIn("draft: false\n", content)
            self.assertEqual(content.count("updated:"), 1)
            self.assertTrue(content.endswith("Source body.\n"))

    def test_replaces_updated_date_and_skips_unchanged_second_run(self):
        """Writing unchanged output or duplicating updated must fail this test."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = self.write_source(directory)
            destination_path = directory / "destination.md"
            destination_path.write_text(
                "---\n"
                'title: "Destination title"\n'
                "published: 2024-01-02\n"
                "updated: 2020-01-01\n"
                "description: Keep this value.\n"
                "---\n"
                "Old body.\n",
                encoding="utf-8",
            )

            self.assertTrue(sync_docs.sync_file(source_path, destination_path))
            first_content = destination_path.read_text(encoding="utf-8")
            self.assertFalse(sync_docs.sync_file(source_path, destination_path))

            self.assertEqual(destination_path.read_text(encoding="utf-8"), first_content)
            self.assertIn("published: 2024-01-02\n", first_content)
            self.assertIn("updated: 2026-07-31\n", first_content)
            self.assertIn("description: Keep this value.\n", first_content)
            self.assertEqual(first_content.count("updated:"), 1)


if __name__ == "__main__":
    unittest.main()
