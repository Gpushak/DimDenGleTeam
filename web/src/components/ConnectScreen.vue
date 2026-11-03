<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '@/api/client'
import { useSettingsStore } from '@/stores/settings'
import TopBar from '@/components/TopBar.vue'
import AboutDialog from '@/components/dialogs/AboutDialog.vue'

const settings = useSettingsStore()
const draft = ref(settings.baseUrl)
const localError = ref('')
const saving = ref(false)
const aboutOpen = ref(false)

async function save() {
  localError.value = ''
  saving.value = true
  try {
    await settings.useServer(draft.value)
  } catch (cause) {
    localError.value = errorMessage(cause)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="app-shell">
    <TopBar :show-actions="false" @about="aboutOpen = true" />
    <main class="gate">
      <form class="card" @submit.prevent="save">
        <h2>Сервер</h2>
        <p v-if="settings.phase === 'checking'" class="muted">Проверка сервера…</p>
        <template v-else>
          <p v-if="settings.error" class="error">{{ settings.error }}</p>
          <p class="muted">
            Приложение не хранит свою базу: данные только на сервере.
            Адрес: {{ settings.baseUrl }}
          </p>
          <p class="muted">Проверьте, что общий сервер запущен, либо укажите его адрес.</p>
        </template>
        <label for="server-url">Адрес сервера</label>
        <input
          id="server-url"
          v-model="draft"
          class="field"
          type="text"
          autocomplete="url"
          spellcheck="false"
        />
        <p v-if="localError" class="error">{{ localError }}</p>
        <div class="form-actions">
          <button type="submit" class="btn" :disabled="saving">
            Подключиться
          </button>
        </div>
      </form>
    </main>
    <AboutDialog v-if="aboutOpen" @close="aboutOpen = false" />
  </div>
</template>

<style scoped lang="scss">
.gate {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.card {
  width: min(520px, 100%);
  padding: 20px;
  border-radius: 12px;
  background: var(--panel-bg);
}

h2 {
  margin: 0 0 10px;
  font-size: 18px;
}

.muted {
  margin: 0 0 8px;
  color: var(--muted);
  line-height: 1.45;
}

.error {
  margin: 0 0 8px;
  color: #d35b4a;
  white-space: pre-line;
  line-height: 1.45;
}

label {
  display: block;
  margin: 12px 0 6px;
}
</style>
