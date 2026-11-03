import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api, errorMessage } from '@/api/client'
import type { HealthDto } from '@/api/types'
import { configuredUrl, DEFAULT_API_BASE_URL, normalizeBaseUrl } from '@/lib/url'

export type ThemeMode = 'light' | 'dark'
export type ConnectionPhase = 'checking' | 'ready' | 'offline'

const THEME_KEY = 'qwentory.theme'
const URL_KEY = 'qwentory.serverUrl'

function readTheme(): ThemeMode {
  return localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark'
}

function readInitialUrl(): string {
  const saved = configuredUrl(localStorage.getItem(URL_KEY))
  if (saved) return saved
  const fromEnv = configuredUrl(import.meta.env.VITE_API_BASE_URL)
  if (fromEnv) return fromEnv
  return DEFAULT_API_BASE_URL
}

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<ThemeMode>(readTheme())
  const baseUrl = ref(readInitialUrl())
  const phase = ref<ConnectionPhase>('checking')
  const error = ref('')
  let attempt = 0

  function applyTheme(mode: ThemeMode) {
    theme.value = mode
    localStorage.setItem(THEME_KEY, mode)
    document.documentElement.dataset.theme = mode
  }

  async function connect() {
    const token = ++attempt
    phase.value = 'checking'
    error.value = ''
    api.setBaseUrl(baseUrl.value)
    try {
      await api.health()
      if (token !== attempt) return
      phase.value = 'ready'
    } catch (cause) {
      if (token !== attempt) return
      error.value = errorMessage(cause)
      phase.value = 'offline'
    }
  }

  async function useServer(raw: string): Promise<HealthDto> {
    const token = ++attempt
    try {
      const url = normalizeBaseUrl(raw)
      const health = await api.healthAt(url)
      if (token !== attempt) return health
      baseUrl.value = url
      localStorage.setItem(URL_KEY, url)
      api.setBaseUrl(url)
      phase.value = 'ready'
      error.value = ''
      return health
    } catch (cause) {
      if (token === attempt && phase.value !== 'ready') phase.value = 'offline'
      throw cause
    }
  }

  return { theme, baseUrl, phase, error, applyTheme, connect, useServer }
})
