"""A tiny Result type for operations whose failure is expected and routine
(command timeout, NACK) — as opposed to genuine faults, which raise typed
exceptions. Keeps protocol call sites free of broad try/except.

Construct directly: ``Result(ok=True, value=x)`` / ``Result(ok=False, error=e)``.
Inside a function annotated ``-> Result[int]`` the element type is inferred from
the return type, so the failure form needs no explicit parameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Result(Generic[T]):
    ok: bool
    value: T | None = None
    error: str | None = None
