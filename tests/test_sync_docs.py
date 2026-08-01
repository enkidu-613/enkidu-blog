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


class SyncFileMetadataTests(unittest.TestCase):
    """Ensure source metadata is synchronized into post frontmatter."""

    def write_source(self, directory):
        source_path = directory / "source.md"
        source_path.write_text("# Source title\n\nSource body.\n", encoding="utf-8")
        os.utime(source_path, (SHANGHAI_2026_07_31_EPOCH, SHANGHAI_2026_07_31_EPOCH))
        return source_path

    def test_inserts_section_and_replaces_published_from_source_mtime(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = self.write_source(directory)
            destination_path = directory / "destination.md"
            destination_path.write_text(
                "---\n"
                'title: "Destination title"\n'
                "published: 2024-01-02\n"
                "updated: 2020-01-01\n"
                "draft: false\n"
                "---\n"
                "Old body.\n",
                encoding="utf-8",
            )
            self.assertTrue(sync_docs.sync_file(source_path, destination_path, "main"))
            content = destination_path.read_text(encoding="utf-8")
            self.assertIn("published: 2026-07-31\n", content)
            self.assertIn("section: main\n", content)
            self.assertNotIn("updated:", content)
            self.assertIn("draft: false\n", content)

    def test_replaces_stale_section_preserves_metadata_and_skips_unchanged_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = self.write_source(directory)
            destination_path = directory / "destination.md"
            destination_path.write_text(
                "---\n"
                'title: "Destination title"\n'
                "published: 2024-01-02\n"
                "section: supplement\n"
                "updated: 2020-01-01\n"
                "description: Keep this value.\n"
                "---\n"
                "Old body.\n",
                encoding="utf-8",
            )
            self.assertTrue(sync_docs.sync_file(source_path, destination_path, "main"))
            first_content = destination_path.read_text(encoding="utf-8")
            self.assertFalse(sync_docs.sync_file(source_path, destination_path, "main"))
            self.assertEqual(destination_path.read_text(encoding="utf-8"), first_content)
            self.assertIn("published: 2026-07-31\n", first_content)
            self.assertIn("section: main\n", first_content)
            self.assertNotIn("updated:", first_content)
            self.assertIn("description: Keep this value.\n", first_content)


if __name__ == "__main__":
    unittest.main()
