"""Unicode-safe text normalization shared by indexing and search."""

import html
import re
import unicodedata

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_UNSUPPORTED_CHAR_RE = re.compile(r"[^\w\s]")
_TEXT_FIELD_CHAR_RE = re.compile(r"[^\w\s:.-]")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str, preserve_punctuation: bool = False) -> str:
    """Normalize text without dropping non-ASCII letters such as Cyrillic."""
    if not text:
        return ""

    normalized = html.unescape(unicodedata.normalize("NFKC", text))
    normalized = unicodedata.normalize("NFD", normalized)

    normalized_chars: list[str] = []
    for char in normalized:
        if unicodedata.category(char) == "Mn":
            previous_char = normalized_chars[-1] if normalized_chars else ""
            if not ("\u0400" <= previous_char <= "\u04ff"):
                continue
        normalized_chars.append(char)
    normalized = unicodedata.normalize("NFC", "".join(normalized_chars))

    normalized = _HTML_TAG_RE.sub(" ", normalized)
    unsupported_char_re = _TEXT_FIELD_CHAR_RE if preserve_punctuation else _UNSUPPORTED_CHAR_RE
    normalized = unsupported_char_re.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)

    return normalized.lower().strip()
