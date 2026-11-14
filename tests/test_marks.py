"""Marks: unforgeable, per process."""

from __future__ import annotations

import subprocess
import sys

from theaios.core.marks import is_marked, mark


def test_the_mark_is_recognised_and_stable_in_a_process() -> None:
    assert is_marked(mark()) and mark() == mark()


def test_anything_else_is_not() -> None:
    for value in (
        None,
        "",
        "theaios",
        mark()[:-1],
        mark() + "x",
        mark().upper(),
        1,
        {"mark": mark()},
    ):
        assert not is_marked(value), value


def test_another_process_has_another_mark() -> None:
    other = subprocess.run(
        [sys.executable, "-c", "from theaios.core.marks import mark; print(mark())"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert len(other) == 32 and not is_marked(other)
