"""The reference Emdashy virtual machine.

A small stack machine with arbitrary-precision integers, a sparse integer
heap, and a call stack.  The :class:`VM` exposes single-stepping so the
debugger and REPL can drive it interactively.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, TextIO

from .errors import EmdashyRuntimeError
from .parser import Instr, Program

DEFAULT_MAX_CALL_DEPTH = 100_000


class VM:
    def __init__(
        self,
        program: Program,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        max_steps: Optional[int] = None,
        max_call_depth: int = DEFAULT_MAX_CALL_DEPTH,
    ) -> None:
        self.instrs: List[Instr] = program.instrs
        self.labels: Dict[int, int] = dict(program.labels)
        self.source = program.source
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout
        self.max_steps = max_steps
        self.max_call_depth = max_call_depth

        self.pc = 0
        self.stack: List[int] = []
        self.calls: List[int] = []
        self.heap: Dict[int, int] = {}
        self.halted = False
        self.steps = 0
        self._pushback: List[str] = []

    # ------------------------------------------------------------------
    @property
    def finished(self) -> bool:
        return self.halted or not (0 <= self.pc < len(self.instrs))

    def _error(self, message: str, instr: Instr) -> EmdashyRuntimeError:
        return EmdashyRuntimeError(
            f"{message} (in '{instr.render()}')",
            self.source, instr.line, instr.col,
        )

    def _pop(self, instr: Instr) -> int:
        if not self.stack:
            raise self._error("stack underflow", instr)
        return self.stack.pop()

    def _peek(self, instr: Instr, depth: int) -> int:
        if len(self.stack) <= depth:
            raise self._error("stack underflow", instr)
        return self.stack[-1 - depth]

    # -- character-buffered input --------------------------------------
    def _read1(self) -> str:
        if self._pushback:
            return self._pushback.pop()
        return self.stdin.read(1)

    def _unread(self, ch: str) -> None:
        if ch:
            self._pushback.append(ch)

    def _read_int(self, instr: Instr) -> int:
        ch = self._read1()
        while ch and ch.isspace():
            ch = self._read1()
        if not ch:
            raise self._error("unexpected end of input while reading an integer", instr)
        sign = 1
        if ch in "+-":
            sign = -1 if ch == "-" else 1
            ch = self._read1()
        digits = ""
        while ch and ch.isdigit():
            digits += ch
            ch = self._read1()
        self._unread(ch)
        if not digits:
            raise self._error("invalid integer on input", instr)
        return sign * int(digits)

    # ------------------------------------------------------------------
    def step(self) -> None:
        """Execute exactly one instruction."""
        instr = self.instrs[self.pc]
        self.steps += 1
        if self.max_steps is not None and self.steps > self.max_steps:
            raise self._error(f"exceeded the step limit of {self.max_steps}", instr)
        self.pc += 1
        name = instr.name
        stack = self.stack

        if name == "push":
            stack.append(instr.arg)  # type: ignore[arg-type]
        elif name == "pop":
            self._pop(instr)
        elif name == "dup":
            stack.append(self._peek(instr, 0))
        elif name == "swap":
            b, a = self._pop(instr), self._pop(instr)
            stack.append(b)
            stack.append(a)
        elif name == "over":
            stack.append(self._peek(instr, 1))
        elif name == "add":
            b, a = self._pop(instr), self._pop(instr)
            stack.append(a + b)
        elif name == "sub":
            b, a = self._pop(instr), self._pop(instr)
            stack.append(a - b)
        elif name == "mul":
            b, a = self._pop(instr), self._pop(instr)
            stack.append(a * b)
        elif name == "div":
            b, a = self._pop(instr), self._pop(instr)
            if b == 0:
                raise self._error("division by zero", instr)
            stack.append(a // b)
        elif name == "mod":
            b, a = self._pop(instr), self._pop(instr)
            if b == 0:
                raise self._error("division by zero", instr)
            stack.append(a % b)
        elif name == "neg":
            stack.append(-self._pop(instr))
        elif name == "eq":
            b, a = self._pop(instr), self._pop(instr)
            stack.append(1 if a == b else 0)
        elif name == "lt":
            b, a = self._pop(instr), self._pop(instr)
            stack.append(1 if a < b else 0)
        elif name == "gt":
            b, a = self._pop(instr), self._pop(instr)
            stack.append(1 if a > b else 0)
        elif name == "label":
            pass
        elif name == "jmp":
            self.pc = self._target(instr)
        elif name == "jz":
            if self._pop(instr) == 0:
                self.pc = self._target(instr)
        elif name == "jnz":
            if self._pop(instr) != 0:
                self.pc = self._target(instr)
        elif name == "call":
            if len(self.calls) >= self.max_call_depth:
                raise self._error(
                    f"call stack overflow (depth {self.max_call_depth})", instr)
            self.calls.append(self.pc)
            self.pc = self._target(instr)
        elif name == "ret":
            if not self.calls:
                raise self._error("'ret' outside of a call", instr)
            self.pc = self.calls.pop()
        elif name == "load":
            addr = self._pop(instr)
            stack.append(self.heap.get(addr, 0))
        elif name == "store":
            value = self._pop(instr)
            addr = self._pop(instr)
            self.heap[addr] = value
        elif name == "outn":
            self.stdout.write(str(self._pop(instr)))
        elif name == "outc":
            value = self._pop(instr)
            if not (0 <= value <= 0x10FFFF) or 0xD800 <= value <= 0xDFFF:
                raise self._error(f"{value} is not a valid character code", instr)
            self.stdout.write(chr(value))
        elif name == "inn":
            stack.append(self._read_int(instr))
        elif name == "inc":
            ch = self._read1()
            stack.append(ord(ch) if ch else -1)
        elif name == "halt":
            self.halted = True
        else:  # pragma: no cover - the parser only produces known ops
            raise self._error(f"unimplemented instruction '{name}'", instr)

    def _target(self, instr: Instr) -> int:
        try:
            return self.labels[instr.arg]  # type: ignore[index]
        except KeyError:
            raise self._error(f"undefined label L{instr.arg}", instr) from None

    # ------------------------------------------------------------------
    def run(self, trace: bool = False, trace_out: Optional[TextIO] = None) -> None:
        trace_out = trace_out if trace_out is not None else sys.stderr
        while not self.finished:
            if trace:
                instr = self.instrs[self.pc]
                tail = self.stack[-8:]
                shown = ("... " if len(self.stack) > 8 else "") + repr(tail)
                trace_out.write(f"[{self.steps:>6}] pc={self.pc:<5} "
                                f"{instr.render():<18} stack={shown}\n")
            self.step()


def run_program(
    program: Program,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
    trace: bool = False,
    max_steps: Optional[int] = None,
) -> VM:
    vm = VM(program, stdin=stdin, stdout=stdout, max_steps=max_steps)
    vm.run(trace=trace)
    return vm
