<script setup lang="ts">
import { useSettingsStore } from '@/stores/settings'

withDefaults(defineProps<{ showActions?: boolean }>(), { showActions: true })
defineEmits<{ refresh: []; server: []; about: [] }>()

const settings = useSettingsStore()
</script>

<template>
  <header class="topbar">
    <h1>Складской учёт</h1>
    <div class="actions">
      <span class="theme-label">Тема:</span>
      <div class="segment" role="group" aria-label="Тема">
        <button
          type="button"
          :class="{ active: settings.theme === 'light' }"
          @click="settings.applyTheme('light')"
        >
          Светлая
        </button>
        <button
          type="button"
          :class="{ active: settings.theme === 'dark' }"
          @click="settings.applyTheme('dark')"
        >
          Тёмная
        </button>
      </div>
      <button v-if="showActions" type="button" class="btn" @click="$emit('refresh')">Обновить</button>
      <button v-if="showActions" type="button" class="btn ghost" @click="$emit('server')">Сервер</button>
      <button type="button" class="btn ghost" @click="$emit('about')">О программе</button>
    </div>
  </header>
  <div class="sep" />
</template>

<style scoped lang="scss">
.topbar {
  height: 52px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px 0 18px;
  background: var(--panel-bg);
}

h1 {
  margin: 0;
  font-size: 16px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.theme-label {
  color: var(--muted);
}

.segment {
  display: flex;
  height: 30px;
  padding: 2px;
  border-radius: 8px;
  background: var(--segment-bg);
}

.segment button {
  border: 0;
  border-radius: 6px;
  padding: 0 12px;
  background: transparent;
  color: #fff;
  cursor: pointer;
}

.segment button.active {
  background: var(--button-bg);
}

.segment button:hover:not(.active) {
  background: rgba(255, 255, 255, 0.08);
}
</style>
