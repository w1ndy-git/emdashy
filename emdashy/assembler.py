"""Assembler: human-readable Emdashy assembly (``.emda``) -> em dashes.

Nobody should have to count em dashes by hand.  The assembly language is
a thin, friendly skin over the instruction set:

* one instruction per whitespace-separated token pair (mnemonics are not
  line-oriented, so ``push 3 push 4 add`` on one line is fine);
* ``;`` and ``#`` start comments that run to the end of the line;
* labels are *names*: declare with ``name:`` (or ``label name``), target
  with ``jmp name`` / ``jz name`` / ``jnz name`` / ``call name``;
* ``push`` accepts decimal, ``0x``/``0b`` prefixed, and character
  literals such as ``'A'`` or ``'\\n'``; negative literals expand to a
  push + ``neg``; literals above 255 expand to a short push/mul/add
  sequence so the em dash file stays sane;
* ``prints "text"`` is a macro that prints a string literal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Union

from . import EM_DASH, ops
from .errors import AsmError
from .parser import Instr, Program

#: Largest literal emitted as a single unary run (a run of 256 dashes).
MAX_DIRECT_LITERAL = 255

_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "0": "\0",
    "\\": "\\", "'": "'", '"': '"', "e": "\x1b",
}


@dataclass(frozen=True)
class _Tok:
    kind: str  # "word", "str", "char", "labeldef"
    value: Union[str, int]
    line: int
    col: int


def _tokenize(text: str, source: str) -> List[_Tok]:
    tokens: List[_Tok] = []
    line, col = 1, 0
    i, n = 0, len(text)

    def bump(ch: str) -> None:
        nonlocal line, col
        if ch == "\n":
            line += 1
            col = 0
        else:
            col += 1

    def read_escape(start_line: int, start_col: int) -> str:
        nonlocal i
        if i >= n:
            raise AsmError("unterminated escape sequence", source, start_line, start_col)
        ch = text[i]
        i += 1
        bump(ch)
        if ch == "x":
            hexs = text[i:i + 2]
            if len(hexs) != 2 or any(c not in "0123456789abcdefABCDEF" for c in hexs):
                raise AsmError("\\x escape expects two hex digits", source, start_line, start_col)
            for c in hexs:
                i += 1
                bump(c)
            return chr(int(hexs, 16))
        if ch in _ESCAPES:
            return _ESCAPES[ch]
        raise AsmError(f"unknown escape sequence '\\{ch}'", source, start_line, start_col)

    while i < n:
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
            bump(ch)
            continue
        if ch in ";#":
            while i < n and text[i] != "\n":
                i += 1
                col += 1
            continue
        start_line, start_col = line, col + 1
        if ch == '"':
            i += 1
            bump(ch)
            parts: List[str] = []
            while True:
                if i >= n or text[i] == "\n":
                    raise AsmError("unterminated string literal", source, start_line, start_col)
                c = text[i]
                i += 1
                bump(c)
                if c == '"':
                    break
                if c == "\\":
                    parts.append(read_escape(start_line, start_col))
                else:
                    parts.append(c)
            tokens.append(_Tok("str", "".join(parts), start_line, start_col))
            continue
        if ch == "'":
            i += 1
            bump(ch)
            if i >= n or text[i] == "\n":
                raise AsmError("unterminated character literal", source, start_line, start_col)
            c = text[i]
            i += 1
            bump(c)
            value = read_escape(start_line, start_col) if c == "\\" else c
            if i >= n or text[i] != "'":
                raise AsmError("character literal must contain exactly one character",
                               source, start_line, start_col)
            i += 1
            bump("'")
            tokens.append(_Tok("char", ord(value), start_line, start_col))
            continue
        # bare word: mnemonic, number, or label
        word_chars: List[str] = []
        while i < n and text[i] not in " \t\r\n;#\"'":
            word_chars.append(text[i])
            bump(text[i])
            i += 1
        word = "".join(word_chars)
        if word.endswith(":") and len(word) > 1:
            tokens.append(_Tok("labeldef", word[:-1], start_line, start_col))
        else:
            tokens.append(_Tok("word", word, start_line, start_col))
    return tokens


def _parse_int(word: str) -> Optional[int]:
    try:
        return int(word, 0)
    except ValueError:
        return None


def _expand_push(value: int, line: int, col: int) -> List[Instr]:
    """Lower an integer literal into core instructions.

    Values 0..MAX_DIRECT_LITERAL become one ``push``.  Larger magnitudes
    are built digit-by-digit (``acc = acc * 10 + digit``) so a million is
    a handful of runs instead of a million and one dashes.  Negative
    values push the magnitude and negate.
    """
    if value < 0:
        return _expand_push(-value, line, col) + [Instr("neg", None, line, col)]
    if value <= MAX_DIRECT_LITERAL:
        return [Instr("push", value, line, col)]
    digits = str(value)
    out = [Instr("push", int(digits[0]), line, col)]
    for d in digits[1:]:
        out.append(Instr("push", 10, line, col))
        out.append(Instr("mul", None, line, col))
        out.append(Instr("push", int(d), line, col))
        out.append(Instr("add", None, line, col))
    return out


class LabelSpace:
    """Maps symbolic label names to numeric label ids (1-based)."""

    def __init__(self) -> None:
        self.ids: Dict[str, int] = {}
        self.defined: Set[str] = set()

    def id_for(self, name: str) -> int:
        if name not in self.ids:
            self.ids[name] = len(self.ids) + 1
        return self.ids[name]


def parse_assembly(
    text: str,
    source: str = "<asm>",
    labels: Optional[LabelSpace] = None,
) -> Tuple[List[Instr], LabelSpace]:
    """Parse assembly text into core instructions with numeric labels.

    Passing an existing :class:`LabelSpace` lets callers (the REPL)
    accumulate label definitions across separate snippets.
    """
    labels = labels or LabelSpace()
    tokens = _tokenize(text, source)
    instrs: List[Instr] = []
    referenced: List[Tuple[str, int, int, str]] = []  # name, line, col, mnemonic
    defined_here: Set[str] = set()

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        i += 1
        if tok.kind == "labeldef":
            name = str(tok.value)
            if name in defined_here or name in labels.defined:
                raise AsmError(f"label '{name}' is declared more than once",
                               source, tok.line, tok.col)
            defined_here.add(name)
            instrs.append(Instr("label", labels.id_for(name), tok.line, tok.col))
            continue
        if tok.kind != "word":
            raise AsmError(f"unexpected {tok.kind} literal", source, tok.line, tok.col)
        word = str(tok.value).lower()

        if word == "prints":
            if i >= len(tokens) or tokens[i].kind != "str":
                raise AsmError("'prints' expects a string literal", source, tok.line, tok.col)
            for ch in str(tokens[i].value):
                instrs.extend(_expand_push(ord(ch), tok.line, tok.col))
                instrs.append(Instr("outc", None, tok.line, tok.col))
            i += 1
            continue

        info = ops.BY_NAME.get(word)
        if info is None:
            raise AsmError(f"unknown mnemonic '{tok.value}'", source, tok.line, tok.col)

        if not info.has_arg:
            instrs.append(Instr(info.name, None, tok.line, tok.col))
            continue

        if i >= len(tokens):
            raise AsmError(f"'{info.name}' expects an operand", source, tok.line, tok.col)
        operand = tokens[i]
        i += 1

        if info.arg_kind == "value":
            if operand.kind == "char":
                value: Optional[int] = int(operand.value)
            elif operand.kind == "word":
                value = _parse_int(str(operand.value))
            else:
                value = None
            if value is None:
                raise AsmError(
                    f"'{info.name}' expects an integer or character literal, "
                    f"got '{operand.value}'",
                    source, operand.line, operand.col,
                )
            instrs.extend(_expand_push(value, tok.line, tok.col))
            continue

        # label operand
        if operand.kind != "word" or _parse_int(str(operand.value)) is not None:
            raise AsmError(f"'{info.name}' expects a label name", source, operand.line, operand.col)
        name = str(operand.value)
        if info.name == "label":
            if name in defined_here or name in labels.defined:
                raise AsmError(f"label '{name}' is declared more than once",
                               source, tok.line, tok.col)
            defined_here.add(name)
        else:
            referenced.append((name, operand.line, operand.col, info.name))
        instrs.append(Instr(info.name, labels.id_for(name), tok.line, tok.col))

    for name, line, col, mnemonic in referenced:
        if name not in defined_here and name not in labels.defined:
            raise AsmError(f"'{mnemonic}' targets undeclared label '{name}'",
                           source, line, col)
    labels.defined.update(defined_here)
    return instrs, labels


def build_program(instrs: List[Instr], source: str) -> Program:
    program = Program(instrs=list(instrs), source=source)
    for index, instr in enumerate(program.instrs):
        if instr.name == "label":
            program.labels[instr.arg] = index  # type: ignore[index]
    return program


def assemble_program(text: str, source: str = "<asm>") -> Program:
    """Assemble ``.emda`` text straight into an executable Program."""
    instrs, _ = parse_assembly(text, source)
    return build_program(instrs, source)


def emit_text(instrs: List[Instr], annotate: bool = True) -> str:
    """Render core instructions as Emdashy source (runs of em dashes).

    With ``annotate`` (the default) each line carries the mnemonic as a
    trailing comment.  Comments are legal Emdashy — every non-em-dash
    character is ignored — so annotated output is still a pure program.
    """
    lines: List[str] = []
    for instr in instrs:
        info = ops.BY_NAME[instr.name]
        runs = EM_DASH * info.opcode
        if info.arg_kind == "value":
            runs += " " + EM_DASH * (instr.arg + 1)  # type: ignore[operator]
        elif info.arg_kind == "label":
            runs += " " + EM_DASH * instr.arg  # type: ignore[operator]
        if annotate:
            runs += f"  ; {instr.render(char_hint=True)}"
        lines.append(runs)
    return "\n".join(lines) + ("\n" if lines else "")


def assemble_text(text: str, source: str = "<asm>", annotate: bool = True) -> str:
    """Assemble ``.emda`` text into Emdashy source text."""
    instrs, _ = parse_assembly(text, source)
    return emit_text(instrs, annotate=annotate)
