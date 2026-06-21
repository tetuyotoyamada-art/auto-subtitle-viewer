"""Legacy OpenAI-compatible translator (batch-only; prefer core.translate_segments for Gemini)."""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from auto_subtitle.subtitle.models import SubtitleSegment

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたは字幕翻訳の専門家です。
入力 JSON の segments 配列について、各 text を text_ja に翻訳し、
同じ構造の JSON のみを1回のレスポンスで返してください。
"""


class LLMTranslator:
    """Translate subtitle segments via OpenAI-compatible API in one batch request."""

    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def translate(self, segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
        """Translate all segments in a single API call."""
        return self.translate_batch(segments)

    def translate_batch(self, segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
        if not segments:
            return segments

        payload = {
            "segment_count": len(segments),
            "segments": [
                {
                    "index": seg.index,
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text_zh,
                }
                for seg in segments
            ],
        }

        logger.info("LLM batch translation: 1 API request for %d segments", len(segments))
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            temperature=0.3,
        )

        raw = (response.choices[0].message.content or "").strip()
        try:
            parsed = json.loads(raw)
            items = parsed.get("segments", parsed) if isinstance(parsed, dict) else parsed
            by_index = {seg.index: seg for seg in segments}
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    index = item.get("index")
                    text_ja = item.get("text_ja") or item.get("text")
                    if index in by_index and isinstance(text_ja, str):
                        by_index[index].text_ja = text_ja.strip()
        except json.JSONDecodeError:
            logger.warning("LLM batch response was not valid JSON.")

        return segments
