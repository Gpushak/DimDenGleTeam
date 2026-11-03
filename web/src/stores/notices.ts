import { ref } from 'vue'
import { defineStore } from 'pinia'

interface AlertState {
  title: string
  message: string
  resolve: () => void
}

interface ConfirmState {
  title: string
  message: string
  resolve: (value: boolean) => void
}

export const useNoticesStore = defineStore('notices', () => {
  const alertState = ref<AlertState | null>(null)
  const confirmState = ref<ConfirmState | null>(null)

  function alert(title: string, message: string): Promise<void> {
    return new Promise((resolve) => {
      alertState.value = { title, message, resolve }
    })
  }

  function closeAlert() {
    alertState.value?.resolve()
    alertState.value = null
  }

  function confirm(title: string, message: string): Promise<boolean> {
    return new Promise((resolve) => {
      confirmState.value = { title, message, resolve }
    })
  }

  function closeConfirm(value: boolean) {
    confirmState.value?.resolve(value)
    confirmState.value = null
  }

  return { alertState, confirmState, alert, confirm, closeAlert, closeConfirm }
})
