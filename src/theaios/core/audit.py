"""Append-only JSONL logs, optionally hash-chained so tampering is detectable.

Each library decides what goes into an entry; this module only writes, reads and
verifies. With ``chain=True`` every entry gets ``prev_hash`` and ``hash`` fields:
``hash = sha256(prev_hash + canonical JSON of the entry without "hash")``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

GENESIS = "0" * 64
Entry = dict[str, object]


def _digest(prev: str, entry: Entry) -> str:
    body = json.dumps(entry, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


class JsonlLog:
    """One JSON object per line, append only."""

    def __init__(self, path: str | Path, *, chain: bool = False) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._chain = chain
        self._last: str | None = None

    @property
    def path(self) -> Path:
        return self._path

    def _last_hash(self) -> str:
        if self._last is None:
            self._last = GENESIS
            for entry in self.entries():
                found = entry.get("hash")
                if isinstance(found, str):
                    self._last = found
        return self._last

    def append(self, entry: Mapping[str, object]) -> Entry:
        """Write one entry and return it as written (with hash fields when chained)."""
        record = dict(entry)
        if self._chain:
            record.pop("hash", None)
            record["prev_hash"] = self._last_hash()
            record["hash"] = _digest(str(record["prev_hash"]), record)
            self._last = str(record["hash"])
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return record

    def entries(self) -> Iterator[Entry]:
        """Yield entries in order, skipping blank and malformed lines."""
        if not self._path.exists():
            return
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    loaded = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(loaded, dict):
                    yield loaded

    def read(self, where: Callable[[Entry], bool] | None = None, limit: int = 1000) -> list[Entry]:
        """Entries matching ``where``, oldest first, at most ``limit``."""
        out: list[Entry] = []
        for entry in self.entries():
            if where is None or where(entry):
                out.append(entry)
                if len(out) >= limit:
                    break
        return out

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
        self._last = None


def verify_chain(path: str | Path) -> tuple[bool, int]:
    """Check a chained log. Returns (intact, number of entries verified before a break)."""
    prev, count = GENESIS, 0
    p = Path(path)
    if not p.exists():
        return True, 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False, count
            if not isinstance(entry, dict):
                return False, count
            claimed = entry.pop("hash", None)
            if entry.get("prev_hash") != prev or claimed != _digest(prev, entry):
                return False, count
            prev, count = str(claimed), count + 1
    return True, count


def main(argv: list[str] | None = None) -> int:
    """``python -m theaios.core.audit verify <file>``"""
    import sys

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] != "verify":
        print("usage: python -m theaios.core.audit verify <file.jsonl>")
        return 2
    path = Path(args[1])
    # A missing log is not an intact one: deleting the whole file must not pass the check.
    if not path.is_file():
        print(f"error: {path} does not exist or is not a file")
        return 2
    if not _is_chained(path):
        print(
            f"error: {path} is not hash-chained (it was written without chain=True), "
            "so it cannot be verified"
        )
        return 2
    intact, count = verify_chain(path)
    print(f"{'intact' if intact else 'BROKEN'}: {count} entries verified")
    return 0 if intact else 1


def _is_chained(path: Path) -> bool:
    """Whether the first entry carries the chain fields."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    return True  # let verify_chain report the corruption
                return isinstance(entry, dict) and "hash" in entry and "prev_hash" in entry
    return True  # an existing empty file: verify_chain reports 0 entries


if __name__ == "__main__":
    raise SystemExit(main())
