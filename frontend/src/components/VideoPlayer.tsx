import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import type { Segment, SubtitleStyle } from '../types'
import { SubtitleOverlay } from './SubtitleOverlay'

export interface VideoPlayerHandle {
  seek: (time: number) => void
}

interface VideoPlayerProps {
  videoUrl: string
  fileName?: string
  segments: Segment[]
  currentTime: number
  subtitleStyle: SubtitleStyle
  onTimeUpdate: (time: number) => void
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(
  function VideoPlayer(
    { videoUrl, fileName, segments, currentTime, subtitleStyle, onTimeUpdate },
    ref,
  ) {
    const videoRef = useRef<HTMLVideoElement>(null)

    useImperativeHandle(ref, () => ({
      seek: (time: number) => {
        const video = videoRef.current
        if (!video) return
        video.currentTime = time
        void video.play()
      },
    }))

    useEffect(() => {
      const video = videoRef.current
      if (!video) return

      const handler = () => onTimeUpdate(video.currentTime)
      video.addEventListener('timeupdate', handler)
      return () => video.removeEventListener('timeupdate', handler)
    }, [onTimeUpdate, videoUrl])

    return (
      <div className="video-player">
        <div className="video-player__frame">
          <video
            ref={videoRef}
            key={videoUrl}
            className="video-player__video"
            controls
            playsInline
            src={videoUrl}
          />
          <SubtitleOverlay
            segments={segments}
            currentTime={currentTime}
            style={subtitleStyle}
          />
        </div>
        {fileName && <p className="video-player__filename">{fileName}</p>}
      </div>
    )
  },
)
