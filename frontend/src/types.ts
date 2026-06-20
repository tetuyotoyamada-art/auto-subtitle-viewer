export type SubtitleFormat = 'vtt' | 'srt'

export interface Segment {
  index: number
  start: number
  end: number
  text_zh: string
  text_ja: string
}

export interface SubtitleGenerateResponse {
  format: SubtitleFormat
  subtitle_content: string
  segments: Segment[]
  segment_count: number
}

export type JobStage =
  | 'idle'
  | 'uploading'
  | 'preparing'
  | 'transcribing'
  | 'transcribed'
  | 'translating'
  | 'formatting'
  | 'ready'
  | 'error'

export type ProcessingStage = JobStage

export interface ProgressEvent {
  stage: 'preparing' | 'transcribing' | 'transcribed' | 'translating' | 'formatting' | 'complete'
  message: string
  segment_count?: number | null
}

export interface ProgressState {
  stage: JobStage
  message: string
  segmentCount?: number
}

export interface SubtitleStyle {
  fontSize: number
  color: string
  backgroundColor: string
}

export interface AppErrorInfo {
  title: string
  message: string
  hint?: string
  statusCode?: number
}
