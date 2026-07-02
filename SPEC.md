# The Emdashy Language Specification

Version 1.0 — this document is normative; the reference interpreter in
`emdashy/interpreter.py` implements it exactly.

## 1. Source encoding

An Emdashy source file is Unicode text (UTF-8 on disk). Exactly one
character is meaningful: **the em dash, U+2014 (`—`)**.

* A **token** is a maximal run of consecutive em dashes. Its **value** is
  the number of em dashes in the run.
* **Every other character is a comment.** Any non-em-dash character ends
  the current run and is otherwise ignored. In particular the hyphen
  (`-`, U+002D), en dash (`–`, U+2013), minus sign (`−`, U+2212), and
  horizontal bar (`―`, U+2015) are *not* em dashes and have no meaning.
* An empty program (no em dashes at all) is valid and does nothing.

Because comments are unrestricted, tools may freely annotate programs with
mnemonics; the annotated file remains a conforming program.

## 2. Program structure

Tokens are decoded left to right:

1. A token of value *k* selects the instruction with opcode *k* from the
   table in §4. A value with no assigned opcode (currently *k* > 27) is a
   **parse error**.
2. If the instruction takes an operand, the *next* token supplies it:
   * a **value** operand (only `push`) encodes the integer
     `token value − 1`, so a run of one em dash encodes the literal `0`;
   * a **label** operand encodes the label id `token value` (labels are
     numbered from 1).
   A program that ends where an operand is required is a parse error.
3. `label` declares its id at the current position. Declaring the same
   label id twice is a parse error. A branch (`jmp`, `jz`, `jnz`, `call`)
   whose target id is never declared is a parse error.

## 3. Execution model

Emdashy is a stack machine with:

* **Integers** — signed, arbitrary precision.
* **The data stack** — the only place values live. Popping an empty stack
  is a runtime error.
* **The heap** — a sparse map from integer addresses (any integer,
  including negatives) to integers. Cells that were never stored read
  as `0`.
* **The call stack** — return addresses only; not addressable by the
  program.
* **The program counter** — starts at the first instruction. Execution
  stops at `halt` or by running past the last instruction (an implicit
  halt). Falling off the end is not an error, even inside a `call`.

Runtime errors (stack underflow, division by zero, invalid character
code, `ret` with an empty call stack, malformed integer input) terminate
the program with a diagnostic.

## 4. Instructions

Stack effects are written `( before -- after )`, top of stack rightmost.

| Opcode | Mnemonic | Operand | Effect |
| ---: | --- | --- | --- |
| 1 | `push` | value *n* | `( -- n )` |
| 2 | `pop` | | `( a -- )` |
| 3 | `dup` | | `( a -- a a )` |
| 4 | `swap` | | `( a b -- b a )` |
| 5 | `over` | | `( a b -- a b a )` |
| 6 | `add` | | `( a b -- a+b )` |
| 7 | `sub` | | `( a b -- a−b )` |
| 8 | `mul` | | `( a b -- a·b )` |
| 9 | `div` | | `( a b -- ⌊a/b⌋ )` — floor division; error if `b = 0` |
| 10 | `mod` | | `( a b -- a mod b )` — result has `b`'s sign; error if `b = 0`; `a = b·⌊a/b⌋ + (a mod b)` always holds |
| 11 | `neg` | | `( a -- −a )` |
| 12 | `eq` | | `( a b -- a=b )` — pushes `1` or `0` |
| 13 | `lt` | | `( a b -- a<b )` |
| 14 | `gt` | | `( a b -- a>b )` |
| 15 | `label` | label *L* | declares *L* here; no effect at run time |
| 16 | `jmp` | label *L* | jump to *L* |
| 17 | `jz` | label *L* | `( a -- )` jump to *L* if `a = 0` |
| 18 | `jnz` | label *L* | `( a -- )` jump to *L* if `a ≠ 0` |
| 19 | `call` | label *L* | push the return address on the call stack, jump to *L* |
| 20 | `ret` | | pop the call stack, jump there; error if empty |
| 21 | `load` | | `( addr -- heap[addr] )` |
| 22 | `store` | | `( addr value -- )` sets `heap[addr] = value` |
| 23 | `outn` | | `( a -- )` write `a` in decimal (no separator) to stdout |
| 24 | `outc` | | `( a -- )` write the character with code point `a`; error unless `0 ≤ a ≤ 0x10FFFF` and `a` is not a surrogate |
| 25 | `inn` | | `( -- a )` skip whitespace, read an optionally signed decimal integer from stdin; error at EOF or on non-numeric input |
| 26 | `inc` | | `( -- a )` read one character from stdin, push its code point; push `−1` at EOF |
| 27 | `halt` | | stop the program |

## 5. The assembly language (`.emda`)

The assembly syntax is a convenience defined by this toolchain, not part
of the dash encoding:

* Instructions are whitespace-separated; the format is not line-oriented.
* `;` and `#` start comments running to the end of the line.
* Labels are names: declare with `name:` or `label name`, target with
  `jmp name`, `jz name`, `jnz name`, `call name`. The assembler assigns
  numeric ids in order of first appearance.
* `push` accepts decimal (`42`, `-7`, `1_000`), hex (`0x2A`), binary
  (`0b101010`), and character literals (`'A'`, `'\n'`, `'\x41'`;
  escapes: `\n \t \r \0 \e \\ \' \" \xNN`).
* Negative literals assemble to `push |n|` followed by `neg` (the dash
  encoding has no negative literals).
* Literals larger than 255 assemble to a digit-by-digit
  `push/mul/add` sequence so files stay small: the dash encoding of a
  literal is unary.
* `prints "text"` is a macro emitting `push c` / `outc` per character.

## 6. Compiled targets

`emdash compile` produces code that matches the interpreter except where
noted:

* **C target** — integers are 64-bit two's complement (overflow wraps or
  traps per the C implementation rather than growing, unlike the
  interpreter's bignums); `inc` reads one *byte*, not one decoded
  character; `outc` emits UTF-8. Data stack depth is 2²⁰, call depth 2¹⁶.
* **Python target** — semantically identical to the interpreter.

Programs that stay within 64-bit arithmetic and ASCII input behave
identically everywhere.

## 7. File extensions

| Extension | Meaning |
| --- | --- |
| `.emd` | Emdashy source (em dashes) |
| `.emda` | Emdashy assembly |
