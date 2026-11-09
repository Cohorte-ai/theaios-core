# theaios-core

Shared foundations of the [theaios](https://github.com/Cohorte-ai) libraries. You do not
need to install it yourself: `theaios-guardrails`, `theaios-context-router`,
`theaios-agent-monitor` and `theaios-agent-auth` depend on it.

It exists so that security-sensitive code lives in one place instead of four copies.

## What is inside

| Module | What it does |
|---|---|
| `theaios.core.expressions` | The safe condition language used in policy files (`action == "send_email" and recipient.domain != $company_domain`). No `eval()`, no code execution. Limits: 10,000 characters and 64 levels of nesting; `and` / `or` chains of any length. |
| `theaios.core.env` | `${VAR}` interpolation for config files, with an optional `${VAR:default}` form. |
| `theaios.core.audit` | Append-only JSONL logs, optionally hash-chained so that any edit or deletion is detectable. |

```python
from theaios.core.expressions import compile_expression, evaluate

rule = compile_expression('amount > 1000 and currency in ["EUR", "USD"]')
evaluate(rule, {"amount": 4800, "currency": "EUR"})  # True
```

`references(rule)` lists the `$variables`, matchers and fields an expression uses without
evaluating it, so a library can reject a config that names something undefined (a typo in a
deny rule) when it loads, not when the rule is silently skipped at runtime.

```bash
python -m theaios.core.audit verify .guardrails_audit/audit.jsonl
```

## Compatibility

The expression language is the one the four libraries already used; their existing test
suites pass unchanged against this package. The only difference: input over the limits
above now raises `ExpressionError` instead of failing with a Python `RecursionError`.

Since 0.1.1, ordering comparisons treat strings that spell numbers as numbers (`"10000" > 5000`)
and raise `ExpressionError` when only one side is a number; `==`, `!=`, `in` and `not in`
treat `"1001"` and `1001` as equal.

## License

Apache 2.0. See [LICENSE](LICENSE).
