import type { SubtitleStyle } from '../types'
import { COLOR_PRESETS, FONT_SIZE_OPTIONS } from '../utils/subtitleStyle'

interface SubtitleSettingsProps {
  style: SubtitleStyle
  onChange: (style: SubtitleStyle) => void
  disabled?: boolean
}

export function SubtitleSettings({ style, onChange, disabled }: SubtitleSettingsProps) {
  return (
    <section className="subtitle-settings">
      <h3 className="subtitle-settings__title">字幕の表示設定</h3>

      <label className="subtitle-settings__field">
        <span>フォントサイズ</span>
        <select
          value={style.fontSize}
          disabled={disabled}
          onChange={(e) => onChange({ ...style, fontSize: Number(e.target.value) })}
        >
          {FONT_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>
              {size}px
            </option>
          ))}
        </select>
      </label>

      <div className="subtitle-settings__field">
        <span>文字色</span>
        <div className="subtitle-settings__colors">
          {COLOR_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              className={`color-swatch${style.color === preset.value ? ' color-swatch--active' : ''}`}
              style={{ backgroundColor: preset.value }}
              disabled={disabled}
              aria-label={preset.label}
              title={preset.label}
              onClick={() => onChange({ ...style, color: preset.value })}
            />
          ))}
          <input
            type="color"
            value={style.color}
            disabled={disabled}
            aria-label="カスタム色"
            onChange={(e) => onChange({ ...style, color: e.target.value })}
          />
        </div>
      </div>

      <p
        className="subtitle-settings__preview"
        style={{
          fontSize: `${style.fontSize}px`,
          color: style.color,
          backgroundColor: style.backgroundColor,
        }}
      >
        字幕プレビュー Sample
      </p>
    </section>
  )
}
