import type { Segment } from '../types'

function formatVttTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
}

export function segmentsToVtt(segments: Segment[]): string {
  const lines = ['WEBVTT', '']
  for (const seg of segments) {
    lines.push(`${formatVttTime(seg.start)} --> ${formatVttTime(seg.end)}`)
    lines.push(seg.text_ja || seg.text_zh)
    lines.push('')
  }
  return lines.join('\n')
}

export function createSubtitleBlob(content: string, format: 'vtt' | 'srt'): string {
  const mime = format === 'srt' ? 'application/x-subrip' : 'text/vtt;charset=utf-8'
  return URL.createObjectURL(new Blob([content], { type: mime }))
}

export function createVttBlobFromSegments(segments: Segment[]): string {
  return createSubtitleBlob(segmentsToVtt(segments), 'vtt')
}
