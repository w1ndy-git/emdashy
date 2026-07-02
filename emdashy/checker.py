"""Static analysis for Emdashy programs (the ``emdash check`` command).

Hard errors (unknown opcodes, missing operands, undefined labels) are
caught by the parser/assembler before we get here; this module adds
lint-style warnings on programs that already parse.
"""

from __future__ import annotations

from typing import List

from . import ops
from .parser import Program


def check(program: Program) -> List[str]:
    """Return a list of human-readable warnings for *program*."""
    warnings: List[str] = []

    if not program.instrs:
        warnings.append("the program contains no instructions")
        return warnings

    # Unreachable code: anything after jmp/ret/halt until the next label.
    # Only the first instruction of each dead block is flagged.
    state = "live"  # "live" | "dead" | "reported"
    for instr in program.instrs:
        if instr.name == "label":
            state = "live"
            continue
        if state == "dead":
            warnings.append(
                f"{program.source}:{instr.line}:{instr.col}: unreachable "
                f"instruction '{instr.render()}' (control never falls through here)"
            )
            state = "reported"
        elif state == "live" and instr.name in ops.TERMINATORS:
            state = "dead"

    # Labels that are never targeted.
    targeted = {i.arg for i in program.instrs if i.name in ops.BRANCHES}
    for instr in program.instrs:
        if instr.name == "label" and instr.arg not in targeted:
            warnings.append(
                f"{program.source}:{instr.line}:{instr.col}: label "
                f"L{instr.arg} is declared but never targeted"
            )

    # ret with no call anywhere is suspicious (though calls could come later).
    has_call = any(i.name == "call" for i in program.instrs)
    if not has_call and any(i.name == "ret" for i in program.instrs):
        warnings.append(
            f"{program.source}: 'ret' is used but the program never 'call's"
        )

    return warnings
