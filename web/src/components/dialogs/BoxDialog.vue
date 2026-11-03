<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { api, errorMessage } from '@/api/client'
import type { BoxDto } from '@/api/types'
import { createBoxIndex } from '@/lib/boxIndex'
import { labelFor, uniqueOptions, type LabeledOption } from '@/lib/options'
import { useNoticesStore } from '@/stores/notices'
import AppDialog from '@/components/AppDialog.vue'

const props = defineProps<{
  mode: 'add' | 'edit'
  box: BoxDto | null
  parentId: number | null
}>()

const emit = defineEmits<{ close: []; saved: [] }>()
const notices = useNoticesStore()

const ROOT = '— Корень —'
const ready = ref(false)
const saving = ref(false)
const name = ref(props.box?.name ?? '')
const parentLabel = ref(ROOT)
const typeLabel = ref('')
const parentOptions = ref<LabeledOption[]>([])
const typeOptions = ref<LabeledOption[]>([])
const nameInput = ref<HTMLInputElement | null>(null)

watch(ready, async (value) => {
  if (!value) return
  await nextTick()
  nameInput.value?.focus()
})

onMounted(async () => {
  try {
    const [boxes, types] = await Promise.all([api.getBoxes(), api.getBoxTypes()])
    const index = createBoxIndex(boxes)
    let candidates = index.all()
    if (props.mode === 'edit' && props.box) {
      const forbidden = index.descendantIds(props.box.id)
      forbidden.add(props.box.id)
      candidates = candidates.filter((box) => !forbidden.has(box.id))
    }
    parentOptions.value = uniqueOptions([
      { id: null, label: ROOT },
      ...candidates.map((box) => ({ id: box.id, label: index.fullPath(box.id) })),
    ])
    typeOptions.value = uniqueOptions(types.map((type) => ({ id: type.id, label: type.name })))

    if (props.mode === 'edit' && props.box) {
      parentLabel.value = labelFor(parentOptions.value, props.box.parent_id, ROOT)
      const typeId = props.box.box_type_id
      typeLabel.value = labelFor(typeOptions.value, typeId, typeOptions.value[0]?.label ?? '')
    } else {
      parentLabel.value = labelFor(parentOptions.value, props.parentId, ROOT)
      typeLabel.value = typeOptions.value[0]?.label ?? ''
    }
    ready.value = true
  } catch (cause) {
    await notices.alert('Ошибка', errorMessage(cause))
    emit('close')
  }
})

async function save() {
  const trimmed = name.value.trim()
  if (!trimmed) {
    await notices.alert('Ошибка', 'Введите название')
    return
  }
  const type = typeOptions.value.find((option) => option.label === typeLabel.value)
  if (type?.id == null) {
    await notices.alert('Ошибка', 'Выберите тип контейнера')
    return
  }
  const parent = parentOptions.value.find((option) => option.label === parentLabel.value)
  const parentId = parent ? parent.id : null
  saving.value = true
  try {
    if (props.mode === 'add') {
      await api.createBox({ name: trimmed, box_type_id: type.id, parent_id: parentId })
    } else if (props.box) {
      await api.updateBox(props.box.id, { name: trimmed, box_type_id: type.id })
      await api.moveBox(props.box.id, parentId)
    }
    emit('saved')
  } catch (cause) {
    await notices.alert('Ошибка', errorMessage(cause))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog :title="mode === 'add' ? 'Новый контейнер' : 'Редактировать контейнер'" @close="emit('close')">
    <p v-if="!ready">Загрузка…</p>
    <form v-else class="form-grid" @submit.prevent="save">
      <label for="box-parent">Родительский контейнер:</label>
      <select id="box-parent" v-model="parentLabel" class="field">
        <option v-for="option in parentOptions" :key="option.label" :value="option.label">
          {{ option.label }}
        </option>
      </select>

      <label for="box-name">Название:</label>
      <input id="box-name" ref="nameInput" v-model="name" class="field" />

      <label for="box-type">Тип контейнера:</label>
      <select id="box-type" v-model="typeLabel" class="field">
        <option v-for="option in typeOptions" :key="option.label" :value="option.label">
          {{ option.label }}
        </option>
      </select>

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
</style>
