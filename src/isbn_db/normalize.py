"""Publisher-name normalization for cross-source aggregation.

Source records spell the same publisher many ways: trailing MARC punctuation
("Cambridge University Press," vs "Cambridge University Press"), legal-form noise
("John Wiley & Sons Inc.," / "John Wiley & Sons, Inc.," / "John Wiley & Sons,"),
case ("MANZ'sche…" vs "Manz'sche…") and the *sine nomine* placeholder
("[s.n.]" / "s.n." / "s.n.]") that means "no publisher named" and must be dropped.

:func:`normalize_publisher` collapses those into one grouping key so analytics count a
publisher once. It is intentionally conservative — it does not try to merge genuine
sub-brands/imprints (e.g. "Diogenes" vs "Diogenes Verlag"), only spelling/punctuation/
legal-form variants of the *same* name. Non-Latin scripts (Korean, Cyrillic, CJK) are
preserved, not stripped.
"""

from __future__ import annotations

# Corporate legal-form tokens dropped when they appear as standalone words. Kept minimal
# and unambiguous; English words that double as company forms (e.g. "as") are excluded.
_LEGAL_FORMS = frozenset({
    "inc", "incorporated", "ltd", "limited", "llc", "gmbh", "plc", "ag", "corp",
    "corporation", "co", "company", "sa", "srl", "bv", "pvt", "pty", "kg", "sas",
    "sarl", "spa", "nv", "kgaa", "mbh",
})

# Placeholders for "no publisher named" / "no place" — never a real publisher.
_SINE_NOMINE = frozenset({"sn", "sl", "nn"})

_KEEP_EXTRA = frozenset("&'")


def normalize_publisher(name: str | None) -> str | None:
    """Return a canonical grouping key for ``name``, or ``None`` to drop it.

    ``None`` is returned for empty input and for *sine nomine* placeholders, signalling
    "no real publisher" so the caller can exclude the record from publisher rankings.
    """
    if not name:
        return None
    s = name.strip().casefold()
    if not s:
        return None

    # Sine-nomine detection on the alphanumeric skeleton: "[s.n.]", "s.n.", "s n" -> drop.
    skeleton = "".join(ch for ch in s if ch.isalnum())
    if skeleton in _SINE_NOMINE:
        return None

    # Split on everything that isn't a letter/digit (Unicode-aware) or kept punctuation.
    tokens = "".join(ch if (ch.isalnum() or ch in _KEEP_EXTRA) else " " for ch in s).split()
    tokens = ["&" if t == "and" else t for t in tokens]

    kept = [t for t in tokens if t not in _LEGAL_FORMS]
    if not kept:  # name was only legal-form words — fall back to the raw tokens
        kept = tokens

    # Drop dangling connectors left at the edges (e.g. "Lind & Co" -> "lind &" -> "lind").
    while kept and kept[0] == "&":
        kept.pop(0)
    while kept and kept[-1] == "&":
        kept.pop()

    key = " ".join(kept).strip()
    return key or None
