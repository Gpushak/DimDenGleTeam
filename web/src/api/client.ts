import type {
  BoxDto,
  BoxTypeDto,
  DeleteBoxResult,
  HealthDto,
  ItemDto,
  ItemQuery,
  ItemTypeDto,
  ScaleDto,
} from '@/api/types'

const TIMEOUT_MS = 10_000

export class ApiError extends Error {
  status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}

function detailText(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: unknown }).msg)
        }
        return String(item)
      })
      .join('; ')
  }
  if (detail == null) return 'Ошибка сервера'
  try {
    return JSON.stringify(detail)
  } catch {
    return String(detail)
  }
}

export class ApiClient {
  baseUrl = ''

  setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/+$/, '')
  }

  health(): Promise<HealthDto> {
    return this.get<HealthDto>('/health')
  }

  healthAt(baseUrl: string): Promise<HealthDto> {
    return this.request<HealthDto>('/health', { baseUrl })
  }

  getBoxes(): Promise<BoxDto[]> {
    return this.get<BoxDto[]>('/boxes')
  }

  getBox(id: number): Promise<BoxDto> {
    return this.get<BoxDto>(`/boxes/${id}`)
  }

  createBox(body: { name: string; box_type_id: number; parent_id: number | null }): Promise<BoxDto> {
    return this.post<BoxDto>('/boxes', body)
  }

  updateBox(id: number, body: { name: string; box_type_id: number }): Promise<BoxDto> {
    return this.patch<BoxDto>(`/boxes/${id}`, body)
  }

  moveBox(id: number, parentId: number | null): Promise<BoxDto> {
    return this.post<BoxDto>(`/boxes/${id}/move`, { parent_id: parentId })
  }

  deleteBox(id: number): Promise<DeleteBoxResult> {
    return this.delete<DeleteBoxResult>(`/boxes/${id}`)
  }

  getBoxTypes(): Promise<BoxTypeDto[]> {
    return this.get<BoxTypeDto[]>('/box-types')
  }

  getItemTypes(): Promise<ItemTypeDto[]> {
    return this.get<ItemTypeDto[]>('/item-types')
  }

  createItemType(body: { name: string; weight_g: number | null }): Promise<ItemTypeDto> {
    return this.post<ItemTypeDto>('/item-types', body)
  }

  getItems(query: ItemQuery = {}): Promise<ItemDto[]> {
    return this.get<ItemDto[]>('/items', query)
  }

  getItem(id: number): Promise<ItemDto> {
    return this.get<ItemDto>(`/items/${id}`)
  }

  createItem(body: {
    item_type_id: number
    box_id: number | null
    quantity: number
  }): Promise<ItemDto> {
    return this.post<ItemDto>('/items', body)
  }

  updateItem(
    id: number,
    body: { item_type_id: number; box_id: number | null; quantity: number },
  ): Promise<ItemDto> {
    return this.patch<ItemDto>(`/items/${id}`, body)
  }

  deleteItem(id: number): Promise<void> {
    return this.delete<void>(`/items/${id}`)
  }

  getScale(): Promise<ScaleDto> {
    return this.get<ScaleDto>('/scale')
  }

  private get<T>(path: string, query?: ItemQuery): Promise<T> {
    return this.request<T>(path, { query })
  }

  private post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: 'POST', body })
  }

  private patch<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: 'PATCH', body })
  }

  private delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' })
  }

  private async request<T>(
    path: string,
    options: { method?: string; body?: unknown; query?: ItemQuery; baseUrl?: string } = {},
  ): Promise<T> {
    const base = (options.baseUrl ?? this.baseUrl).replace(/\/+$/, '')
    const url = new URL(base + path)
    if (options.query) {
      for (const [key, value] of Object.entries(options.query)) {
        if (value != null) url.searchParams.set(key, String(value))
      }
    }

    const headers: Record<string, string> = { Accept: 'application/json' }
    let body: string | undefined
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(options.body)
    }

    try {
      const response = await fetch(url, {
        method: options.method ?? 'GET',
        headers,
        body,
        signal: AbortSignal.timeout(TIMEOUT_MS),
      })
      const raw = await response.text()
      const payload = raw ? parseJson(raw) : null
      if (!response.ok) {
        const detail =
          payload && typeof payload === 'object' && 'detail' in payload
            ? (payload as { detail: unknown }).detail
            : raw
        throw new ApiError(detailText(detail) || response.statusText, response.status)
      }
      return payload as T
    } catch (error) {
      if (error instanceof ApiError) throw error
      if (error instanceof DOMException && (error.name === 'TimeoutError' || error.name === 'AbortError')) {
        throw new ApiError(
          `Сервер не отвечает (${base}): превышено время ожидания. Проверьте адрес общего сервера.`,
        )
      }
      const reason = error instanceof Error ? error.message : String(error)
      throw new ApiError(`Сервер недоступен (${base}): ${reason}. Проверьте адрес общего сервера.`)
    }
  }
}

function parseJson(raw: string): unknown {
  try {
    return JSON.parse(raw) as unknown
  } catch {
    return raw
  }
}

export const api = new ApiClient()
