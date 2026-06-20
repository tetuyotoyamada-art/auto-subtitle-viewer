interface StatusBannerProps {
  message: string
  variant?: 'info' | 'error' | 'success'
}

export function StatusBanner({ message, variant = 'info' }: StatusBannerProps) {
  return (
    <div className={`status-banner status-banner--${variant}`} role="status">
      {variant === 'info' && <span className="status-banner__spinner" aria-hidden="true" />}
      <span>{message}</span>
    </div>
  )
}
