from __future__ import annotations

import json
from pathlib import Path

from theaios.core.audit import JsonlLog, main, verify_chain


def test_plain_log_writes_entries_unchanged(tmp_path: Path) -> None:
    log = JsonlLog(tmp_path / "a" / "audit.jsonl")
    written = log.append({"agent": "x", "outcome": "deny"})
    assert written == {"agent": "x", "outcome": "deny"}
    assert json.loads(log.path.read_text()) == {"agent": "x", "outcome": "deny"}


def test_read_filters_limit_and_skips_bad_lines(tmp_path: Path) -> None:
    log = JsonlLog(tmp_path / "audit.jsonl")
    for i in range(5):
        log.append({"i": i, "agent": "a" if i % 2 else "b"})
    with open(log.path, "a") as f:
        f.write("not json\n\n[1,2]\n")
    assert [e["i"] for e in log.read(lambda e: e["agent"] == "a")] == [1, 3]
    assert len(log.read(limit=2)) == 2
    log.clear()
    assert log.read() == []


def test_chained_log_verifies_and_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = JsonlLog(path, chain=True)
    for i in range(4):
        log.append({"i": i})
    assert verify_chain(path) == (True, 4)
    # a new writer continues the same chain
    JsonlLog(path, chain=True).append({"i": 4})
    assert verify_chain(path) == (True, 5)
    lines = path.read_text().splitlines()
    lines[2] = lines[2].replace('"i": 2', '"i": 9')
    path.write_text("\n".join(lines) + "\n")
    assert verify_chain(path) == (False, 2)
    assert main(["verify", str(path)]) == 1


def test_deleting_an_entry_breaks_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = JsonlLog(path, chain=True)
    for i in range(3):
        log.append({"i": i})
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert verify_chain(path) == (False, 1)


def test_cli_missing_file_is_an_error_not_intact(tmp_path: Path) -> None:
    assert main(["verify", str(tmp_path / "deleted.jsonl")]) == 2
    assert main(["verify", str(tmp_path)]) == 2


def test_cli_unchained_log_is_reported_as_such(tmp_path: Path) -> None:
    path = tmp_path / "plain.jsonl"
    log = JsonlLog(path)
    log.append({"event": "a"})
    assert main(["verify", str(path)]) == 2
