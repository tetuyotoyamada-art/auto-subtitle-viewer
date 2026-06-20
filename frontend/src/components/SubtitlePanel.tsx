import { useEffect, useRef } from 'react'
import type { Segment } from '../types'

interface SubtitlePanelProps {
  segments: Segment[]
  currentTime: number
  onSeek: (time: number) => void
}

function formatClock(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function SubtitlePanel({ segments, currentTime, onSeek }: SubtitlePanelProps) {
  const listRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLButtonElement>(null)

  const activeIndex = segments.findIndex(
    (seg) => currentTime >= seg.start && currentTime < seg.end,
  )

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [activeIndex])

  if (segments.length === 0) {
    return (
      <aside className="subtitle-panel">
        <header className="subtitle-panel__header">
          <h2>字幕</h2>
        </header>
        <p className="subtitle-panel__empty">字幕データがありません</p>
      </aside>
    )
  }

  return (
    <aside className="subtitle-panel">
      <header className="subtitle-panel__header">
        <h2>字幕</h2>
        <span className="subtitle-panel__count">{segments.length} 件</span>
      </header>

      <div className="subtitle-panel__list" ref={listRef}>
        {segments.map((seg, index) => {
          const isActive = index === activeIndex
          return (
            <button
              key={seg.index}
              ref={isActive ? activeRef : undefined}
              type="button"
              className={`subtitle-item${isActive ? ' subtitle-item--active' : ''}`}
              onClick={() => onSeek(seg.start)}
            >
              <time className="subtitle-item__time">
                {formatClock(seg.start)} → {formatClock(seg.end)}
              </time>
              <p className="subtitle-item__ja">{seg.text_ja || '—'}</p>
              <p className="subtitle-item__zh">{seg.text_zh}</p>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
