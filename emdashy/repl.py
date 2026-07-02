"""Interactive REPL for Emdashy.

Accepts assembly mnemonics (``push 3 push 4 add outn``) *or* raw em
dashes on each line, executes them on a persistent VM, and shows the
stack.  Labels defined on earlier lines stay visible, so subroutines can
be built up incrementally.
"""

from __future__ import annotations

import sys
from typing import Optional, TextIO

from . import EM_DASH, __version__
from .assembler import LabelSpace, parse_assembly
from .errors import EmdashyError
from .interpreter import VM
from .lexer import lex
from .parser import Program, parse_tokens

_BANNER = f"""Emdashy {__version__} — the em dash programming language.
Type assembly (e.g. `push 2 push 3 add outn`) or raw em dashes.
Meta commands: .stack .heap .reset .load FILE .help .quit
"""

_HELP = """Meta commands:
  .stack        show the full data stack
  .heap         show every heap cell that has been written
  .reset        clear the stack, heap, program and labels
  .load FILE    assemble/run a .emd or .emda file inside this session
  .help         show this message
  .quit         leave the REPL (Ctrl-D works too)
Anything else is assembled and executed immediately; labels persist
between lines, so you can `label f ... ret` one line and `call f` later.
"""


class Repl:
    def __init__(self, stdout: Optional[TextIO] = None) -> None:
        self.stdout = stdout if stdout is not None else sys.stdout
        self._reset()

    def _reset(self) -> None:
        self.labels = LabelSpace()
        self.vm = VM(Program(source="<repl>"))

    # ------------------------------------------------------------------
    def execute(self, text: str, source: str = "<repl>",
                force_run: bool = False) -> bool:
        """Assemble *text* (asm or raw dashes), append it, and maybe run it.

        A snippet that *starts* with a label declaration is treated as a
        definition: it is appended (so it can be ``call``ed later) but not
        executed, unless *force_run* is set (used by ``.load``).  Returns
        True if the snippet was executed.
        """
        if EM_DASH in text:
            chunk = parse_tokens(lex(text), source)
            instrs = chunk.instrs
        else:
            instrs, _ = parse_assembly(text, source, self.labels)
        if not instrs:
            return True  # nothing to append; showing the stack is harmless
        base = len(self.vm.instrs)
        self.vm.instrs.extend(instrs)
        for offset, instr in enumerate(instrs):
            if instr.name == "label":
                self.vm.labels[instr.arg] = base + offset  # type: ignore[index]
        if instrs[0].name == "label" and not force_run:
            return False
        self.vm.pc = base
        self.vm.halted = False
        self.vm.run()
        return True

    def _show_stack(self) -> None:
        self.stdout.write(f"stack: {self.vm.stack!r}\n")

    def _meta(self, line: str) -> bool:
        """Handle a meta command; return False to exit the REPL."""
        parts = line.split(None, 1)
        cmd = parts[0]
        if cmd in (".quit", ".exit", ".q"):
            return False
        if cmd == ".help":
            self.stdout.write(_HELP)
        elif cmd == ".stack":
            self._show_stack()
        elif cmd == ".heap":
            if self.vm.heap:
                for addr in sorted(self.vm.heap):
                    self.stdout.write(f"  heap[{addr}] = {self.vm.heap[addr]}\n")
            else:
                self.stdout.write("  (heap is empty)\n")
        elif cmd == ".reset":
            self._reset()
            self.stdout.write("reset.\n")
        elif cmd == ".load":
            if len(parts) < 2:
                self.stdout.write("usage: .load FILE\n")
            else:
                path = parts[1].strip()
                with open(path, encoding="utf-8") as fh:
                    self.execute(fh.read(), source=path, force_run=True)
                self._show_stack()
        else:
            self.stdout.write(f"unknown meta command {cmd} (try .help)\n")
        return True

    # ------------------------------------------------------------------
    def loop(self) -> None:
        self.stdout.write(_BANNER)
        while True:
            try:
                line = input("emdash> ")
            except EOFError:
                self.stdout.write("\n")
                return
            except KeyboardInterrupt:
                self.stdout.write("\n(interrupted — .quit to leave)\n")
                continue
            line = line.strip()
            if not line:
                continue
            try:
                if line.startswith("."):
                    if not self._meta(line):
                        return
                else:
                    if self.execute(line):
                        self._show_stack()
                    else:
                        self.stdout.write("defined (not executed).\n")
            except EmdashyError as exc:
                self.stdout.write(f"error: {exc}\n")
            except OSError as exc:
                self.stdout.write(f"error: {exc}\n")


def main() -> int:
    Repl().loop()
    return 0
