"""The Emdashy instruction set.

An instruction is selected by the length of a run of em dashes.  A run of
one em dash is ``push``, a run of two is ``pop``, and so on.  Instructions
that take an operand consume the *next* run as that operand:

* ``value`` operands encode the integer ``run length - 1`` (so a run of a
  single em dash encodes the literal ``0``).
* ``label`` operands encode the label id ``run length`` (labels are
  numbered starting at 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class OpInfo:
    name: str
    opcode: int
    arg_kind: Optional[str]  # None, "value" or "label"
    doc: str

    @property
    def has_arg(self) -> bool:
        return self.arg_kind is not None


_TABLE = [
    # name      opcode  arg      documentation
    ("push", 1, "value", "Push the integer encoded by the next run (length - 1)."),
    ("pop", 2, None, "Discard the top of the stack."),
    ("dup", 3, None, "Duplicate the top of the stack."),
    ("swap", 4, None, "Swap the top two stack values."),
    ("over", 5, None, "Push a copy of the second value from the top."),
    ("add", 6, None, "Pop b, pop a, push a + b."),
    ("sub", 7, None, "Pop b, pop a, push a - b."),
    ("mul", 8, None, "Pop b, pop a, push a * b."),
    ("div", 9, None, "Pop b, pop a, push floor(a / b). Error if b is 0."),
    ("mod", 10, None, "Pop b, pop a, push a mod b (result takes b's sign). Error if b is 0."),
    ("neg", 11, None, "Negate the top of the stack."),
    ("eq", 12, None, "Pop b, pop a, push 1 if a == b else 0."),
    ("lt", 13, None, "Pop b, pop a, push 1 if a < b else 0."),
    ("gt", 14, None, "Pop b, pop a, push 1 if a > b else 0."),
    ("label", 15, "label", "Declare the label named by the next run. No effect at run time."),
    ("jmp", 16, "label", "Jump to a label unconditionally."),
    ("jz", 17, "label", "Pop a; jump to a label if a == 0."),
    ("jnz", 18, "label", "Pop a; jump to a label if a != 0."),
    ("call", 19, "label", "Call a label as a subroutine (pushes a return address)."),
    ("ret", 20, None, "Return to the instruction after the most recent call."),
    ("load", 21, None, "Pop an address, push heap[address] (uninitialised cells read 0)."),
    ("store", 22, None, "Pop a value, pop an address, set heap[address] = value."),
    ("outn", 23, None, "Pop a value and write it to stdout as a decimal number."),
    ("outc", 24, None, "Pop a value and write it to stdout as a Unicode character."),
    ("inn", 25, None, "Read an integer from stdin and push it."),
    ("inc", 26, None, "Read one character from stdin and push its code point (-1 at EOF)."),
    ("halt", 27, None, "Stop the program immediately."),
]

BY_CODE: Dict[int, OpInfo] = {}
BY_NAME: Dict[str, OpInfo] = {}
for _name, _code, _arg, _doc in _TABLE:
    _info = OpInfo(_name, _code, _arg, _doc)
    BY_CODE[_code] = _info
    BY_NAME[_name] = _info

MAX_OPCODE = max(BY_CODE)

#: Instructions after which control never falls through to the next one.
TERMINATORS = frozenset({"jmp", "ret", "halt"})

#: Instructions whose label operand is a jump/call target.
BRANCHES = frozenset({"jmp", "jz", "jnz", "call"})
