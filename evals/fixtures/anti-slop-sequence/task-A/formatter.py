"""Output formatting utilities for calculator results."""


def _pad_value(value, width=10):
    """Internal helper: right-align a value within the given width."""
    return str(value).rjust(width)


def format_result(operation, a, b, result):
    """Format a calculation result as a human-readable string."""
    return f"{a} {operation} {b} = {result}"


def format_error(message):
    """Format an error message with a standard prefix."""
    return f"Error: {message}"
