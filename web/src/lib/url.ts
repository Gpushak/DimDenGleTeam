/** Общий сервер проекта через Tailscale — тот же адрес, что у десктопа. */
export const DEFAULT_API_BASE_URL = 'http://warehouse-server.tail96180b.ts.net:8000'

const LOOPBACK = new Set(['localhost', '::1', '0.0.0.0'])

export function normalizeBaseUrl(url: string): string {
  let text = url.trim().replace(/\/+$/, '')
  if (!text) throw new Error('Адрес сервера пустой')
  if (!/^https?:\/\//i.test(text)) text = `http://${text}`

  let host = ''
  try {
    host = new URL(text).hostname
  } catch {
    host = ''
  }
  const name = host.toLowerCase().replace(/^\[|\]$/g, '')
  if (!name || LOOPBACK.has(name) || name.startsWith('127.')) {
    throw new Error(
      'Приложение не подключается к локальному API. Укажите адрес общего сервера.',
    )
  }
  return text.replace(/\/+$/, '')
}

/** Нормализованный адрес либо null, если строка пустая или это локальный API. */
export function configuredUrl(raw: string | null | undefined): string | null {
  const text = (raw ?? '').trim()
  if (!text) return null
  try {
    return normalizeBaseUrl(text)
  } catch (error) {
    if (error instanceof Error && error.message.includes('локальному API')) return null
    throw error
  }
}
