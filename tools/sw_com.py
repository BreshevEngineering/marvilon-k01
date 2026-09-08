r"""
Small SOLIDWORKS/pywin32 compatibility layer for K01.

Why this exists
---------------
In the user's SOLIDWORKS 2026 + late-bound pywin32 environment, some COM
members with method-like names are exposed already evaluated:

    model.GetType       -> int
    model.GetTitle      -> str
    model.GetEquationMgr-> COM object
    model.FirstFeature  -> COM object
    comp.GetPathName    -> str

Calling those values again causes errors such as:
    TypeError: 'int' object is not callable
    TypeError: 'str' object is not callable
    Member not found

`member0()` handles zero-argument members safely and records any real error.
`call()` is for members that genuinely require arguments.
"""

from __future__ import annotations
from typing import Any


_PRIMITIVES = (str, int, float, bool, tuple, list, dict, bytes)


def is_com_object(value: Any) -> bool:
    return hasattr(value, "_oleobj_")


def member0(obj: Any, name: str, default=None) -> tuple[Any, str | None]:
    """Read/call a zero-argument COM member without double-invoking values."""
    try:
        attr = getattr(obj, name)
    except Exception as exc:
        return default, f"{name}: getattr: {type(exc).__name__}: {exc}"

    if attr is None:
        return None, None

    if isinstance(attr, _PRIMITIVES):
        return attr, None

    # A returned COM interface is already the result; do not invoke its
    # default dispatch member.
    if is_com_object(attr):
        return attr, None

    if callable(attr):
        try:
            return attr(), None
        except Exception as exc:
            return default, f"{name}: call: {type(exc).__name__}: {exc}"

    return attr, None


def value0(obj: Any, name: str, default=None):
    """Convenience wrapper when the caller does not need an error string."""
    return member0(obj, name, default=default)[0]


def call(obj: Any, name: str, *args, default=None) -> tuple[Any, str | None]:
    """Call a COM member that requires one or more arguments."""
    try:
        attr = getattr(obj, name)
    except Exception as exc:
        return default, f"{name}: getattr: {type(exc).__name__}: {exc}"

    if not callable(attr):
        return default, (
            f"{name}: expected callable for args={args!r}, got {type(attr).__name__}"
        )

    try:
        return attr(*args), None
    except Exception as exc:
        return default, f"{name}: call: {type(exc).__name__}: {exc}"


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, (tuple, list)):
        return list(value)
    try:
        return list(value)
    except Exception:
        return [value]
