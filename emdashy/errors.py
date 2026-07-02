"""Error types shared by the whole Emdashy toolchain.

Every error carries an optional source location so the CLI can print
``file:line:col: message`` diagnostics.
"""

from __future__ import annotations

from typing import Optional


class EmdashyError(Exception):
    """Base class for all toolchain errors."""

    kind = "error"

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        line: Optional[int] = None,
        col: Optional[int] = None,
    ) -> None:
        self.message = message
        self.source = source
        self.line = line
        self.col = col
        super().__init__(self.formatted())

    def formatted(self) -> str:
        loc = self.source or ""
        if self.line is not None:
            loc += f":{self.line}"
            if self.col is not None:
                loc += f":{self.col}"
        if loc:
            return f"{loc}: {self.kind}: {self.message}"
        return f"{self.kind}: {self.message}"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.formatted()


class ParseError(EmdashyError):
    """Malformed em dash source (unknown opcode, missing operand, ...)."""

    kind = "parse error"


class AsmError(EmdashyError):
    """Malformed assembly source."""

    kind = "assembly error"


class EmdashyRuntimeError(EmdashyError):
    """A program failed while executing (underflow, division by zero, ...)."""

    kind = "runtime error"
