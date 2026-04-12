"""Tests for the calculator and formatter modules."""

import unittest
from calculator import add, subtract, multiply, divide, power, square_root
from calculator import batch_calculate
from formatter import format_result, format_error, format_table


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


class TestDivide(unittest.TestCase):
    def test_divide_basic(self):
        self.assertEqual(divide(10, 2), 5.0)

    def test_divide_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            divide(10, 0)

    def test_divide_float_result(self):
        self.assertAlmostEqual(divide(7, 2), 3.5)


class TestPower(unittest.TestCase):
    def test_power_basic(self):
        self.assertEqual(power(2, 3), 8)

    def test_power_zero_exponent(self):
        self.assertEqual(power(5, 0), 1)


class TestSquareRoot(unittest.TestCase):
    def test_square_root_basic(self):
        self.assertEqual(square_root(9), 3.0)

    def test_square_root_negative(self):
        with self.assertRaises(ValueError):
            square_root(-4)


class TestBatchCalculate(unittest.TestCase):
    def test_batch_add(self):
        result = batch_calculate(add, [(1, 2), (3, 4), (5, 6)])
        self.assertEqual(result, [3, 7, 11])

    def test_batch_empty(self):
        result = batch_calculate(add, [])
        self.assertEqual(result, [])


class TestFormatter(unittest.TestCase):
    def test_format_result(self):
        self.assertEqual(format_result("+", 2, 3, 5), "2 + 3 = 5")

    def test_format_error(self):
        self.assertEqual(format_error("bad input"), "Error: bad input")

    def test_format_table(self):
        rows = ["2 + 3 = 5", "10 - 4 = 6"]
        expected = "  1. 2 + 3 = 5\n  2. 10 - 4 = 6"
        self.assertEqual(format_table(rows), expected)


if __name__ == "__main__":
    unittest.main()
