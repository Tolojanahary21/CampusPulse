"""Tests de sûreté du helper d'archives, sans Docker ni données applicatives."""

import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import storage_archive

ROOT = Path(__file__).resolve().parents[1]


class StorageArchiveTests(unittest.TestCase):
    def setUp(self):
        self.test_root = ROOT / ".test-data"
        self.test_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="archive-check-", dir=self.test_root)
        self.workspace = Path(self.temporary.name).resolve()
        self.assertTrue(self.workspace.is_relative_to(self.test_root.resolve()))
        self.source = self.workspace / "source"
        self.destination = self.workspace / "destination"
        self.archive = self.workspace / "uploads.tar.gz"
        self.source.mkdir()

    def tearDown(self):
        # La suppression récursive ne concerne que notre répertoire temporaire
        # préalablement résolu et vérifié sous .test-data.
        self.assertTrue(self.workspace.is_relative_to(self.test_root.resolve()))
        self.temporary.cleanup()

    def run_helper(self, action, storage):
        with patch.object(sys, "argv", ["storage_archive.py", action, "--storage", str(storage), "--archive", str(self.archive)]):
            storage_archive.main()

    def test_roundtrip_preserves_private_files(self):
        (self.source / "nested").mkdir()
        (self.source / "nested" / "sample.txt").write_bytes(b"private sample\x00\xff")
        self.run_helper("backup", self.source)
        self.run_helper("verify", self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.run_helper("restore", self.destination)
        self.assertEqual((self.destination / "nested" / "sample.txt").read_bytes(), b"private sample\x00\xff")

    def test_refuses_path_traversal_before_writing(self):
        with tarfile.open(self.archive, "w:gz") as archive:
            entry = tarfile.TarInfo("../outside.txt")
            entry.size = 4
            archive.addfile(entry, io.BytesIO(b"evil"))
        with self.assertRaises(ValueError):
            self.run_helper("restore", self.destination)
        self.assertFalse((self.workspace / "outside.txt").exists())
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_refuses_symbolic_link(self):
        with tarfile.open(self.archive, "w:gz") as archive:
            entry = tarfile.TarInfo("link")
            entry.type = tarfile.SYMTYPE
            entry.linkname = "../outside"
            archive.addfile(entry)
        with self.assertRaises(ValueError):
            self.run_helper("restore", self.destination)

    def test_refuses_nonempty_destination(self):
        (self.source / "existing.txt").write_text("preserved", encoding="utf-8")
        self.run_helper("backup", self.source)
        with self.assertRaises(ValueError):
            self.run_helper("restore", self.source)
        self.assertEqual((self.source / "existing.txt").read_text(encoding="utf-8"), "preserved")


if __name__ == "__main__":
    unittest.main()
