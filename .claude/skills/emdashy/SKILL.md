---
name: emdashy
description: >-
  Write, run, test, debug, and compile programs in Emdashy, the esoteric
  programming language comprised only of em dashes. Use whenever the user asks
  for an Emdashy program, mentions .emd or .emda files, the emdash CLI, em dash
  code, or wants to port an algorithm to Emdashy. Covers the instruction set,
  assembly syntax, stack idioms, and the full toolchain workflow.
---

# Programming in Emdashy

Emdashy is a stack machine whose source contains one meaningful character:
the em dash `—` (U+2014). Runs of consecutive em dashes encode instructions;
**every other character is a comment**. The normative spec is `SPEC.md` in
this repository; reference programs live in `examples/`.

## Golden rules

1. **Never write em dashes by hand.** Write assembly in a `.emda` file and
   let the toolchain produce the `.emd`. Hand-counted dashes are the #1
   source of bugs — a run of 24 (`outc`) vs 23 (`outn`) is invisible to eyes.
2. **`emdash run` accepts `.emda` directly** — develop and test against the
   assembly, generate the `.emd` artifact last.
3. **Always test with real I/O** before declaring success:
   `echo "5" | emdash run prog.emda`
4. While a loop is under development, guard against hangs:
   `emdash run prog.emda --max-steps 100000`
5. Run `emdash check prog.emda` to catch unreachable code and unused labels.

## Toolchain commands

```bash
emdash run prog.emda            # interpret (also: prog.emd); --trace, --max-steps N
emdash asm prog.emda            # -> prog.emd (annotated; --bare for dashes only)
emdash disasm prog.emd          # dashes -> assembly
emdash check prog.emda          # lint
emdash compile prog.emd --build          # -> C -> native binary
emdash compile prog.emd --target py      # -> standalone Python script
emdash repl                     # interactive; definitions persist across lines
emdash debug prog.emda          # breakpoints, stepping, stack/heap inspection
emdash fmt prog.emd -i          # canonical formatting + mnemonic annotations
```

If `emdash` is not installed, `python -m emdashy ...` works from a checkout.

## Machine model

- **Data stack** of arbitrary-precision signed integers — the only value store
  besides the heap. Underflow is a runtime error.
- **Heap**: sparse map from any integer address to an integer; unwritten
  cells read 0. Use it for loop counters and variables.
- **Call stack**: used only by `call`/`ret`.
- Execution stops at `halt` or by falling off the end (implicit halt).

## Instruction set (stack effects: top of stack is rightmost)

| Mnemonic | Effect | Mnemonic | Effect |
| --- | --- | --- | --- |
| `push n` | `( -- n )` | `label L` | declare label, no-op |
| `pop` | `( a -- )` | `jmp L` | goto L |
| `dup` | `( a -- a a )` | `jz L` | `( a -- )` goto L if a == 0 |
| `swap` | `( a b -- b a )` | `jnz L` | `( a -- )` goto L if a != 0 |
| `over` | `( a b -- a b a )` | `call L` | subroutine call |
| `add` | `( a b -- a+b )` | `ret` | return; error if no call |
| `sub` | `( a b -- a-b )` | `load` | `( addr -- heap[addr] )` |
| `mul` | `( a b -- a*b )` | `store` | `( addr value -- )` heap[addr]=value |
| `div` | `( a b -- floor(a/b) )` | `outn` | `( a -- )` print decimal, no newline |
| `mod` | `( a b -- a mod b )` sign of b | `outc` | `( a -- )` print Unicode char |
| `neg` | `( a -- -a )` | `inn` | `( -- n )` read integer, error at EOF |
| `eq` `lt` `gt` | `( a b -- 0/1 )` | `inc` | `( -- c )` read char code, -1 at EOF |
|  |  | `halt` | stop |

## Assembly syntax (.emda)

- Whitespace-separated, **not line-oriented**: `push 3 push 4 add outn` is valid.
- Comments: `;` or `#` to end of line.
- Labels are names: declare `name:` (or `label name`), target `jmp name`,
  `jz`/`jnz`/`call name`.
- `push` literals: `42`, `-7`, `0x2A`, `0b1010`, `'A'`, `'\n'`
  (escapes `\n \t \r \0 \e \\ \' \" \xNN`). Negatives and values > 255 are
  expanded automatically by the assembler — just write the number.
- `prints "text\n"` — macro that prints a string.

## Idioms cookbook

**Count-down loop (counter on stack):**
```
    push 10
loop:
    dup jz done         ; exit when counter hits 0
    dup outn push '\n' outc
    push 1 sub
    jmp loop
done:
    pop halt
```

**Variable in heap cell 0** (read `push 0 load`; write `push 0 <value> store`;
increment):
```
    push 0  push 0 load  push 1 add  store    ; heap[0] += 1
```
Mind the order: `store` takes *address first, then value* — address is pushed
before the value.

**If/else** — comparisons leave 0/1, and `jz`/`jnz` consume it:
```
    ... push 100 gt jnz too_big
    ; else-branch here
    jmp endif
too_big:
    ; then-branch here
endif:
```

**Subroutine convention** — arguments on the stack, results on the stack:
```
    push 9 call square outn halt
square:                 ; ( n -- n*n )
    dup mul ret
```

**Pair update** (e.g. Fibonacci `(a, b) -> (b, a+b)`): `swap over add`.

**EOF-driven read loop** (cat): `inc` then `dup push -1 eq jnz done`.

## Pitfalls

- `sub`/`div`/`mod`/`lt`/`gt` operate as `a OP b` where `b` is on top —
  `push 10 push 3 sub` is 7, not -7.
- `jz`/`jnz` **pop** the tested value; `dup` first if you still need it.
- `outn` prints no separator — emit `push '\n' outc` yourself.
- Track the stack depth in comments (`; ( n acc )`) for anything nontrivial;
  most bugs are stack-shape bugs. `emdash run --trace` shows the stack at
  every step; `emdash debug` single-steps.
- The C target uses 64-bit integers and byte input; the interpreter and
  Python target have bignums. Stay in 64-bit range for portable programs.
- Only U+2014 is code. Hyphens `-`, en dashes `–`, minus signs `−`, and
  horizontal bars `―` are comments — a "dash" pasted from elsewhere may be
  silently ignored.

## Workflow for a new program

1. Sketch the algorithm and the stack shape at each point.
2. Write `prog.emda`, keeping `; ( stack )` comments on tricky lines.
3. `emdash check prog.emda`, then run with test input and `--max-steps`.
4. Debug with `--trace` (small programs) or `emdash debug` (breakpoints).
5. Ship: `emdash asm prog.emda` for the pure em dash artifact, and commit
   **both** files. Optionally `emdash compile prog.emd --build` for a binary.
