"""Basic calculator module with arithmetic operations."""

import math


def _validate_numbers(a, b):
    """Internal helper: ensure both arguments are numeric."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both arguments must be numbers")


def _validate_number(a):
    """Internal helper: ensure argument is numeric."""
    if not isinstance(a, (int, float)):
        raise TypeError("Argument must be a number")


def add(a, b):
    """Return the sum of a and b."""
    _validate_numbers(a, b)
    return a + b


def subtract(a, b):
    """Return the difference of a and b."""
    _validate_numbers(a, b)
    return a - b


def multiply(a, b):
    """Return the product of a and b."""
    _validate_numbers(a, b)
    return a * b


def divide(a, b):
    """Return the quotient of a divided by b.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    _validate_numbers(a, b)
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


def power(base, exponent):
    """Return base raised to the power of exponent."""
    _validate_numbers(base, exponent)
    return base ** exponent


def square_root(a):
    """Return the square root of a.

    Raises:
        ValueError: If a is negative.
    """
    _validate_number(a)
    if a < 0:
        raise ValueError("Cannot take square root of a negative number")
    return math.sqrt(a)


def batch_calculate(operation, pairs):
    """Apply an operation to each (a, b) pair and return a list of results.

    Args:
        operation: A callable taking two arguments.
        pairs: An iterable of (a, b) tuples.

    Returns:
        A list of results, one per pair.
    """
    return [operation(a, b) for a, b in pairs]
