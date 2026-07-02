"""End-to-end tests: every shipped example runs and produces its output.

Each example is tested both from its assembly source (.emda) and from
the committed em dash form (.emd) to make sure the two stay in sync.
"""

import unittest

from emdashy.assembler import assemble_program
from emdashy.parser import parse_source

from helpers import example, run_vm


class ExampleTests(unittest.TestCase):
    def run_both(self, name, stdin=""):
        """Run NAME.emda and NAME.emd; assert they agree and return stdout."""
        from_asm, _ = run_vm(assemble_program(example(name + ".emda")), stdin)
        from_emd, _ = run_vm(parse_source(example(name + ".emd")), stdin)
        self.assertEqual(from_asm, from_emd,
                         f"{name}.emd is out of date with {name}.emda")
        return from_asm

    def test_hello(self):
        self.assertEqual(self.run_both("hello"), "Hello, World!\n")

    def test_adder(self):
        self.assertEqual(self.run_both("adder", "17 25\n"), "42\n")

    def test_cat(self):
        text = "em dashes — all the way down\n"
        self.assertEqual(self.run_both("cat", text), text)

    def test_factorial(self):
        self.assertEqual(self.run_both("factorial", "5\n"), "120\n")
        self.assertEqual(self.run_both("factorial", "0\n"), "1\n")
        self.assertEqual(self.run_both("factorial", "20\n"),
                         "2432902008176640000\n")

    def test_fibonacci(self):
        self.assertEqual(self.run_both("fibonacci"),
                         "0\n1\n1\n2\n3\n5\n8\n13\n21\n34\n")

    def test_truth_machine_zero(self):
        self.assertEqual(self.run_both("truth_machine", "0\n"), "0\n")

    def test_fizzbuzz(self):
        out = self.run_both("fizzbuzz")
        lines = out.splitlines()
        self.assertEqual(len(lines), 100)
        self.assertEqual(lines[0], "1")
        self.assertEqual(lines[2], "Fizz")
        self.assertEqual(lines[4], "Buzz")
        self.assertEqual(lines[14], "FizzBuzz")
        self.assertEqual(lines[99], "Buzz")


if __name__ == "__main__":
    unittest.main()
