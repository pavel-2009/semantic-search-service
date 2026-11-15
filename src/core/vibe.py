"""Vibe text shared by indexing and search so documents and queries live in one format.

Example: "Мрачный, жуткий."
"""

from collections.abc import Iterable


def format_vibe(moods: Iterable[str]) -> str | None:
    """Join mood tags into one short sentence, or None when there are none."""
    text = ", ".join(dict.fromkeys(moods))
    return f"{text[0].upper()}{text[1:]}." if text else None
