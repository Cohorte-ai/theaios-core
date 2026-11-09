from __future__ import annotations

from theaios.core.env import interpolate_env, interpolate_recursive

ENV = {"HOST": "db.local", "_X1": "v", "1ABC": "digit"}


def test_plain_substitution_and_unset_left_as_written() -> None:
    assert interpolate_env("${HOST}:5432 ${NOPE}", environ=ENV) == "db.local:5432 ${NOPE}"


def test_default_syntax_only_when_enabled() -> None:
    text = "${NOPE:fallback} ${HOST:other}"
    assert interpolate_env(text, environ=ENV) == text  # agent-auth / context-router dialect
    assert interpolate_env(text, defaults=True, environ=ENV) == "fallback db.local"
    assert interpolate_env("${NOPE:}", defaults=True, environ=ENV) == ""


def test_strict_names_reject_leading_digit() -> None:
    assert interpolate_env("${1ABC}", environ=ENV) == "digit"
    assert interpolate_env("${1ABC}", strict_names=True, environ=ENV) == "${1ABC}"
    assert interpolate_env("${_X1}", strict_names=True, environ=ENV) == "v"


def test_recursive_walks_dicts_and_lists_and_keeps_other_types() -> None:
    raw = {"a": ["${HOST}", 3, {"b": "${HOST}"}], "c": None, "${HOST}": True}
    assert interpolate_recursive(raw, environ=ENV) == {
        "a": ["db.local", 3, {"b": "db.local"}],
        "c": None,
        "${HOST}": True,
    }
