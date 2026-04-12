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


def format_table(rows):
    """Format a list of result strings as a numbered table.

    Args:
        rows: A list of strings (typically from format_result).

    Returns:
        A single string with numbered rows, one per line.
    """
    lines = []
    for i, row in enumerate(rows, 1):
        lines.append(f"  {i}. {row}")
    return "\n".join(lines)
