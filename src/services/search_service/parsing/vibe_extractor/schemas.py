"""Schemas for vibe extractor"""

from dataclasses import dataclass
from typing import List


@dataclass
class VibeExtracted:
    vibe: str
    text: str
