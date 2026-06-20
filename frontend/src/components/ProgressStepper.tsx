import type { JobStage, ProgressState } from '../types'

const STEPS: { key: JobStage; label: string }[] = [
  { key: 'uploading', label: 'アップロード' },
  { key: 'transcribing', label: '音声認識' },
  { key: 'translating', label: '翻訳' },
  { key: 'ready', label: '完了' },
]

function stepIndex(stage: JobStage): number {
  if (stage === 'idle' || stage === 'error') return -1
  if (stage === 'uploading' || stage === 'preparing') return 0
  if (stage === 'transcribing' || stage === 'transcribed') return 1
  if (stage === 'translating' || stage === 'formatting') return 2
  if (stage === 'ready') return 3
  return 0
}

interface ProgressStepperProps {
  progress: ProgressState
  isActive: boolean
}

export function ProgressStepper({ progress, isActive }: ProgressStepperProps) {
  if (!isActive && progress.stage !== 'ready') return null

  const current = stepIndex(progress.stage)

  return (
    <div className="progress-stepper" role="status" aria-live="polite">
      <div className="progress-stepper__steps">
        {STEPS.map((step, index) => {
          const completed = current > index
          const active = current === index && progress.stage !== 'ready'
          const done = progress.stage === 'ready' && index === STEPS.length - 1

          return (
            <div
              key={step.key}
              className={`progress-step${completed || done ? ' progress-step--done' : ''}${active ? ' progress-step--active' : ''}`}
            >
              <span className="progress-step__dot">{completed || done ? '✓' : index + 1}</span>
              <span className="progress-step__label">{step.label}</span>
            </div>
          )
        })}
      </div>
      {isActive && (
        <p className="progress-stepper__message">{progress.message}</p>
      )}
    </div>
  )
}
