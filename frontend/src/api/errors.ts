import axios from 'axios'

/** APIエラーからユーザー向けメッセージ（FastAPIのdetail）を取り出す */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}
