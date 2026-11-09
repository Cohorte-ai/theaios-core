"""``${VAR}`` interpolation for theaios configuration files.

Interpolate after a config has been parsed and validated once, so a malformed file is
rejected before any environment value can appear in an error message.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

_STRICT = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_WORD = re.compile(r"\$\{(\w+)\}")
_WORD_WITH_DEFAULT = re.compile(r"\$\{(\w+)(?::([^}]*))?\}")


def interpolate_env(
    value: str,
    *,
    defaults: bool = False,
    strict_names: bool = False,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Replace ``${VAR}`` with the variable's value. Unset variables stay as written.

    defaults: also accept ``${VAR:default}``, used when VAR is unset.
    strict_names: names must start with a letter or underscore and contain only ASCII
        letters, digits and underscores. Ignored when ``defaults`` is true.
    """
    env = os.environ if environ is None else environ
    if defaults:

        def _with_default(m: re.Match[str]) -> str:
            found = env.get(m.group(1))
            if found is not None:
                return found
            return m.group(2) if m.group(2) is not None else m.group(0)

        return _WORD_WITH_DEFAULT.sub(_with_default, value)
    pattern = _STRICT if strict_names else _WORD
    return pattern.sub(lambda m: env.get(m.group(1), m.group(0)), value)


def interpolate_recursive(
    obj: object,
    *,
    defaults: bool = False,
    strict_names: bool = False,
    environ: Mapping[str, str] | None = None,
) -> object:
    """Apply :func:`interpolate_env` to every string inside dicts and lists."""
    if isinstance(obj, str):
        return interpolate_env(obj, defaults=defaults, strict_names=strict_names, environ=environ)
    if isinstance(obj, dict):
        return {
            k: interpolate_recursive(
                v, defaults=defaults, strict_names=strict_names, environ=environ
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [
            interpolate_recursive(v, defaults=defaults, strict_names=strict_names, environ=environ)
            for v in obj
        ]
    return obj
