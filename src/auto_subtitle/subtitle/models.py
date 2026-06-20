"""Shared data models for subtitle segments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubtitleSegment:
    """A single subtitle cue with timing and text."""

    index: int
    start: float  # seconds
    end: float  # seconds
    text_zh: str
    text_ja: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start
