"""ISBN validation and normalization.

Every ingest path funnels raw identifiers through here so the database stores a single
canonical key (ISBN-13, digits only) and never accepts a record whose check digit is wrong.

References:
- ISBN-10 / ISBN-13 check-digit algorithms (ISO 2108).
"""

from __future__ import annotations

import re

_NON_ISBN_CHARS = re.compile(r"[^0-9Xx]")
# 978/979 are the only valid Bookland EAN prefixes for ISBN-13.
_VALID_PREFIXES = ("978", "979")


def clean(raw: str) -> str:
    """Strip hyphens, spaces and any other separators, upper-casing a trailing 'x'."""
    return _NON_ISBN_CHARS.sub("", raw).upper()


def is_valid_isbn10(value: str) -> bool:
    """Validate an ISBN-10 by its mod-11 check digit ('X' == 10)."""
    digits = clean(value)
    if len(digits) != 10:
        return False
    total = 0
    for position, char in enumerate(digits):
        if char == "X":
            # 'X' is only allowed as the final check digit.
            if position != 9:
                return False
            value_at = 10
        elif char.isdigit():
            value_at = int(char)
        else:
            return False
        total += (10 - position) * value_at
    return total % 11 == 0


def is_valid_isbn13(value: str) -> bool:
    """Validate an ISBN-13 by its mod-10 (EAN-13) check digit."""
    digits = clean(value)
    if len(digits) != 13 or not digits.isdigit():
        return False
    if not digits.startswith(_VALID_PREFIXES):
        return False
    total = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(digits))
    return total % 10 == 0


def is_valid(value: str) -> bool:
    """True if ``value`` is a valid ISBN-10 or ISBN-13."""
    digits = clean(value)
    if len(digits) == 10:
        return is_valid_isbn10(digits)
    if len(digits) == 13:
        return is_valid_isbn13(digits)
    return False


def _isbn13_check_digit(first12: str) -> str:
    total = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def _isbn10_check_digit(first9: str) -> str:
    total = sum((10 - i) * int(d) for i, d in enumerate(first9))
    remainder = (11 - total % 11) % 11
    return "X" if remainder == 10 else str(remainder)


def to_isbn13(value: str) -> str | None:
    """Convert a valid ISBN-10 or ISBN-13 to canonical ISBN-13 form; ``None`` if invalid."""
    digits = clean(value)
    if len(digits) == 13:
        return digits if is_valid_isbn13(digits) else None
    if len(digits) == 10 and is_valid_isbn10(digits):
        body = "978" + digits[:9]
        return body + _isbn13_check_digit(body)
    return None


def to_isbn10(value: str) -> str | None:
    """Convert to ISBN-10 when possible (only 978-prefixed ISBN-13s have one)."""
    digits = clean(value)
    if len(digits) == 10:
        return digits if is_valid_isbn10(digits) else None
    if len(digits) == 13 and is_valid_isbn13(digits) and digits.startswith("978"):
        body = digits[3:12]
        return body + _isbn10_check_digit(body)
    return None


def normalize(value: str) -> str | None:
    """Return the canonical database key (ISBN-13, digits only) or ``None`` if invalid.

    This is the single entry point ingest code should call before storing an identifier.
    """
    return to_isbn13(value)
