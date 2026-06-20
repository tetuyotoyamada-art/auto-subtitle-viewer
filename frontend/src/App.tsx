import { useCallback, useEffect, useRef, useState } from 'react'
import {
  generateSubtitlesStream,
  checkHealth,
  toFriendlyError,
} from './api/client'
import { ErrorAlert } from './components/ErrorAlert'
import { ProgressStepper } from './components/ProgressStepper'
import { StatusBanner } from './components/StatusBanner'
import { SubtitlePanel } from './components/SubtitlePanel'
import { SubtitleSettings } from './components/SubtitleSettings'
import { UploadZone } from './components/UploadZone'
import { VideoPlayer, type VideoPlayerHandle } from './components/VideoPlayer'
import type {
  AppErrorInfo,
  JobStage,
  ProgressEvent,
  ProgressState,
  Segment,
  SubtitleFormat,
} from './types'
import {
  createSubtitleBlob,
} from './utils/subtitles'
import {
  loadSubtitleStyle,
  saveSubtitleStyle,
} from './utils/subtitleStyle'

const PROCESSING_STAGES: JobStage[] = [
  'uploading',
  'preparing',
  'transcribing',
  'transcribed',
  'translating',
  'formatting',
]

function mapProgressEvent(event: ProgressEvent): ProgressState {
  const stageMap: Record<ProgressEvent['stage'], JobStage> = {
    preparing: 'preparing',
    transcribing: 'transcribing',
    transcribed: 'transcribed',
    translating: 'translating',
    formatting: 'formatting',
    complete: 'ready',
  }

  return {
    stage: stageMap[event.stage],
    message: event.message,
    segmentCount: event.segment_count ?? undefined,
  }
}

export default function App() {
  const [stage, setStage] = useState<JobStage>('idle')
  const [progress, setProgress] = useState<ProgressState>({
    stage: 'idle',
    message: '',
  })
  const [error, setError] = useState<AppErrorInfo | null>(null)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [segments, setSegments] = useState<Segment[]>([])
  const [currentTime, setCurrentTime] = useState(0)
  const [format, setFormat] = useState<SubtitleFormat>('vtt')
  const [subtitleStyle, setSubtitleStyle] = useState(loadSubtitleStyle)

  const videoUrlRef = useRef<string | null>(null)
  const downloadUrlRef = useRef<string | null>(null)
  const playerRef = useRef<VideoPlayerHandle>(null)

  const revokeUrls = useCallback(() => {
    if (videoUrlRef.current) {
      URL.revokeObjectURL(videoUrlRef.current)
      videoUrlRef.current = null
    }
    if (downloadUrlRef.current) {
      URL.revokeObjectURL(downloadUrlRef.current)
      downloadUrlRef.current = null
    }
  }, [])

  useEffect(() => {
    checkHealth().then(setApiOnline)
    return () => revokeUrls()
  }, [revokeUrls])

  useEffect(() => {
    saveSubtitleStyle(subtitleStyle)
  }, [subtitleStyle])

  const processFile = useCallback(
    async (file: File) => {
      revokeUrls()
      setError(null)
      setSegments([])
      setCurrentTime(0)
      setStage('uploading')
      setProgress({ stage: 'uploading', message: '動画をアップロードしています…' })

      const nextVideoUrl = URL.createObjectURL(file)
      videoUrlRef.current = nextVideoUrl
      setVideoUrl(nextVideoUrl)
      setSelectedFile(file)

      try {
        const result = await generateSubtitlesStream(
          file,
          { format },
          (event) => {
            const next = mapProgressEvent(event)
            setProgress(next)
            if (next.stage !== 'ready') {
              setStage(next.stage)
            }
          },
        )

        const nextDownloadUrl = createSubtitleBlob(result.subtitle_content, result.format)
        downloadUrlRef.current = nextDownloadUrl
        setDownloadUrl(nextDownloadUrl)
        setSegments(result.segments)
        setStage('ready')
        setProgress({
          stage: 'ready',
          message: `字幕生成が完了しました（${result.segment_count} セグメント）`,
          segmentCount: result.segment_count,
        })
      } catch (err) {
        setError(toFriendlyError(err))
        setStage('error')
        setProgress({ stage: 'error', message: '処理中にエラーが発生しました' })
      }
    },
    [format, revokeUrls],
  )

  const handleReset = () => {
    revokeUrls()
    setSelectedFile(null)
    setVideoUrl(null)
    setDownloadUrl(null)
    setSegments([])
    setCurrentTime(0)
    setError(null)
    setStage('idle')
    setProgress({ stage: 'idle', message: '' })
  }

  const handleSeek = (time: number) => {
    playerRef.current?.seek(time)
  }

  const isProcessing = PROCESSING_STAGES.includes(stage)

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo" aria-hidden="true">字</span>
          <div>
            <h1>Auto Subtitle Viewer</h1>
            <p>多言語動画 → 日本語字幕を自動生成</p>
          </div>
        </div>
        <div className="app-header__actions">
          {apiOnline === false && (
            <span className="app-header__badge app-header__badge--warn">
              API 未接続
            </span>
          )}
          {apiOnline === true && (
            <span className="app-header__badge app-header__badge--ok">API 接続中</span>
          )}
          <label className="format-select">
            形式
            <select
              value={format}
              disabled={isProcessing}
              onChange={(e) => setFormat(e.target.value as SubtitleFormat)}
            >
              <option value="vtt">WebVTT</option>
              <option value="srt">SRT</option>
            </select>
          </label>
          {stage !== 'idle' && (
            <button type="button" className="btn btn--ghost" onClick={handleReset} disabled={isProcessing}>
              リセット
            </button>
          )}
        </div>
      </header>

      <main className="app-main">
        {stage === 'idle' && (
          <section className="hero">
            <UploadZone disabled={isProcessing} onFileSelect={processFile} />
            <ul className="hero__steps">
              <li>動画をアップロード</li>
              <li>音声認識（多言語・自動検出）</li>
              <li>Gemini で日本語字幕に変換</li>
              <li>プレイヤーで字幕表示</li>
            </ul>
          </section>
        )}

        {stage !== 'idle' && (
          <section className="workspace">
            <ProgressStepper progress={progress} isActive={isProcessing} />

            {error && (
              <ErrorAlert
                error={error}
                onRetry={selectedFile ? () => processFile(selectedFile) : undefined}
              />
            )}

            <div className="workspace__grid">
              <div className="workspace__player">
                {videoUrl ? (
                  <VideoPlayer
                    ref={playerRef}
                    videoUrl={videoUrl}
                    fileName={selectedFile?.name}
                    segments={segments}
                    currentTime={currentTime}
                    subtitleStyle={subtitleStyle}
                    onTimeUpdate={setCurrentTime}
                  />
                ) : null}

                {stage === 'ready' && downloadUrl && (
                  <div className="workspace__toolbar">
                    <StatusBanner
                      message={`字幕生成完了（${segments.length} セグメント）`}
                      variant="success"
                    />
                    <a
                      className="btn btn--primary"
                      href={downloadUrl}
                      download={`${selectedFile?.name.replace(/\.[^.]+$/, '') ?? 'subtitle'}.${format}`}
                    >
                      字幕をダウンロード ({format.toUpperCase()})
                    </a>
                  </div>
                )}

                <SubtitleSettings
                  style={subtitleStyle}
                  onChange={setSubtitleStyle}
                  disabled={segments.length === 0}
                />
              </div>

              <SubtitlePanel
                segments={segments}
                currentTime={currentTime}
                onSeek={handleSeek}
              />
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
