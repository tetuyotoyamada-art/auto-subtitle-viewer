import type { Segment, SubtitleStyle } from '../types'

interface SubtitleOverlayProps {
  segments: Segment[]
  currentTime: number
  style: SubtitleStyle
}

export function SubtitleOverlay({ segments, currentTime, style }: SubtitleOverlayProps) {
  const active = segments.find(
    (seg) => currentTime >= seg.start && currentTime < seg.end,
  )

  if (!active?.text_ja) return null

  return (
    <div className="subtitle-overlay" aria-live="polite">
      <p
        className="subtitle-overlay__text"
        style={{
          fontSize: `${style.fontSize}px`,
          color: style.color,
          backgroundColor: style.backgroundColor,
        }}
      >
        {active.text_ja}
      </p>
    </div>
  )
}
