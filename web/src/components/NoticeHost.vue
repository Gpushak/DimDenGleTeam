<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useNoticesStore } from '@/stores/notices'

const notices = useNoticesStore()

function onKey(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (!notices.alertState && !notices.confirmState) return
  event.stopImmediatePropagation()
  if (notices.alertState) notices.closeAlert()
  else notices.closeConfirm(false)
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div v-if="notices.alertState" class="notice-layer">
    <div class="notice-card" role="alertdialog" aria-modal="true">
      <h2>{{ notices.alertState.title }}</h2>
      <p>{{ notices.alertState.message }}</p>
      <div class="form-actions">
        <button type="button" class="btn" @click="notices.closeAlert()">ОК</button>
      </div>
    </div>
  </div>
  <div v-else-if="notices.confirmState" class="notice-layer">
    <div class="notice-card" role="alertdialog" aria-modal="true">
      <h2>{{ notices.confirmState.title }}</h2>
      <p>{{ notices.confirmState.message }}</p>
      <div class="form-actions">
        <button type="button" class="btn" @click="notices.closeConfirm(true)">Да</button>
        <button type="button" class="btn ghost" @click="notices.closeConfirm(false)">Нет</button>
      </div>
    </div>
  </div>
</template>
