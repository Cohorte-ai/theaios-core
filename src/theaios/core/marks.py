"""Unforgeable marks for decisions the theaios libraries hand to each other in one process.

A middleware that refuses a tool call returns a message carrying a structured decision. A
middleware outside it must tell such a refusal from a message a tool returned, whose content
may come from anywhere (a fetched error body, a document). A dict key alone can be forged by
content; a mark cannot: it is a secret generated once per process, never derived from input.

    from theaios.core.marks import mark, is_marked

    artifact = {"theaios": {"component": "guardrails", "mark": mark(), ...}}
    if is_marked(detail.get("mark")): ...   # made by a theaios library in this process

The mark is meaningful only in the process that made it (a restart makes a new one): check it
right after the call returns, never from a stored copy. Do not log or export it.
"""

from __future__ import annotations

import hmac
import secrets

_MARK = secrets.token_hex(16)


def mark() -> str:
    """This process's mark."""
    return _MARK


def is_marked(value: object) -> bool:
    """True only for this process's mark (compared in constant time)."""
    return isinstance(value, str) and hmac.compare_digest(value, _MARK)
