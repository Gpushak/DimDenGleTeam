<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { api, errorMessage } from '@/api/client'
import type { ItemDto } from '@/api/types'
import { createBoxIndex, NO_LOCATION } from '@/lib/boxIndex'
import { itemTypeLabel } from '@/lib/format'
import { labelFor, uniqueOptions, type LabeledOption } from '@/lib/options'
import { useNoticesStore } from '@/stores/notices'
import AppDialog from '@/components/AppDialog.vue'

const props = defineProps<{
  mode: 'add' | 'edit'
  item: ItemDto | null
  defaultBoxId: number | null
}>()

const emit = defineEmits<{ close: []; saved: [] }>()
const notices = useNoticesStore()

const ready = ref(false)
const saving = ref(false)
const typeLabel = ref('')
const boxLabel = ref(NO_LOCATION)
const quantity = ref(props.item ? String(props.item.quantity) : '1')
const typeOptions = ref<LabeledOption[]>([])
const boxOptions = ref<LabeledOption[]>([])
const typeInput = ref<HTMLSelectElement | null>(null)

watch(ready, async (value) => {
  if (!value) return
  await nextTick()
  typeInput.value?.focus()
})

onMounted(async () => {
  try {
    const [types, boxes] = await Promise.all([api.getItemTypes(), api.getBoxes()])
    const index = createBoxIndex(boxes)
    typeOptions.value = uniqueOptions(
      types.map((type) => ({ id: type.id, label: itemTypeLabel(type) })),
    )
    boxOptions.value = uniqueOptions([
      { id: null, label: NO_LOCATION },
      ...index.all().map((box) => ({ id: box.id, label: index.fullPath(box.id) })),
    ])

    if (props.mode === 'edit' && props.item) {
      typeLabel.value = labelFor(typeOptions.value, props.item.item_type_id, '')
      boxLabel.value = labelFor(boxOptions.value, props.item.box_id, NO_LOCATION)
    } else {
      typeLabel.value = typeOptions.value[0]?.label ?? ''
      boxLabel.value = labelFor(boxOptions.value, props.defaultBoxId, NO_LOCATION)
    }
    ready.value = true
  } catch (cause) {
    await notices.alert('Ошибка', errorMessage(cause))
    emit('close')
  }
})

async function save() {
  const type = typeOptions.value.find((option) => option.label === typeLabel.value)
  if (type?.id == null) {
    await notices.alert('Ошибка', 'Выберите тип товара')
    return
  }
  const raw = quantity.value.trim()
  const parsed = Number(raw)
  if (!/^\d+$/.test(raw) || parsed < 1) {
    const detail = /^\d+$/.test(raw) ? 'Количество должно быть >= 1' : 'введите целое число'
    await notices.alert('Ошибка', `Неверное количество: ${detail}`)
    return
  }
  const box = boxOptions.value.find((option) => option.label === boxLabel.value)
  const boxId = box ? box.id : null
  saving.value = true
  try {
    if (props.mode === 'add') {
      await api.createItem({ item_type_id: type.id, box_id: boxId, quantity: parsed })
    } else if (props.item) {
      await api.updateItem(props.item.id, {
        item_type_id: type.id,
        box_id: boxId,
        quantity: parsed,
      })
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
  <AppDialog :title="mode === 'add' ? 'Новый товар' : 'Редактировать товар'" @close="emit('close')">
    <p v-if="!ready">Загрузка…</p>
    <form v-else class="form-grid" @submit.prevent="save">
      <label for="item-type">Тип товара:</label>
      <select id="item-type" ref="typeInput" v-model="typeLabel" class="field">
        <option v-for="option in typeOptions" :key="option.label" :value="option.label">
          {{ option.label }}
        </option>
      </select>

      <label for="item-box">Расположение:</label>
      <select id="item-box" v-model="boxLabel" class="field">
        <option v-for="option in boxOptions" :key="option.label" :value="option.label">
          {{ option.label }}
        </option>
      </select>

      <label for="item-qty">Количество:</label>
      <input id="item-qty" v-model="quantity" class="field" inputmode="numeric" />

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
