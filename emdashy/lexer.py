"""Lexer: turn Emdashy source text into a list of em dash runs.

The only meaningful character is the em dash (U+2014).  Every other
character — letters, digits, hyphens, en dashes, emoji — is a comment and
merely *separates* runs.  A token records the run's length and where it
started, for diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from . import EM_DASH


@dataclass(frozen=True)
class Token:
    length: int
    line: int
    col: int


def lex(text: str) -> List[Token]:
    """Split *text* into runs of consecutive em dashes."""
    tokens: List[Token] = []
    line, col = 1, 1
    run_len = 0
    run_line = run_col = 0
    for ch in text:
        if ch == EM_DASH:
            if run_len == 0:
                run_line, run_col = line, col
            run_len += 1
        elif run_len:
            tokens.append(Token(run_len, run_line, run_col))
            run_len = 0
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1
    if run_len:
        tokens.append(Token(run_len, run_line, run_col))
    return tokens
