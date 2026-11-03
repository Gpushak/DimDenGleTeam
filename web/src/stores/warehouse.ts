import { computed, nextTick, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api, errorMessage } from '@/api/client'
import type { ItemDto } from '@/api/types'
import { createBoxIndex } from '@/lib/boxIndex'
import { formatWeight, totalWeightG } from '@/lib/format'
import { compareNatural, weightLabelGrams } from '@/lib/sort'
import { useNoticesStore } from '@/stores/notices'

export type SortColumn = 'type' | 'quantity' | 'weight' | 'location'

export interface ItemRow {
  id: number
  typeName: string
  quantity: number
  weightLabel: string
  location: string
  weightG: number
}

export const useWarehouseStore = defineStore('warehouse', () => {
  const boxes = ref<Awaited<ReturnType<typeof api.getBoxes>>>([])
  const selectedId = ref<number | null>(null)
  const expanded = ref<Record<number, boolean>>({})
  const search = ref('')
  const header = ref('Все товары')
  const rows = ref<ItemRow[]>([])
  const selectedItemId = ref<number | null>(null)
  const sortColumn = ref<SortColumn | null>(null)
  const sortReverse = ref(false)
  const scaleWeight = ref<number | null>(null)

  let silenceSearch = false
  let searchTimer = 0
  let scaleTimer = 0
  let request = 0

  const sortedRows = computed(() => {
    const list = [...rows.value]
    const column = sortColumn.value
    if (!column) return list
    list.sort((left, right) => {
      const diff = compareRows(left, right, column)
      return sortReverse.value ? -diff : diff
    })
    return list
  })

  const statusText = computed(() => {
    const quantity = rows.value.reduce((sum, row) => sum + row.quantity, 0)
    const weight = rows.value.reduce((sum, row) => sum + row.weightG, 0)
    let text =
      `Позиций: ${rows.value.length} | Общее кол-во: ${quantity} | Общий вес: ${formatWeight(weight)}`
    if (scaleWeight.value != null) {
      text += ` | Весы: ${scaleWeight.value.toFixed(1)} г`
    }
    return text
  })

  watch(search, () => {
    if (silenceSearch) return
    window.clearTimeout(searchTimer)
    searchTimer = window.setTimeout(() => {
      void loadItems().catch((cause: unknown) => {
        void useNoticesStore().alert('Сервер', errorMessage(cause))
      })
    }, 200)
  })

  function sortBy(column: SortColumn) {
    if (sortColumn.value === column) sortReverse.value = !sortReverse.value
    else {
      sortColumn.value = column
      sortReverse.value = false
    }
  }

  function toggleExpanded(boxId: number) {
    expanded.value[boxId] = expanded.value[boxId] === false
  }

  function reveal(boxId: number) {
    const index = createBoxIndex(boxes.value)
    const guard = new Set<number>()
    let current = index.get(boxId)
    while (current && !guard.has(current.id)) {
      guard.add(current.id)
      if (current.parent_id != null) expanded.value[current.parent_id] = true
      current = current.parent_id != null ? index.get(current.parent_id) : undefined
    }
  }

  async function loadTree() {
    const loaded = await api.getBoxes()
    boxes.value = loaded
    const known = new Set(loaded.map((box) => box.id))
    if (selectedId.value != null && selectedId.value > 0 && !known.has(selectedId.value)) {
      selectedId.value = null
    }
    if (selectedId.value != null && selectedId.value > 0) reveal(selectedId.value)
  }

  async function loadItems() {
    const token = ++request
    try {
      const loadedBoxes = await api.getBoxes()
      if (token !== request) return
      boxes.value = loadedBoxes
      const index = createBoxIndex(loadedBoxes)
      const query = search.value.trim()
      let items: ItemDto[]
      let nextHeader: string

      if (query) {
        nextHeader = `Результаты поиска: ${query}`
        const needle = query.toLowerCase()
        items = (await api.getItems()).filter((item) => {
          const typeName = (item.item_type_name || '').toLowerCase()
          const place = index.fullPath(item.box_id).toLowerCase()
          return typeName.includes(needle) || place.includes(needle)
        })
      } else if (selectedId.value == null) {
        nextHeader = 'Все товары'
        items = await api.getItems()
      } else if (selectedId.value === -1) {
        nextHeader = 'Товары без расположения'
        items = await api.getItems({ unboxed: true })
      } else {
        const box = index.get(selectedId.value)
        if (!box) {
          if (token !== request) return
          header.value = 'Контейнер не найден'
          rows.value = []
          selectedItemId.value = null
          return
        }
        nextHeader = `${box.name} — ${index.fullPath(box.id)}`
        items = await api.getItems({ box_id: box.id, include_children: false })
      }

      if (token !== request) return
      rows.value = items.map((item) => {
        const weightG = totalWeightG(item)
        return {
          id: item.id,
          typeName: item.item_type_name || '—',
          quantity: item.quantity,
          weightLabel: formatWeight(weightG),
          location: index.fullPath(item.box_id),
          weightG,
        }
      })
      header.value = nextHeader
      if (
        selectedItemId.value != null &&
        !rows.value.some((row) => row.id === selectedItemId.value)
      ) {
        selectedItemId.value = null
      }
      if (selectedId.value != null && selectedId.value > 0) reveal(selectedId.value)
    } catch (cause) {
      if (token !== request) return
      throw cause
    }
  }

  function selectNode(id: number | null) {
    selectedId.value = id
    if (id != null && id > 0) reveal(id)
    void loadItems().catch((cause: unknown) => {
      void useNoticesStore().alert('Сервер', errorMessage(cause))
    })
  }

  async function refreshAll() {
    window.clearTimeout(searchTimer)
    silenceSearch = true
    search.value = ''
    await nextTick()
    silenceSearch = false
    await loadTree()
    await loadItems()
  }

  function startScale() {
    stopScale()
    const tick = async () => {
      try {
        const state = await api.getScale()
        if (state.weight_g != null) scaleWeight.value = Number(state.weight_g)
      } catch {
        // Весы недоступны — строка статуса остаётся с последним показанием.
      }
    }
    void tick()
    scaleTimer = window.setInterval(() => {
      void tick()
    }, 1000)
  }

  function stopScale() {
    window.clearInterval(scaleTimer)
    scaleTimer = 0
  }

  return {
    boxes,
    selectedId,
    expanded,
    search,
    header,
    rows,
    sortedRows,
    selectedItemId,
    sortColumn,
    sortReverse,
    scaleWeight,
    statusText,
    sortBy,
    toggleExpanded,
    selectNode,
    refreshAll,
    loadItems,
    startScale,
    stopScale,
  }
})

function compareRows(left: ItemRow, right: ItemRow, column: SortColumn): number {
  if (column === 'quantity') return left.quantity - right.quantity
  if (column === 'weight') {
    return weightLabelGrams(left.weightLabel) - weightLabelGrams(right.weightLabel)
  }
  if (column === 'type') return compareNatural(left.typeName, right.typeName)
  return compareNatural(left.location, right.location)
}
