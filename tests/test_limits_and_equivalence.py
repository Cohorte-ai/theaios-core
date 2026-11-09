"""Safety limits, and proof that iterative and/or evaluation matches the pairwise rule."""

from __future__ import annotations

import itertools
import random

import pytest

from theaios.core.expressions import (
    MAX_EXPRESSION_LENGTH,
    MAX_NESTING_DEPTH,
    BinaryOp,
    BoolLiteral,
    ExpressionError,
    compile_expression,
    evaluate,
)


def test_overlong_expression_is_rejected_cleanly() -> None:
    with pytest.raises(ExpressionError, match="longer than"):
        compile_expression("a == 1 or " * (MAX_EXPRESSION_LENGTH // 10 + 1) + "a == 1")


@pytest.mark.parametrize("opener,closer", [("(", ")"), ("[", "]"), ("not ", "")])
def test_deep_nesting_is_rejected_cleanly(opener: str, closer: str) -> None:
    depth = MAX_NESTING_DEPTH + 1
    with pytest.raises(ExpressionError, match="nests deeper"):
        compile_expression(opener * depth + "true" + closer * depth)


@pytest.mark.parametrize("opener,closer", [("(", ")"), ("[", "]"), ("not ", "")])
def test_nesting_at_the_limit_still_works(opener: str, closer: str) -> None:
    depth = MAX_NESTING_DEPTH
    ast = compile_expression(opener * depth + "true" + closer * depth)
    evaluate(ast, {})


def test_long_chains_evaluate_without_recursion_error() -> None:
    terms = 1600  # past Python's default recursion limit, within the length limit
    ors = compile_expression(" or ".join(["x"] * terms) + " or y")
    assert len(" and ".join(["x"] * terms)) < MAX_EXPRESSION_LENGTH
    assert evaluate(ors, {"x": False, "y": True}) is True
    assert evaluate(ors, {"x": False, "y": False}) is False
    ands = compile_expression(" and ".join(["x"] * terms))
    assert evaluate(ands, {"x": True}) is True
    assert evaluate(ands, {"x": 0}) is False


def _pairwise(node: object, values: dict[str, object]) -> object:
    """The original evaluation rule, kept here as the reference."""
    if isinstance(node, BinaryOp) and node.op == "and":
        left = _pairwise(node.left, values)
        return False if not left else bool(_pairwise(node.right, values))
    if isinstance(node, BinaryOp) and node.op == "or":
        left = _pairwise(node.left, values)
        return True if left else bool(_pairwise(node.right, values))
    return evaluate(node, values)  # type: ignore[arg-type]


def test_iterative_and_or_matches_pairwise_rule_exhaustively() -> None:
    rng = random.Random(7)
    names = ["a", "b", "c", "d"]
    for _ in range(300):
        parts = [rng.choice(names) for _ in range(rng.randint(1, 6))]
        ops = [rng.choice(["and", "or"]) for _ in parts[1:]]
        text = parts[0]
        for op, part in zip(ops, parts[1:], strict=True):
            text = f"({text}) {op} {part}" if rng.random() < 0.3 else f"{text} {op} {part}"
        ast = compile_expression(text)
        for combo in itertools.product([True, False, 0, "", "x", None], repeat=len(names)):
            values = dict(zip(names, combo, strict=True))
            assert evaluate(ast, values) == _pairwise(ast, values), text


def test_short_circuit_still_skips_undefined_variables() -> None:
    assert evaluate(compile_expression("false and $missing"), {}) is False
    assert evaluate(compile_expression("true or $missing"), {}) is True
    with pytest.raises(ExpressionError, match="Undefined variable"):
        evaluate(compile_expression("true and $missing"), {})


def test_empty_expression_is_always_true() -> None:
    assert isinstance(compile_expression("   "), BoolLiteral)


def test_references_finds_variables_matchers_and_fields() -> None:
    from theaios.core.expressions import references

    refs = references(
        compile_expression(
            'content matches pii and not (amount > $max or user.role in [$admin, "ops"]) '
            'or note matches "injection"'
        )
    )
    assert refs.variables == {"max", "admin"}
    assert refs.matchers == {"pii", "injection"}
    assert refs.fields == {"content", "amount", "user.role", "note"}  # matcher names excluded


def test_references_handles_long_chains_without_recursion() -> None:
    from theaios.core.expressions import references

    refs = references(compile_expression(" or ".join(f"x == $v{i}" for i in range(500))))
    assert len(refs.variables) == 500


def test_numeric_strings_compare_as_numbers() -> None:
    cap = compile_expression("amount > $max")
    assert evaluate(cap, {"amount": "10000"}, variables={"max": 5000}) is True
    assert evaluate(cap, {"amount": "600"}, variables={"max": 5000}) is False
    assert evaluate(cap, {"amount": 10000}, variables={"max": "5000"}) is True
    assert evaluate(cap, {"amount": " 10000.5 "}, variables={"max": 5000}) is True
    assert evaluate(compile_expression('a < "9"'), {"a": "10"}) is False  # both numeric strings


def test_number_against_non_number_raises() -> None:
    cap = compile_expression("amount > 5000")
    for bad in ["10,000", "abc", [9999], {"x": 1}, "nan", "inf"]:
        with pytest.raises(ExpressionError, match="cannot order"):
            evaluate(cap, {"amount": bad})


def test_missing_and_plain_strings_unchanged() -> None:
    assert evaluate(compile_expression("amount > 5000"), {}) is False
    assert evaluate(compile_expression('name > "m"'), {"name": "zed"}) is True
    assert evaluate(compile_expression('day >= "2026-11-01"'), {"day": "2026-11-09"}) is True
