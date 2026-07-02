"""The ``emdash`` command line front end.

Subcommands:

* ``run``      interpret a program (``.emd`` or ``.emda``)
* ``asm``      assemble ``.emda`` assembly into em dashes
* ``disasm``   disassemble em dashes back into assembly
* ``fmt``      reformat/annotate a ``.emd`` file canonically
* ``check``    parse and lint a program
* ``compile``  compile to C or Python (optionally build a binary)
* ``repl``     interactive session
* ``debug``    interactive stepping debugger
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from typing import List, Optional

from . import __version__
from .assembler import assemble_program, assemble_text, emit_text
from .checker import check
from .compiler_c import compile_to_c
from .compiler_py import compile_to_python
from .debugger import debug_program
from .disassembler import disassemble
from .errors import EmdashyError
from .interpreter import run_program
from .parser import Program, parse_source
from .repl import Repl


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _write(path: Optional[str], text: str) -> None:
    if path is None or path == "-":
        sys.stdout.write(text)
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)


def load_program(path: str) -> Program:
    """Load a program from disk; ``.emda`` files are assembled on the fly."""
    text = _read(path)
    if path.endswith(".emda"):
        return assemble_program(text, source=path)
    return parse_source(text, source=path)


# ----------------------------------------------------------------------
def _cmd_run(args: argparse.Namespace) -> int:
    program = load_program(args.file)
    run_program(program, trace=args.trace, max_steps=args.max_steps)
    return 0


def _cmd_asm(args: argparse.Namespace) -> int:
    out = args.output or os.path.splitext(args.file)[0] + ".emd"
    text = assemble_text(_read(args.file), source=args.file,
                         annotate=not args.bare)
    _write(out, text)
    if out not in (None, "-"):
        sys.stderr.write(f"emdash: wrote {out}\n")
    return 0


def _cmd_disasm(args: argparse.Namespace) -> int:
    _write(args.output, disassemble(load_program(args.file)))
    return 0


def _cmd_fmt(args: argparse.Namespace) -> int:
    program = load_program(args.file)
    text = emit_text(program.instrs, annotate=not args.bare)
    if args.in_place:
        _write(args.file, text)
        sys.stderr.write(f"emdash: reformatted {args.file}\n")
    else:
        _write(args.output, text)
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    program = load_program(args.file)  # parse errors abort before this returns
    warnings = check(program)
    for warning in warnings:
        sys.stderr.write(f"warning: {warning}\n")
    sys.stderr.write(
        f"emdash: {args.file}: OK — {len(program.instrs)} instructions, "
        f"{len(program.labels)} labels, {len(warnings)} warning(s)\n"
    )
    return 0


def _cmd_compile(args: argparse.Namespace) -> int:
    program = load_program(args.file)
    stem = os.path.splitext(args.file)[0]

    target = args.target
    if target is None and args.output:
        if args.output.endswith(".py"):
            target = "py"
        elif args.output.endswith(".c"):
            target = "c"
    if target is None:
        target = "c"

    if target == "py":
        out = args.output or stem + ".py"
        _write(out, compile_to_python(program))
        sys.stderr.write(f"emdash: wrote {out}\n")
        return 0

    out = args.output or stem + ".c"
    _write(out, compile_to_c(program))
    sys.stderr.write(f"emdash: wrote {out}\n")
    if args.build:
        if out in (None, "-"):
            sys.stderr.write("emdash: error: --build needs a real output file\n")
            return 1
        cc = args.cc or os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc")
        if not cc:
            sys.stderr.write("emdash: error: no C compiler found (set --cc or $CC)\n")
            return 1
        exe = os.path.splitext(out)[0]
        cmd = [cc, out, "-O2", "-o", exe]
        sys.stderr.write("emdash: " + " ".join(cmd) + "\n")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            return result.returncode
        sys.stderr.write(f"emdash: built {exe}\n")
    return 0


def _cmd_repl(_args: argparse.Namespace) -> int:
    Repl().loop()
    return 0


def _cmd_debug(args: argparse.Namespace) -> int:
    return debug_program(load_program(args.file))


# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emdash",
        description="Toolchain for Emdashy, the programming language "
                    "comprised only of em dashes.",
    )
    parser.add_argument("--version", action="version",
                        version=f"emdash {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="interpret a .emd or .emda program")
    p.add_argument("file")
    p.add_argument("--trace", action="store_true",
                   help="print each instruction and the stack to stderr")
    p.add_argument("--max-steps", type=int, default=None, metavar="N",
                   help="abort after N instructions (guards infinite loops)")
    p.set_defaults(func=_cmd_run)

    p = sub.add_parser("asm", help="assemble .emda assembly into em dashes")
    p.add_argument("file")
    p.add_argument("-o", "--output", help="output path (default: FILE.emd, '-' for stdout)")
    p.add_argument("--bare", action="store_true",
                   help="omit the mnemonic comments from the output")
    p.set_defaults(func=_cmd_asm)

    p = sub.add_parser("disasm", help="disassemble em dashes into assembly")
    p.add_argument("file")
    p.add_argument("-o", "--output", help="output path (default: stdout)")
    p.set_defaults(func=_cmd_disasm)

    p = sub.add_parser("fmt", help="reformat a program canonically")
    p.add_argument("file")
    p.add_argument("-o", "--output", help="output path (default: stdout)")
    p.add_argument("-i", "--in-place", action="store_true",
                   help="rewrite the file in place")
    p.add_argument("--bare", action="store_true",
                   help="omit the mnemonic comments from the output")
    p.set_defaults(func=_cmd_fmt)

    p = sub.add_parser("check", help="parse and lint a program")
    p.add_argument("file")
    p.set_defaults(func=_cmd_check)

    p = sub.add_parser("compile", help="compile to C (default) or Python")
    p.add_argument("file")
    p.add_argument("-o", "--output", help="output path (default: FILE.c / FILE.py)")
    p.add_argument("--target", choices=("c", "py"),
                   help="code generation target (default: inferred from -o, else c)")
    p.add_argument("--build", action="store_true",
                   help="also compile the generated C into an executable")
    p.add_argument("--cc", help="C compiler to use with --build (default: $CC, cc, gcc)")
    p.set_defaults(func=_cmd_compile)

    p = sub.add_parser("repl", help="interactive read-eval-print loop")
    p.set_defaults(func=_cmd_repl)

    p = sub.add_parser("debug", help="interactive stepping debugger")
    p.add_argument("file")
    p.set_defaults(func=_cmd_debug)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except EmdashyError as exc:
        sys.stderr.write(f"emdash: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"emdash: error: {exc.filename}: no such file\n")
        return 1
    except KeyboardInterrupt:
        sys.stderr.write("\nemdash: interrupted\n")
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
