"""LLM-based translation from Chinese to Japanese."""

from __future__ import annotations

import logging

from openai import OpenAI

from auto_subtitle.config import LLMConfig
from auto_subtitle.subtitle.models import SubtitleSegment

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたは中国語字幕を日本語に翻訳する専門家です。
以下のルールを厳守してください:
- 1行あたり{max_chars}文字以内に収める
- 自然な日本語の意訳を行う（直訳より読みやすさを優先）
- 原文の意味を正確に伝える
- 翻訳結果のみを返す（説明や注釈は不要）
"""


class LLMTranslator:
    """Translate subtitle segments from Chinese to Japanese via LLM API."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def translate(self, segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
        """Translate all segments, preserving timing metadata."""
        if not segments:
            return segments

        logger.info("Translating %d segments via LLM", len(segments))
        system = SYSTEM_PROMPT.format(max_chars=self._config.max_chars_per_line)

        for seg in segments:
            if not seg.text_zh:
                continue
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": seg.text_zh},
                ],
                temperature=0.3,
            )
            seg.text_ja = (response.choices[0].message.content or "").strip()

        logger.info("Translation complete")
        return segments

    def translate_batch(self, segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
        """Translate multiple segments in a single API call (future optimization)."""
        # TODO: Phase 1 enhancement — batch translation to reduce API calls
        return self.translate(segments)
