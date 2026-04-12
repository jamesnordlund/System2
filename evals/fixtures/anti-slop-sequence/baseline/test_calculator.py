"""Tests for the calculator and formatter modules."""

import unittest
from calculator import add, subtract, multiply
from formatter import format_result, format_error


class TestAdd(unittest.TestCase):
    def test_add_positive(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self):
        self.assertEqual(add(-1, -2), -3)


class TestSubtract(unittest.TestCase):
    def test_subtract_basic(self):
        self.assertEqual(subtract(10, 4), 6)


class TestMultiply(unittest.TestCase):
    def test_multiply_basic(self):
        self.assertEqual(multiply(3, 7), 21)


class TestFormatter(unittest.TestCase):
    def test_format_result(self):
        self.assertEqual(format_result("+", 2, 3, 5), "2 + 3 = 5")

    def test_format_error(self):
        self.assertEqual(format_error("bad input"), "Error: bad input")


if __name__ == "__main__":
    unittest.main()
