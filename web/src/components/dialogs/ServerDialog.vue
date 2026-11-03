<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '@/api/client'
import { useNoticesStore } from '@/stores/notices'
import { useSettingsStore } from '@/stores/settings'
import { useWarehouseStore } from '@/stores/warehouse'
import AppDialog from '@/components/AppDialog.vue'

const emit = defineEmits<{ close: [] }>()
const settings = useSettingsStore()
const warehouse = useWarehouseStore()
const notices = useNoticesStore()

const url = ref(settings.baseUrl)
const saving = ref(false)

async function save() {
  saving.value = true
  try {
    const health = await settings.useServer(url.value)
    await warehouse.refreshAll()
    emit('close')
    await notices.alert(
      'Сервер',
      `Подключено к ${settings.baseUrl}\nБаза сервера: ${health.database_path || '—'}`,
    )
  } catch (cause) {
    await notices.alert('Сервер', errorMessage(cause))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog title="Сервер" @close="emit('close')">
    <form @submit.prevent="save">
      <input v-model="url" class="field" type="text" autocomplete="url" spellcheck="false" />
      <div class="form-actions">
        <button type="submit" class="btn" :disabled="saving">Сохранить</button>
        <button type="button" class="btn ghost" @click="emit('close')">Отмена</button>
      </div>
    </form>
  </AppDialog>
</template>
