import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import core


def write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class ScanTests(unittest.TestCase):
    def test_statuses_and_subdirs(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write(a, "same.txt", "x")
            write(b, "same.txt", "x")
            write(a, "mod.txt", "1")
            write(b, "mod.txt", "2")
            write(a, "sub/left.txt", "l")
            write(b, "sub/right.txt", "r")
            got = {e.rel: e.status for e in core.scan(a, b)}
        self.assertEqual(
            got,
            {
                "same.txt": core.SAME,
                "mod.txt": core.MODIFIED,
                "sub/left.txt": core.LEFT_ONLY,
                "sub/right.txt": core.RIGHT_ONLY,
            },
        )

    def test_missing_dir(self):
        with self.assertRaises(NotADirectoryError):
            core.scan("/nope/a", "/nope/b")


class DiffTests(unittest.TestCase):
    def test_align_pads_and_hunks(self):
        rows = core.align(["a", "b", "c"], ["a", "x", "c", "d"])
        self.assertEqual([r.tag for r in rows], ["equal", "replace", "equal", "insert"])
        self.assertEqual(core.hunk_starts(rows), [1, 3])
        self.assertIsNone(rows[3].left)

    def test_binary_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.bin")
            with open(p, "wb") as fh:
                fh.write(b"\0\1\2")
            lines, note = core.read_lines(p)
            self.assertIsNone(lines)
            self.assertTrue(note)
            self.assertEqual(core.read_lines(os.path.join(d, "none"))[0], [])


if __name__ == "__main__":
    unittest.main()
