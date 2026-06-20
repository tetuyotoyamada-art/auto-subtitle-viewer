import type { AppErrorInfo } from '../types'

interface ErrorAlertProps {
  error: AppErrorInfo
  onRetry?: () => void
}

export function ErrorAlert({ error, onRetry }: ErrorAlertProps) {
  return (
    <div className="error-alert" role="alert">
      <div className="error-alert__icon" aria-hidden="true">!</div>
      <div className="error-alert__body">
        <h3 className="error-alert__title">{error.title}</h3>
        <p className="error-alert__message">{error.message}</p>
        {error.hint && <p className="error-alert__hint">{error.hint}</p>}
        {error.statusCode !== undefined && (
          <p className="error-alert__code">エラーコード: HTTP {error.statusCode}</p>
        )}
      </div>
      {onRetry && (
        <button type="button" className="btn btn--primary error-alert__retry" onClick={onRetry}>
          再試行
        </button>
      )}
    </div>
  )
}
