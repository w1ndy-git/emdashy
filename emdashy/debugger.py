"""Interactive debugger for Emdashy programs (``emdash debug``).

A small gdb-flavoured stepping debugger over the reference VM:
breakpoints, single stepping, stack/heap inspection, and a disassembly
listing around the program counter.
"""

from __future__ import annotations

import sys
from typing import Optional, Set, TextIO

from .errors import EmdashyError
from .interpreter import VM
from .parser import Program

_HELP = """Commands:
  s [N]        step N instructions (default 1)
  c            continue until a breakpoint, halt, or the end
  b PC         set a breakpoint at instruction index PC
  b            list breakpoints
  d PC         delete the breakpoint at PC
  l            list the instructions around the program counter
  p            print the data stack
  H            print the heap
  i            print pc / step count / call depth
  r            restart the program from the beginning
  q            quit
  h            this help
"""


class Debugger:
    def __init__(self, program: Program, stdout: Optional[TextIO] = None) -> None:
        self.program = program
        self.out = stdout if stdout is not None else sys.stdout
        self.breakpoints: Set[int] = set()
        self.vm = VM(program)

    # ------------------------------------------------------------------
    def _show_position(self) -> None:
        if self.vm.finished:
            self.out.write("program finished.\n")
            return
        instr = self.vm.instrs[self.vm.pc]
        self.out.write(f"pc={self.vm.pc}: {instr.render(char_hint=True)}"
                       f"   [{self.program.source}:{instr.line}:{instr.col}]\n")

    def _list(self, context: int = 5) -> None:
        if not self.vm.instrs:
            self.out.write("(empty program)\n")
            return
        pc = min(self.vm.pc, len(self.vm.instrs) - 1)
        lo = max(0, pc - context)
        hi = min(len(self.vm.instrs), pc + context + 1)
        for idx in range(lo, hi):
            marker = "->" if idx == self.vm.pc else "  "
            bp = "*" if idx in self.breakpoints else " "
            self.out.write(f" {marker}{bp}{idx:>5}  "
                           f"{self.vm.instrs[idx].render(char_hint=True)}\n")

    def _step(self, count: int) -> None:
        for _ in range(count):
            if self.vm.finished:
                break
            self.vm.step()
        self._show_position()

    def _continue(self) -> None:
        while not self.vm.finished:
            self.vm.step()
            if self.vm.pc in self.breakpoints:
                self.out.write(f"breakpoint hit at pc={self.vm.pc}\n")
                break
        self._show_position()

    # ------------------------------------------------------------------
    def loop(self) -> None:
        self.out.write(f"emdash debugger — {len(self.vm.instrs)} instructions "
                       f"from {self.program.source}. Type h for help.\n")
        self._show_position()
        while True:
            try:
                line = input("(emdb) ").strip()
            except EOFError:
                self.out.write("\n")
                return
            except KeyboardInterrupt:
                self.out.write("\n")
                continue
            if not line:
                continue
            parts = line.split()
            cmd, args = parts[0], parts[1:]
            try:
                if cmd == "q":
                    return
                elif cmd == "h":
                    self.out.write(_HELP)
                elif cmd == "s":
                    self._step(int(args[0]) if args else 1)
                elif cmd == "c":
                    self._continue()
                elif cmd == "b" and args:
                    self.breakpoints.add(int(args[0]))
                    self.out.write(f"breakpoint set at pc={args[0]}\n")
                elif cmd == "b":
                    self.out.write(f"breakpoints: {sorted(self.breakpoints)}\n")
                elif cmd == "d" and args:
                    self.breakpoints.discard(int(args[0]))
                    self.out.write(f"breakpoint removed from pc={args[0]}\n")
                elif cmd == "l":
                    self._list()
                elif cmd == "p":
                    self.out.write(f"stack: {self.vm.stack!r}\n")
                elif cmd == "H":
                    if self.vm.heap:
                        for addr in sorted(self.vm.heap):
                            self.out.write(f"  heap[{addr}] = {self.vm.heap[addr]}\n")
                    else:
                        self.out.write("  (heap is empty)\n")
                elif cmd == "i":
                    self.out.write(f"pc={self.vm.pc} steps={self.vm.steps} "
                                   f"call-depth={len(self.vm.calls)} "
                                   f"stack-depth={len(self.vm.stack)}\n")
                elif cmd == "r":
                    self.vm = VM(self.program)
                    self.out.write("restarted.\n")
                    self._show_position()
                else:
                    self.out.write(f"unknown command '{line}' (h for help)\n")
            except ValueError:
                self.out.write("expected a numeric argument (h for help)\n")
            except EmdashyError as exc:
                self.out.write(f"runtime error: {exc}\n")


def debug_program(program: Program) -> int:
    Debugger(program).loop()
    return 0
