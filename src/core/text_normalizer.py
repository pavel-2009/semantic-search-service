"""Unicode-safe text normalization shared by indexing and search."""

import html
import re
import unicodedata


_HTML_TAG_RE = re.compile(r"<[^>]*>")
_UNSUPPORTED_CHAR_RE = re.compile(r"[^\w\s.,!?\"':;%()\-]")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Normalize text without dropping non-ASCII letters such as Cyrillic."""
    if not text:
        return ""

    normalized = html.unescape(unicodedata.normalize("NFKC", text))
    normalized = _HTML_TAG_RE.sub(" ", normalized)
    normalized = _UNSUPPORTED_CHAR_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.lower().strip()
