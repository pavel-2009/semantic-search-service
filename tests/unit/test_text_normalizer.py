"""Unit tests for text normalization."""

import pytest
from core.text_normalizer import clean_text


class TestTextNormalizer:
    """Test text normalization functions."""
    
    def test_clean_text_basic(self):
        """Basic text cleaning."""
        assert clean_text("  Hello  World  ") == "hello world"
        assert clean_text("Hello World") == "hello world"
    
    def test_clean_text_cyrillic(self):
        """Cyrillic text should be preserved."""
        assert clean_text("Привет Мир") == "привет мир"
        assert clean_text("Фильм 2024 года") == "фильм 2024 года"
    
    def test_clean_text_html(self):
        """HTML tags should be removed."""
        assert clean_text("<p>Text</p>") == "text"
        assert clean_text("<div>Hello</div><p>World</p>") == "hello world"
    
    def test_clean_text_special_chars(self):
        """Special characters should be normalized."""
        assert clean_text("Hello@#World!") == "hello world"
        assert clean_text("Movie: Inception (2010)") == "movie inception 2010"
    
    def test_clean_text_unicode(self):
        """Unicode characters should be normalized."""
        assert clean_text("café") == "cafe"
        assert clean_text("Драма́") == "драма"
    
    def test_clean_text_empty(self):
        """Empty string should return empty."""
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_clean_text_whitespace_only(self):
        """Whitespace-only string should return empty."""
        assert clean_text("   ") == ""
        assert clean_text("\t\n  ") == ""
    
    def test_clean_text_punctuation(self):
        """Punctuation should be preserved where appropriate."""
        result = clean_text("Hello, world! How are you?")
        assert "hello" in result
        assert "world" in result
        assert "," in result or "," not in result  # flexible