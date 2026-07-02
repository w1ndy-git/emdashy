"""Parser: decode em dash runs into an executable :class:`Program`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import ops
from .errors import ParseError
from .lexer import Token, lex


@dataclass
class Instr:
    """One decoded instruction with its source location."""

    name: str
    arg: Optional[int]
    line: int = 0
    col: int = 0

    def render(self, char_hint: bool = False) -> str:
        """Human-readable form, e.g. ``push 72`` or ``jmp L2``."""
        info = ops.BY_NAME[self.name]
        if info.arg_kind == "value":
            text = f"{self.name} {self.arg}"
            if char_hint and self.arg is not None and 32 <= self.arg < 127:
                ch = chr(self.arg).replace("\\", "\\\\").replace("'", "\\'")
                text += f"  '{ch}'"
            return text
        if info.arg_kind == "label":
            return f"{self.name} L{self.arg}"
        return self.name


@dataclass
class Program:
    """A decoded program: instructions plus the label table."""

    instrs: List[Instr] = field(default_factory=list)
    labels: Dict[int, int] = field(default_factory=dict)  # label id -> instr index
    source: str = "<source>"


def parse_tokens(tokens: List[Token], source: str = "<source>") -> Program:
    program = Program(source=source)
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        info = ops.BY_CODE.get(tok.length)
        if info is None:
            raise ParseError(
                f"a run of {tok.length} em dashes is not an instruction "
                f"(valid run lengths are 1..{ops.MAX_OPCODE})",
                source, tok.line, tok.col,
            )
        i += 1
        arg: Optional[int] = None
        if info.has_arg:
            if i >= n:
                raise ParseError(
                    f"'{info.name}' expects an operand run but the program ends",
                    source, tok.line, tok.col,
                )
            operand = tokens[i]
            i += 1
            arg = operand.length - 1 if info.arg_kind == "value" else operand.length
        index = len(program.instrs)
        program.instrs.append(Instr(info.name, arg, tok.line, tok.col))
        if info.name == "label":
            assert arg is not None
            if arg in program.labels:
                raise ParseError(
                    f"label L{arg} is declared more than once",
                    source, tok.line, tok.col,
                )
            program.labels[arg] = index

    for instr in program.instrs:
        if instr.name in ops.BRANCHES and instr.arg not in program.labels:
            raise ParseError(
                f"'{instr.name}' targets undeclared label L{instr.arg}",
                source, instr.line, instr.col,
            )
    return program


def parse_source(text: str, source: str = "<source>") -> Program:
    """Lex and parse raw Emdashy text."""
    return parse_tokens(lex(text), source)
