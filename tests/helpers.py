"""Shared helpers for the Emdashy test suite."""

import io
import os

from emdashy.assembler import assemble_program, assemble_text
from emdashy.interpreter import VM
from emdashy.parser import parse_source

EXAMPLES = os.path.join(os.path.dirname(__file__), os.pardir, "examples")


def run_vm(program, stdin="", max_steps=1_000_000):
    out = io.StringIO()
    vm = VM(program, stdin=io.StringIO(stdin), stdout=out, max_steps=max_steps)
    vm.run()
    return out.getvalue(), vm


def run_asm(asm, stdin="", max_steps=1_000_000):
    """Assemble .emda text and interpret it; return (stdout, vm)."""
    return run_vm(assemble_program(asm, "<test>"), stdin, max_steps)


def run_emd(text, stdin="", max_steps=1_000_000):
    """Parse raw em dash text and interpret it; return (stdout, vm)."""
    return run_vm(parse_source(text, "<test>"), stdin, max_steps)


def asm_to_emd(asm, annotate=True):
    return assemble_text(asm, "<test>", annotate=annotate)


def example(name):
    path = os.path.join(EXAMPLES, name)
    with open(path, encoding="utf-8") as fh:
        return fh.read()
