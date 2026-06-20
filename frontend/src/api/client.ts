import type {
  AppErrorInfo,
  ProgressEvent,
  SubtitleFormat,
  SubtitleGenerateResponse,
} from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function toFriendlyError(error: unknown): AppErrorInfo {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 400:
        return {
          title: 'リクエストエラー',
          message: error.message,
          hint: 'ファイル形式やパラメータを確認してください。',
          statusCode: 400,
        }
      case 404:
        return {
          title: 'ファイルが見つかりません',
          message: error.message,
          hint: '動画ファイルのパスや内容を確認してください。',
          statusCode: 404,
        }
      case 429:
        return {
          title: 'API 利用制限に達しました',
          message: error.message,
          hint: 'Gemini API の無料枠レート制限です。1〜2分待ってから再試行してください。',
          statusCode: 429,
        }
      case 500:
        return {
          title: 'サーバー内部エラー',
          message: error.message,
          hint: 'バックエンドのログを確認するか、しばらく待ってから再試行してください。',
          statusCode: 500,
        }
      default:
        return {
          title: `API エラー (${error.status})`,
          message: error.message,
          statusCode: error.status,
        }
    }
  }

  if (error instanceof TypeError && String(error.message).includes('fetch')) {
    return {
      title: 'API に接続できません',
      message: 'バックエンドサーバーへ接続できませんでした。',
      hint: 'uvicorn auto_subtitle.api.app:app --reload が起動しているか確認してください。',
    }
  }

  if (error instanceof Error) {
    return {
      title: 'エラーが発生しました',
      message: error.message,
    }
  }

  return {
    title: '不明なエラー',
    message: '予期しないエラーが発生しました。',
    hint: 'ページを再読み込みして、もう一度お試しください。',
  }
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  let detail = `HTTP ${response.status}`
  try {
    const body = (await response.json()) as { detail?: string | { msg?: string }[] }
    if (typeof body.detail === 'string') {
      detail = body.detail
    } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      detail = body.detail[0].msg
    }
  } catch {
    // ignore JSON parse errors
  }
  return new ApiError(detail, response.status)
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/health`)
    return response.ok
  } catch {
    return false
  }
}

function buildFormData(
  file: File,
  options: { format?: SubtitleFormat; device?: 'cuda' | 'cpu' },
): FormData {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('format', options.format ?? 'vtt')
  formData.append('device', options.device ?? 'cuda')
  return formData
}

function parseSseBlock(block: string): { event: string; data: string } | null {
  const lines = block.split('\n')
  let event = 'message'
  const dataLines: string[] = []

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }

  if (dataLines.length === 0) return null
  return { event, data: dataLines.join('\n') }
}

export async function generateSubtitlesStream(
  file: File,
  options: {
    format?: SubtitleFormat
    device?: 'cuda' | 'cpu'
  },
  onProgress: (event: ProgressEvent) => void,
): Promise<SubtitleGenerateResponse> {
  const response = await fetch(`${API_BASE}/api/subtitles/generate-stream`, {
    method: 'POST',
    body: buildFormData(file, options),
  })

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  if (!response.body) {
    throw new ApiError('サーバーからの応答ストリームを取得できませんでした。', 500)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result: SubtitleGenerateResponse | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const parsed = parseSseBlock(part.trim())
      if (!parsed) continue

      if (parsed.event === 'progress') {
        onProgress(JSON.parse(parsed.data) as ProgressEvent)
      } else if (parsed.event === 'complete') {
        result = JSON.parse(parsed.data) as SubtitleGenerateResponse
      } else if (parsed.event === 'error') {
        const payload = JSON.parse(parsed.data) as { detail: string; status_code?: number }
        throw new ApiError(payload.detail, payload.status_code ?? 500)
      }
    }
  }

  if (!result) {
    throw new ApiError('処理は完了しましたが、字幕データを受信できませんでした。', 500)
  }

  return result
}

export async function generateSubtitles(
  file: File,
  options: {
    format?: SubtitleFormat
    device?: 'cuda' | 'cpu'
  } = {},
): Promise<SubtitleGenerateResponse> {
  const response = await fetch(`${API_BASE}/api/subtitles/generate`, {
    method: 'POST',
    body: buildFormData(file, options),
  })

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  return response.json() as Promise<SubtitleGenerateResponse>
}
