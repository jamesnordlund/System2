"""Basic calculator module with arithmetic operations."""


def _validate_numbers(a, b):
    """Internal helper: ensure both arguments are numeric."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both arguments must be numbers")


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
