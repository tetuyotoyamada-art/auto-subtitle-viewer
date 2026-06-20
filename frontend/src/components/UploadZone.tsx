import { useCallback, useRef, useState } from 'react'

interface UploadZoneProps {
  disabled?: boolean
  onFileSelect: (file: File) => void
}

const ACCEPT = 'video/*,audio/*,.mp4,.mkv,.webm,.mov,.avi,.m4a,.wav'

export function UploadZone({ disabled, onFileSelect }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file || disabled) return
      onFileSelect(file)
    },
    [disabled, onFileSelect],
  )

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault()
      setIsDragging(false)
      handleFile(event.dataTransfer.files[0])
    },
    [handleFile],
  )

  return (
    <div
      className={`upload-zone${isDragging ? ' upload-zone--active' : ''}${disabled ? ' upload-zone--disabled' : ''}`}
      onDragEnter={(e) => {
        e.preventDefault()
        if (!disabled) setIsDragging(true)
      }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={(e) => {
        e.preventDefault()
        setIsDragging(false)
      }}
      onDrop={onDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          inputRef.current?.click()
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        hidden
        disabled={disabled}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <div className="upload-zone__icon" aria-hidden="true">
        ⬆
      </div>
      <h2 className="upload-zone__title">
        動画をドラッグ＆ドロップ
      </h2>
      <p className="upload-zone__hint">
        日本語・韓国語など多言語の自動認識に対応
      </p>
      <p className="upload-zone__hint">またはクリックしてファイルを選択</p>
      <p className="upload-zone__formats">MP4 / MKV / WebM / MOV など</p>
    </div>
  )
}
