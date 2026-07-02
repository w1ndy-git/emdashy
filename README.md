# Emdashy —

**The esoteric programming language comprised only of em dashes.**

An Emdashy program contains exactly one meaningful character: the em dash
(`—`, U+2014). Instructions are *runs* of consecutive em dashes — a run of
one em dash means `push`, a run of two means `pop`, a run of twenty-seven
means `halt`. Every character that is not an em dash is a comment, which
means hyphens, en dashes, minus signs, prose, and your feelings about
punctuation are all ignored by the language.

This is the complete program that prints `Hi`:

```
— —————————————————————————————————————————————————————————————————————————  ; push 72  'H'
————————————————————————  ; outc
— ——————————————————————————————————————————————————————————————————————————————————————————————————————————  ; push 105  'i'
————————————————————————  ; outc
———————————————————————————  ; halt

```

(Those `; push 72 'H'` annotations are not special syntax — they are simply
not em dashes, so the language ignores them. Annotated Emdashy is still
pure Emdashy.)

## The toolchain

Emdashy ships with everything a working developer needs, in one
dependency-free Python package:

| Tool | Command | What it does |
| --- | --- | --- |
| Interpreter | `emdash run prog.emd` | Reference VM with bignums, tracing, and step limits |
| Compiler → C | `emdash compile prog.emd --build` | Generates portable C99 (labels become real `goto`s) and builds a native binary |
| Compiler → Python | `emdash compile prog.emd --target py` | Generates a standalone, dependency-free script |
| Assembler | `emdash asm prog.emda` | Human-readable assembly → em dashes, with named labels, char/string literals, and macros |
| Disassembler | `emdash disasm prog.emd` | Em dashes → assembly |
| Formatter | `emdash fmt prog.emd -i` | Canonical formatting; adds (or strips, with `--bare`) mnemonic annotations |
| Linter | `emdash check prog.emd` | Parse errors with `file:line:col`, unreachable-code and unused-label warnings |
| REPL | `emdash repl` | Interactive session; accepts assembly *or* raw dashes; definitions persist between lines |
| Debugger | `emdash debug prog.emd` | Breakpoints, single stepping, stack/heap inspection, disassembly listing |

## Installation

```console
$ pip install .        # from a checkout; installs the `emdash` command
$ emdash --version
emdash 1.0.0
```

Or run it straight from the checkout with `python -m emdashy ...` — the
toolchain is pure standard-library Python (3.9+).

## Quick start

Nobody counts em dashes by hand: you write assembly (`.emda`) and let the
assembler produce the dashes (`.emd`).

```console
$ cat examples/adder.emda
    inn
    inn
    add
    outn
    push '\n'
    outc
    halt

$ emdash asm examples/adder.emda      # -> examples/adder.emd (pure em dashes)
$ echo "17 25" | emdash run examples/adder.emd
42
```

`emdash run` also accepts `.emda` files directly, assembling them on the
fly, so the edit-run loop never touches dashes unless you want it to.

Compile to a native binary:

```console
$ emdash compile examples/adder.emd --build
$ echo "17 25" | ./examples/adder
42
```

Poke at the language interactively:

```console
$ emdash repl
emdash> push 6 push 7 mul outn
42stack: []
emdash> label square dup mul ret
defined (not executed).
emdash> push 9 call square
stack: [81]
```

## The language in 60 seconds

Emdashy is a stack machine with 27 instructions. The run length picks the
instruction; `push` and the label instructions consume the *next* run as
their operand.

| Run | Op | Run | Op | Run | Op |
| --- | --- | --- | --- | --- | --- |
| 1 | `push n` | 10 | `mod` | 19 | `call L` |
| 2 | `pop` | 11 | `neg` | 20 | `ret` |
| 3 | `dup` | 12 | `eq` | 21 | `load` |
| 4 | `swap` | 13 | `lt` | 22 | `store` |
| 5 | `over` | 14 | `gt` | 23 | `outn` |
| 6 | `add` | 15 | `label L` | 24 | `outc` |
| 7 | `sub` | 16 | `jmp L` | 25 | `inn` |
| 8 | `mul` | 17 | `jz L` | 26 | `inc` |
| 9 | `div` | 18 | `jnz L` | 27 | `halt` |

Integers are arbitrary precision, there is a sparse heap addressed by
integers (`load`/`store`), a call stack (`call`/`ret`), and character and
numeric I/O. The full, normative description — encoding, operand rules,
semantics of every instruction, and how the C target differs (64-bit
integers, byte input) — lives in **[SPEC.md](SPEC.md)**.

## Examples

The [`examples/`](examples/) directory contains each program in both
forms — readable `.emda` and the assembled `.emd`:

* `hello` — Hello, World!
* `adder` — read two integers, print the sum
* `cat` — copy stdin to stdout
* `factorial` — subroutines via `call`/`ret`
* `fibonacci` — loops, the heap, and stack shuffling
* `fizzbuzz` — the interview classic, in punctuation
* `truth_machine` — the esolang classic

## Development

```console
$ python -m unittest discover -s tests    # run the test suite (55 tests)
```

The package layout mirrors a conventional compiler pipeline: `lexer.py` →
`parser.py` → (`interpreter.py` | `compiler_c.py` | `compiler_py.py`), with
`assembler.py`/`disassembler.py` bridging the human-readable syntax and
`cli.py` tying it all together.

## FAQ

**Why?** — Because somebody had to take a stand for the em dash.

**Is annotated output cheating?** — No. The language specification defines
every non-em-dash character as a comment. A file that is 99% English and
1% em dashes is a valid, running Emdashy program — the dashes are the only
part that executes.

**How do I type an em dash?** — You don't; you write `.emda` assembly and
run `emdash asm`. (But if you insist: Compose `---` on Linux, Option+Shift+Hyphen
on macOS, Alt+0151 on Windows.)
