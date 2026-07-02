"""Disassembler: em dashes -> human-readable Emdashy assembly."""

from __future__ import annotations

from typing import List

from . import ops
from .parser import Program


def disassemble(program: Program) -> str:
    """Render a program as ``.emda`` assembly that reassembles identically.

    Labels come back as ``L<id>:`` so names survive a round trip through
    the numeric encoding (original names are not stored in the dashes).
    """
    lines: List[str] = []
    for instr in program.instrs:
        info = ops.BY_NAME[instr.name]
        if instr.name == "label":
            lines.append(f"L{instr.arg}:")
        elif info.arg_kind == "label":
            lines.append(f"    {instr.name} L{instr.arg}")
        elif info.arg_kind == "value":
            line = f"    {instr.name} {instr.arg}"
            if instr.arg is not None and 32 <= instr.arg < 127:
                ch = chr(instr.arg).replace("\\", "\\\\").replace("'", "\\'")
                line += f"    ; '{ch}'"
            lines.append(line)
        else:
            lines.append(f"    {instr.name}")
    return "\n".join(lines) + ("\n" if lines else "")
