"""Tests for the assembler, disassembler, checker, compilers, and REPL."""

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from emdashy import EM_DASH
from emdashy.assembler import assemble_program, assemble_text, emit_text
from emdashy.checker import check
from emdashy.compiler_c import compile_to_c
from emdashy.compiler_py import compile_to_python
from emdashy.disassembler import disassemble
from emdashy.errors import AsmError
from emdashy.parser import parse_source
from emdashy.repl import Repl

from helpers import run_asm, run_emd


class AssemblerTests(unittest.TestCase):
    def test_output_is_pure_em_dashes_plus_comments(self):
        emd = assemble_text("push 65 outc halt", annotate=False)
        for line in emd.splitlines():
            self.assertTrue(set(line) <= {EM_DASH, " "}, repr(line))

    def test_annotations_are_still_valid_source(self):
        emd = assemble_text("push 2 push 3 add outn", annotate=True)
        out, _ = run_emd(emd)
        self.assertEqual(out, "5")

    def test_char_and_numeric_literals(self):
        out, _ = run_asm("push 'A' outc push 0x42 outc push 0b1000011 outc")
        self.assertEqual(out, "ABC")

    def test_escape_sequences(self):
        out, _ = run_asm(r"push '\n' outc push '\\' outc push '\x41' outc")
        self.assertEqual(out, "\n\\A")

    def test_negative_literals(self):
        out, _ = run_asm("push -12 outn")
        self.assertEqual(out, "-12")

    def test_big_literal_expansion(self):
        # 1234567 in unary would be over a megabyte of dashes; the
        # assembler builds it digit by digit instead.
        emd = assemble_text("push 1234567 outn", annotate=False)
        self.assertLess(len(emd), 2000)
        out, _ = run_emd(emd)
        self.assertEqual(out, "1234567")

    def test_prints_macro(self):
        out, _ = run_asm('prints "hi\\n"')
        self.assertEqual(out, "hi\n")

    def test_label_forms(self):
        out, _ = run_asm("jmp end push 1 outn end: halt")
        self.assertEqual(out, "")
        out, _ = run_asm("jmp end push 1 outn label end halt")
        self.assertEqual(out, "")

    def test_errors(self):
        with self.assertRaises(AsmError):
            assemble_program("frobnicate")
        with self.assertRaises(AsmError):
            assemble_program("push")
        with self.assertRaises(AsmError):
            assemble_program("jmp nowhere")
        with self.assertRaises(AsmError):
            assemble_program("dup: swap dup: pop")
        with self.assertRaises(AsmError):
            assemble_program('prints "unterminated')
        with self.assertRaises(AsmError):
            assemble_program("push 'ab'")

    def test_error_location(self):
        with self.assertRaises(AsmError) as ctx:
            assemble_program("push 1\npush 2\nbogus", source="prog.emda")
        self.assertIn("prog.emda:3", str(ctx.exception))


class RoundTripTests(unittest.TestCase):
    ASM = """
        push 10
    loop:
        dup jz done
        dup outn
        push 1 sub
        jmp loop
    done:
        prints "done\\n"
        halt
    """

    def test_asm_emd_disasm_round_trip(self):
        emd = assemble_text(self.ASM, annotate=True)
        program = parse_source(emd)
        asm2 = disassemble(program)
        program2 = assemble_program(asm2)
        self.assertEqual(
            [(i.name, i.arg) for i in program.instrs],
            [(i.name, i.arg) for i in program2.instrs],
        )

    def test_fmt_is_idempotent(self):
        program = parse_source(assemble_text(self.ASM))
        once = emit_text(program.instrs)
        twice = emit_text(parse_source(once).instrs)
        self.assertEqual(once, twice)


class CheckerTests(unittest.TestCase):
    def test_clean_program(self):
        self.assertEqual(check(assemble_program("push 1 outn halt")), [])

    def test_unreachable_code(self):
        warnings = check(assemble_program("halt push 1 outn"))
        self.assertTrue(any("unreachable" in w for w in warnings))

    def test_unused_label(self):
        warnings = check(assemble_program("unused: push 1 pop"))
        self.assertTrue(any("never targeted" in w for w in warnings))

    def test_ret_without_call(self):
        warnings = check(assemble_program("f: push 1 ret"))
        self.assertTrue(any("never 'call's" in w for w in warnings))

    def test_empty_program(self):
        warnings = check(assemble_program("; only a comment"))
        self.assertTrue(any("no instructions" in w for w in warnings))


class CompilerTests(unittest.TestCase):
    ASM = """
        inn call fact outn push '\\n' outc halt
    fact:
        push 1
    floop:
        over jz fdone
        over mul
        swap push 1 sub swap
        jmp floop
    fdone:
        swap pop ret
    """

    def _program(self):
        return assemble_program(self.ASM, "<test>")

    def test_python_target(self):
        code = compile_to_python(self._program())
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fact.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(code)
            result = subprocess.run([sys.executable, path], input="6\n",
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "720\n")

    @unittest.skipUnless(shutil.which("cc") or shutil.which("gcc"),
                         "no C compiler available")
    def test_c_target(self):
        cc = shutil.which("cc") or shutil.which("gcc")
        code = compile_to_c(self._program())
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "fact.c")
            exe = os.path.join(tmp, "fact")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(code)
            build = subprocess.run([cc, src, "-O2", "-o", exe],
                                   capture_output=True, text=True, timeout=120)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([exe], input="6\n",
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "720\n")

    @unittest.skipUnless(shutil.which("cc") or shutil.which("gcc"),
                         "no C compiler available")
    def test_c_target_heap_and_unicode(self):
        cc = shutil.which("cc") or shutil.which("gcc")
        program = assemble_program(
            "push 1000000 push 7 store push 1000000 load outn push 8212 outc halt")
        code = compile_to_c(program)
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "t.c")
            exe = os.path.join(tmp, "t")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(code)
            build = subprocess.run([cc, src, "-o", exe],
                                   capture_output=True, text=True, timeout=120)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([exe], capture_output=True, timeout=60)
        self.assertEqual(result.stdout.decode("utf-8"), "7—")


class ReplTests(unittest.TestCase):
    def test_immediate_execution(self):
        repl = Repl(stdout=io.StringIO())
        repl.vm.stdout = io.StringIO()
        self.assertTrue(repl.execute("push 2 push 3 add"))
        self.assertEqual(repl.vm.stack, [5])

    def test_definitions_persist_across_lines(self):
        repl = Repl(stdout=io.StringIO())
        out = io.StringIO()
        repl.vm.stdout = out
        self.assertFalse(repl.execute("label square dup mul ret"))
        self.assertTrue(repl.execute("push 9 call square outn"))
        self.assertEqual(out.getvalue(), "81")

    def test_raw_dashes(self):
        repl = Repl(stdout=io.StringIO())
        repl.vm.stdout = io.StringIO()
        repl.execute(EM_DASH + " " + EM_DASH * 8)  # push 7
        self.assertEqual(repl.vm.stack, [7])


if __name__ == "__main__":
    unittest.main()
