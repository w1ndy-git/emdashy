"""Tests for the lexer, parser, and virtual machine."""

import unittest

from emdashy import EM_DASH
from emdashy.errors import EmdashyRuntimeError, ParseError
from emdashy.lexer import lex
from emdashy.parser import parse_source

from helpers import run_asm, run_emd


class LexerTests(unittest.TestCase):
    def test_runs_and_positions(self):
        tokens = lex("—— hi —\n———")
        self.assertEqual([(t.length, t.line, t.col) for t in tokens],
                         [(2, 1, 1), (1, 1, 7), (3, 2, 1)])

    def test_everything_else_is_comment(self):
        # Hyphens, en dashes, minus signs and words are all ignored.
        tokens = lex("-- – hello −—–—-—")
        self.assertEqual([t.length for t in tokens], [1, 1, 1])

    def test_empty(self):
        self.assertEqual(lex(""), [])
        self.assertEqual(lex("no dashes at all"), [])


class ParserTests(unittest.TestCase):
    def test_push_encoding(self):
        # push (1 dash) followed by a run of 6 pushes the literal 5.
        program = parse_source(EM_DASH + " " + EM_DASH * 6)
        self.assertEqual(program.instrs[0].name, "push")
        self.assertEqual(program.instrs[0].arg, 5)

    def test_unknown_opcode(self):
        with self.assertRaises(ParseError) as ctx:
            parse_source(EM_DASH * 99)
        self.assertIn("99", str(ctx.exception))

    def test_missing_operand(self):
        with self.assertRaises(ParseError):
            parse_source(EM_DASH)  # a lone push with no operand run

    def test_duplicate_label(self):
        label = EM_DASH * 15
        with self.assertRaises(ParseError):
            parse_source(f"{label} {EM_DASH} {label} {EM_DASH}")

    def test_undefined_jump_target(self):
        with self.assertRaises(ParseError):
            parse_source(EM_DASH * 16 + " " + EM_DASH * 3)  # jmp L3


class VMTests(unittest.TestCase):
    def assertRuns(self, asm, expected, stdin=""):
        out, _ = run_asm(asm, stdin)
        self.assertEqual(out, expected)

    def test_arithmetic(self):
        self.assertRuns("push 6 push 7 mul outn", "42")
        self.assertRuns("push 10 push 3 sub outn", "7")
        self.assertRuns("push 1 push 2 add outn", "3")

    def test_floor_division_and_modulo(self):
        self.assertRuns("push 7 push 2 div outn", "3")
        self.assertRuns("push -7 push 2 div outn", "-4")
        self.assertRuns("push 7 push -2 div outn", "-4")
        self.assertRuns("push -7 push 2 mod outn", "1")
        self.assertRuns("push 7 push -2 mod outn", "-1")

    def test_division_by_zero(self):
        with self.assertRaises(EmdashyRuntimeError):
            run_asm("push 1 push 0 div")
        with self.assertRaises(EmdashyRuntimeError):
            run_asm("push 1 push 0 mod")

    def test_stack_manipulation(self):
        _, vm = run_asm("push 1 push 2 dup")
        self.assertEqual(vm.stack, [1, 2, 2])
        _, vm = run_asm("push 1 push 2 swap")
        self.assertEqual(vm.stack, [2, 1])
        _, vm = run_asm("push 1 push 2 over")
        self.assertEqual(vm.stack, [1, 2, 1])
        _, vm = run_asm("push 1 push 2 pop")
        self.assertEqual(vm.stack, [1])

    def test_comparisons(self):
        self.assertRuns("push 3 push 3 eq outn", "1")
        self.assertRuns("push 3 push 4 eq outn", "0")
        self.assertRuns("push 3 push 4 lt outn", "1")
        self.assertRuns("push 3 push 4 gt outn", "0")

    def test_stack_underflow_has_location(self):
        with self.assertRaises(EmdashyRuntimeError) as ctx:
            run_asm("add")
        self.assertIn("underflow", str(ctx.exception))

    def test_control_flow(self):
        # Count 3, 2, 1 using a loop.
        asm = """
            push 3
        loop:
            dup jz done
            dup outn
            push 1 sub
            jmp loop
        done:
            halt
        """
        self.assertRuns(asm, "321")

    def test_call_and_ret(self):
        asm = """
            push 5 call double outn halt
        double:
            push 2 mul ret
        """
        self.assertRuns(asm, "10")

    def test_ret_outside_call(self):
        with self.assertRaises(EmdashyRuntimeError):
            run_asm("ret")

    def test_heap(self):
        self.assertRuns("push 42 push 7 store push 42 load outn", "7")
        # Uninitialised cells read as zero.
        self.assertRuns("push 999 load outn", "0")

    def test_io(self):
        self.assertRuns("inn inn add outn", "30", stdin="10 20\n")
        self.assertRuns("inn outn", "-5", stdin="  -5")
        self.assertRuns("inc outc inc outc", "hi", stdin="hi")
        # inc pushes -1 at EOF.
        self.assertRuns("inc outn", "-1", stdin="")

    def test_outc_unicode(self):
        self.assertRuns("push 8212 outc", "—")

    def test_outc_invalid(self):
        with self.assertRaises(EmdashyRuntimeError):
            run_asm("push -1 outc")

    def test_bignums(self):
        self.assertRuns("push 10 call fact outn halt "
                        "label fact push 1 label l over jz d over mul swap "
                        "push 1 sub swap jmp l label d swap pop ret",
                        "3628800")

    def test_halt_and_fall_off_end(self):
        self.assertRuns("push 1 outn halt push 2 outn", "1")
        self.assertRuns("push 1 outn", "1")  # implicit halt at the end

    def test_max_steps_guard(self):
        with self.assertRaises(EmdashyRuntimeError):
            run_asm("label spin jmp spin", max_steps=1000)

    def test_raw_emd_program(self):
        # push 2, push 3, add, outn — written directly in em dashes.
        push, add, outn = EM_DASH, EM_DASH * 6, EM_DASH * 23
        src = f"{push} {EM_DASH * 3} {push} {EM_DASH * 4} {add} {outn}"
        out, _ = run_emd(src)
        self.assertEqual(out, "5")


if __name__ == "__main__":
    unittest.main()
