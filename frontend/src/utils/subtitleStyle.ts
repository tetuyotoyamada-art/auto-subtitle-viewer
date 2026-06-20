import type { SubtitleStyle } from '../types'

export const DEFAULT_SUBTITLE_STYLE: SubtitleStyle = {
  fontSize: 22,
  color: '#ffffff',
  backgroundColor: 'rgba(0, 0, 0, 0.55)',
}

const STORAGE_KEY = 'auto-subtitle-style'

export function loadSubtitleStyle(): SubtitleStyle {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_SUBTITLE_STYLE
    return { ...DEFAULT_SUBTITLE_STYLE, ...JSON.parse(raw) } as SubtitleStyle
  } catch {
    return DEFAULT_SUBTITLE_STYLE
  }
}

export function saveSubtitleStyle(style: SubtitleStyle): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(style))
}

export const FONT_SIZE_OPTIONS = [16, 18, 22, 26, 30, 36, 42] as const

export const COLOR_PRESETS = [
  { label: '白', value: '#ffffff' },
  { label: '黄', value: '#ffe066' },
  { label: 'シアン', value: '#3dd6c6' },
  { label: 'ピンク', value: '#ff8fab' },
] as const
