"""Number Base Translation Module.

The game logic works only with plain integers. This module converts those
integers into the number base shown to the player, and reads the player's
answers back from that base. Changing the base the player sees only needs a
change here (or a different base passed in), not in the game logic.
"""

# The base the player sees numbers in.
DISPLAY_BASE = 8

# Digits used to write numbers, in order of value. Supports bases 2 to 16.
DIGITS = "0123456789ABCDEF"


def to_display(value: int, base: int = DISPLAY_BASE) -> str:
    """Write a non-negative integer in the given base.

    Example: to_display(513) returns "1001", since 513 is 1001 in octal.
    """
    _check_base(base)
    if value < 0:
        raise ValueError(f"Expected a non-negative number, got {value}")

    if value == 0:
        return "0"

    # Build the number from its last digit to its first.
    #
    # The remainder after dividing by the base is the last digit, and
    # dividing by the base (dropping the remainder) removes that digit.
    # Repeating this gives each digit in turn, from last to first, until
    # nothing is left. For example, 100 in octal:
    #     100 % 8 = 4, 100 // 8 = 12  -> last digit 4
    #      12 % 8 = 4,  12 // 8 = 1   -> next digit 4
    #       1 % 8 = 1,   1 // 8 = 0   -> first digit 1, stop
    # This collects the digits as 4, 4, 1 (last to first).
    digits = []
    while value > 0:
        remainder = value % base
        digits.append(DIGITS[remainder])
        value = value // base

    # The digits were collected last to first, so reverse them before
    # joining them into the written number ("144").
    digits.reverse()
    return "".join(digits)


def parse_answer(text: str, base: int = DISPLAY_BASE) -> int | None:
    """Read the player's answer, written in the given base.

    Spaces around the answer are ignored, and letters may be upper or lower
    case. Returns None if the text is empty or has any character that is not
    a digit of the base (e.g. 8 or 9 in octal), so the caller can treat it
    as a wrong answer.
    """
    _check_base(base)
    text = text.strip().upper()

    if text == "":
        return None

    allowed_digits = DIGITS[:base]
    for character in text:
        if character not in allowed_digits:
            return None

    return int(text, base)


def _check_base(base: int) -> None:
    """Check the base is one this module can write."""
    if base < 2 or base > len(DIGITS):
        raise ValueError(f"Base must be 2 to {len(DIGITS)}, got {base}")
