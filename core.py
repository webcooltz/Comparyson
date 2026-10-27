"""Comparison logic for Comparyson, kept free of any GUI code."""

import difflib
import filecmp
import os
from dataclasses import dataclass
from typing import Optional

SAME = "same"
MODIFIED = "modified"
LEFT_ONLY = "left_only"
RIGHT_ONLY = "right_only"

MAX_TEXT_BYTES = 2 * 1024 * 1024  # files above this are not rendered
IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".idea", ".vscode"}


@dataclass(frozen=True)
class Entry:
    rel: str  # forward-slash path relative to the compared roots
    status: str


@dataclass(frozen=True)
class Row:
    """One aligned line pair. A side is None when it has no line here."""
    left_no: Optional[int]
    left: Optional[str]
    right_no: Optional[int]
    right: Optional[str]
    tag: str  # equal | replace | delete | insert
    left_spans: tuple = ()  # intra-line (start, end) changes
    right_spans: tuple = ()


def _walk_files(root):
    found = set()
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in files:
            full = os.path.join(base, name)
            found.add(os.path.relpath(full, root).replace(os.sep, "/"))
    return found


def scan(left_root, right_root):
    """Recursively compare two directories; returns entries sorted by path."""
    for root in (left_root, right_root):
        if not os.path.isdir(root):
            raise NotADirectoryError(f"Not a directory: {root}")

    left, right = _walk_files(left_root), _walk_files(right_root)
    entries = []
    for rel in sorted(left | right, key=str.lower):
        if rel not in right:
            status = LEFT_ONLY
        elif rel not in left:
            status = RIGHT_ONLY
        else:
            try:
                same = filecmp.cmp(os.path.join(left_root, rel),
                                   os.path.join(right_root, rel), shallow=False)
            except OSError:
                same = False
            status = SAME if same else MODIFIED
        entries.append(Entry(rel, status))
    return entries


def read_lines(path):
    """Return (lines, note). lines is None when the file can't be displayed."""
    if not path or not os.path.isfile(path):
        return [], None
    try:
        if os.path.getsize(path) > MAX_TEXT_BYTES:
            return None, "File is too large to display (over 2 MB)."
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        return None, f"Cannot read file: {exc.strerror or exc}"
    if b"\0" in data:
        return None, "Binary file - contents not shown."
    text = data.decode("utf-8", errors="replace")
    return text.splitlines(), None


def _char_spans(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    left, right = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        if i2 > i1:
            left.append((i1, i2))
        if j2 > j1:
            right.append((j1, j2))
    return tuple(left), tuple(right)


def align(left_lines, right_lines):
    """Build side-by-side rows; changed blocks are paired line by line."""
    rows = []
    sm = difflib.SequenceMatcher(None, left_lines, right_lines, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                rows.append(Row(i1 + k + 1, left_lines[i1 + k],
                                j1 + k + 1, right_lines[j1 + k], "equal"))
            continue
        span = max(i2 - i1, j2 - j1)
        for k in range(span):
            li, rj = i1 + k, j1 + k
            has_l, has_r = li < i2, rj < j2
            a = left_lines[li] if has_l else None
            b = right_lines[rj] if has_r else None
            if has_l and has_r:
                ls, rs = _char_spans(a, b)
                rows.append(Row(li + 1, a, rj + 1, b, "replace", ls, rs))
            elif has_l:
                rows.append(Row(li + 1, a, None, None, "delete"))
            else:
                rows.append(Row(None, None, rj + 1, b, "insert"))
    return rows


def hunk_starts(rows):
    """Indices of the first row of each contiguous changed block."""
    starts, prev_changed = [], False
    for i, row in enumerate(rows):
        changed = row.tag != "equal"
        if changed and not prev_changed:
            starts.append(i)
        prev_changed = changed
    return starts
