"""Emdashy — an esoteric programming language comprised only of em dashes.

A program is a sequence of *runs* of consecutive em dash characters
(U+2014).  The length of each run selects an instruction (or encodes an
operand).  Every character that is not an em dash is a comment and is
ignored, so annotated Emdashy source is still pure Emdashy.

This package ships the full developer toolchain:

* :mod:`emdashy.interpreter`   — the reference virtual machine
* :mod:`emdashy.assembler`     — human-readable assembly -> em dashes
* :mod:`emdashy.disassembler`  — em dashes -> human-readable assembly
* :mod:`emdashy.compiler_c`    — ahead-of-time compiler targeting C
* :mod:`emdashy.compiler_py`   — ahead-of-time compiler targeting Python
* :mod:`emdashy.checker`       — static analysis / linting
* :mod:`emdashy.repl`          — interactive read-eval-print loop
* :mod:`emdashy.debugger`      — interactive source-level debugger
* :mod:`emdashy.cli`           — the ``emdash`` command line front end
"""

__version__ = "1.0.0"

EM_DASH = "—"
