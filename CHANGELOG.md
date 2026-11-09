# Changelog

All notable changes to theaios-core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-11-09

### Added

- `theaios.core.expressions.references(ast)`: the variables, matcher names and fields an
  expression uses, found without evaluating it. The libraries use it to reject configs that
  reference an undefined `$variable` or matcher at load time.

### Fixed

- Ordering comparisons (`>`, `<`, `>=`, `<=`) between a number and a string that spells a
  number now compare numerically: `"10000" > 5000` is true. Before, the number was turned into
  a string and compared character by character, so a cap like `amount > $max_transfer` let a
  string amount of `"10000"` through. Two numeric strings also compare as numbers.
- Ordering a number against something that is not one (`"10,000"`, `"abc"`, a list) now raises
  `ExpressionError` instead of guessing. The libraries treat a rule that raises as matched (fail
  closed). A missing value (null) is unchanged.
- `==`, `!=`, `in` and `not in` treat a number and a string that spells the same number as
  equal (`"1001" == 1001`, `"1001" in [1001, 1002]`), so a blocklist of ids cannot be bypassed by
  sending the id as a string. Two strings still compare as text (`"1.0" != "1"`).

## [0.1.0] - 2026-11-08

### Added

- `theaios.core.expressions`: the safe expression language previously copied into
  theaios-guardrails, theaios-context-router, theaios-agent-monitor and
  theaios-agent-auth (the four copies had identical code).
- Limits: expressions over 10,000 characters or nesting deeper than 64 levels raise
  `ExpressionError`; `and` / `or` chains are evaluated iteratively, so long chains no
  longer hit Python's recursion limit. Results are unchanged.
- `theaios.core.env`: `${VAR}` interpolation, with the `${VAR:default}` and strict-name
  dialects the libraries used.
- `theaios.core.audit`: append-only JSONL log with optional hash chaining and
  `python -m theaios.core.audit verify`.
