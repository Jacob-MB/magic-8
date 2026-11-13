"""Octal number helpers and the magic cube's octal constants."""

# Sum of a cell and its complement: 1001 (octal) = 513 (decimal).
COMPLEMENT_SUM = 0o1001

# Sum of the 4 cells in a half-line: 2002 (octal) = 1026 (decimal).
HALF_LINE_SUM = 0o2002

# Sum of the 8 cells in a full line: 4004 (octal) = 2052 (decimal).
LINE_SUM = 0o4004

OCTAL_DIGITS = "01234567"


def to_octal(value: int) -> str:
    """Return a non-negative integer written in octal, e.g. 513 -> "1001"."""
    if value < 0:
        raise ValueError(f"Expected a non-negative number, got {value}")
    return format(value, "o")


def parse_octal(text: str) -> int | None:
    """Read the player's octal answer.

    Spaces around the answer are ignored. Returns None if the text is empty
    or contains anything other than the digits 0-7, so the caller can treat
    it as a wrong answer.
    """
    text = text.strip()

    if text == "":
        return None

    for character in text:
        if character not in OCTAL_DIGITS:
            return None

    return int(text, 8)
