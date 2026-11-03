<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useNoticesStore } from '@/stores/notices'

defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
const notices = useNoticesStore()

function onKey(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (notices.alertState || notices.confirmState) return
  emit('close')
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="overlay">
    <div class="dialog-card" role="dialog" aria-modal="true" :aria-label="title">
      <h2>{{ title }}</h2>
      <slot />
    </div>
  </div>
</template>
