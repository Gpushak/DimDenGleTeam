<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { api, errorMessage } from '@/api/client'
import { useNoticesStore } from '@/stores/notices'
import AppDialog from '@/components/AppDialog.vue'

const emit = defineEmits<{ close: []; saved: [] }>()
const notices = useNoticesStore()

const name = ref('')
const weight = ref('')
const manual = ref(false)
const saving = ref(false)
const nameInput = ref<HTMLInputElement | null>(null)
let writing = false
let timer = 0

watch(weight, () => {
  if (writing) return
  manual.value = true
}, { flush: 'sync' })

function setWeight(value: string) {
  writing = true
  weight.value = value
  writing = false
}

async function readFreshWeight(): Promise<number | null> {
  try {
    const state = await api.getScale()
    if (state.stale || state.weight_g == null) return null
    return Math.round(Number(state.weight_g))
  } catch {
    return null
  }
}

async function tick() {
  if (manual.value) {
    window.clearInterval(timer)
    return
  }
  const grams = await readFreshWeight()
  if (manual.value) return
  if (grams) setWeight(String(grams))
}

async function fetchFromScale() {
  const grams = await readFreshWeight()
  if (grams == null) {
    await notices.alert('Весы', 'Нет свежего показания весов')
    return
  }
  setWeight(String(grams))
  manual.value = true
}

onMounted(async () => {
  await nextTick()
  nameInput.value?.focus()
  void tick()
  timer = window.setInterval(() => {
    void tick()
  }, 1500)
})

onUnmounted(() => window.clearInterval(timer))

async function save() {
  const trimmed = name.value.trim()
  if (!trimmed) {
    await notices.alert('Ошибка', 'Введите название')
    return
  }
  const weightText = weight.value.trim()
  let weightG: number | null = null
  if (weightText) {
    const value = Number(weightText)
    if (!Number.isFinite(value)) {
      await notices.alert('Ошибка', `Неверный вес: ${weightText}`)
      return
    }
    weightG = Math.round(value)
  }
  saving.value = true
  try {
    await api.createItemType({ name: trimmed, weight_g: weightG })
    emit('saved')
  } catch (cause) {
    await notices.alert('Ошибка', errorMessage(cause))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog title="Новый тип товара" @close="emit('close')">
    <form class="form-grid" @submit.prevent="save">
      <label for="type-name">Название типа:</label>
      <input id="type-name" ref="nameInput" v-model="name" class="field" />

      <label for="type-weight">Вес (г):</label>
      <div class="weight-line">
        <input id="type-weight" v-model="weight" class="field" inputmode="decimal" />
        <button type="button" class="btn" @click="fetchFromScale">С весов</button>
      </div>

      <div class="form-actions span">
        <button type="submit" class="btn" :disabled="saving">Сохранить</button>
        <button type="button" class="btn ghost" @click="emit('close')">Отмена</button>
      </div>
    </form>
  </AppDialog>
</template>

<style scoped lang="scss">
.span {
  grid-column: 1 / -1;
}

.weight-line {
  display: flex;
  gap: 8px;
}

.weight-line .field {
  flex: 1;
}

.weight-line .btn {
  width: 80px;
  padding: 0;
}
</style>
