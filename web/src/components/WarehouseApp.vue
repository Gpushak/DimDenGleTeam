<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { api, ApiError, errorMessage } from '@/api/client'
import type { BoxDto, ItemDto } from '@/api/types'
import { useNoticesStore } from '@/stores/notices'
import { useWarehouseStore } from '@/stores/warehouse'
import TopBar from '@/components/TopBar.vue'
import BoxTree from '@/components/BoxTree.vue'
import ItemsTable from '@/components/ItemsTable.vue'
import AboutDialog from '@/components/dialogs/AboutDialog.vue'
import ServerDialog from '@/components/dialogs/ServerDialog.vue'
import BoxDialog from '@/components/dialogs/BoxDialog.vue'
import ItemDialog from '@/components/dialogs/ItemDialog.vue'
import ItemTypeDialog from '@/components/dialogs/ItemTypeDialog.vue'
import QrDialog from '@/components/dialogs/QrDialog.vue'

const warehouse = useWarehouseStore()
const notices = useNoticesStore()

const aboutOpen = ref(false)
const serverOpen = ref(false)
const itemTypeOpen = ref(false)
const qrItemId = ref<number | null>(null)
const boxDialog = ref<{ mode: 'add' | 'edit'; box: BoxDto | null; parentId: number | null } | null>(null)
const itemDialog = ref<{ mode: 'add' | 'edit'; item: ItemDto | null; defaultBoxId: number | null } | null>(null)

onMounted(() => {
  warehouse.startScale()
  void refresh()
})

onUnmounted(() => warehouse.stopScale())

async function refresh() {
  try {
    await warehouse.refreshAll()
  } catch (cause) {
    await notices.alert('Сервер', errorMessage(cause))
  }
}

function addBox() {
  const parentId = warehouse.selectedId != null && warehouse.selectedId > 0
    ? warehouse.selectedId
    : null
  boxDialog.value = { mode: 'add', box: null, parentId }
}

async function editBox() {
  if (warehouse.selectedId == null || warehouse.selectedId <= 0) {
    await notices.alert('Информация', 'Выберите контейнер для редактирования')
    return
  }
  try {
    const box = await api.getBox(warehouse.selectedId)
    boxDialog.value = { mode: 'edit', box, parentId: null }
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) return
    await notices.alert('Ошибка', errorMessage(cause))
  }
}

async function deleteBox() {
  if (warehouse.selectedId == null || warehouse.selectedId <= 0) {
    await notices.alert('Информация', 'Выберите контейнер для удаления')
    return
  }
  try {
    const box = await api.getBox(warehouse.selectedId)
    const confirmed = await notices.confirm(
      'Подтверждение',
      `Удалить контейнер "${box.name}"?\nТовары останутся без расположения.`,
    )
    if (!confirmed) return
    const result = await api.deleteBox(box.id)
    warehouse.selectedId = null
    await refresh()
    const unboxed = Number(result.unboxed ?? 0)
    if (unboxed > 0) {
      await notices.alert('Информация', `${unboxed} товар(ов) остались без расположения`)
    }
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) return
    await notices.alert('Ошибка', errorMessage(cause))
  }
}

function addItem() {
  const defaultBoxId = warehouse.selectedId != null && warehouse.selectedId > 0
    ? warehouse.selectedId
    : null
  itemDialog.value = { mode: 'add', item: null, defaultBoxId }
}

async function editItem() {
  if (warehouse.selectedItemId == null) {
    await notices.alert('Информация', 'Выберите товар для редактирования')
    return
  }
  try {
    const item = await api.getItem(warehouse.selectedItemId)
    itemDialog.value = { mode: 'edit', item, defaultBoxId: null }
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) return
    await notices.alert('Ошибка', errorMessage(cause))
  }
}

async function deleteItem() {
  if (warehouse.selectedItemId == null) {
    await notices.alert('Информация', 'Выберите товар для удаления')
    return
  }
  try {
    const item = await api.getItem(warehouse.selectedItemId)
    const typeName = item.item_type_name || '—'
    const confirmed = await notices.confirm('Подтверждение', `Удалить товар "${typeName}"?`)
    if (!confirmed) return
    await api.deleteItem(item.id)
    await refresh()
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) return
    await notices.alert('Ошибка', errorMessage(cause))
  }
}

async function showQr() {
  if (warehouse.selectedItemId == null) {
    await notices.alert('Информация', 'Выберите товар, чтобы сформировать QR-этикетку')
    return
  }
  try {
    const item = await api.getItem(warehouse.selectedItemId)
    qrItemId.value = item.id
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) return
    await notices.alert('QR', errorMessage(cause))
  }
}

async function onSaved(kind: 'box' | 'item' | 'type') {
  if (kind === 'box') boxDialog.value = null
  if (kind === 'item') itemDialog.value = null
  if (kind === 'type') itemTypeOpen.value = false
  await refresh()
}
</script>

<template>
  <div class="app-shell">
    <TopBar @refresh="refresh" @server="serverOpen = true" @about="aboutOpen = true" />
    <div class="body">
      <div class="search">
        <label for="search">Поиск:</label>
        <input id="search" v-model="warehouse.search" class="field search-field" type="search" />
      </div>
      <div class="workspace">
        <section class="tree-pane">
          <h2>Структура склада</h2>
          <div class="toolbar">
            <button type="button" class="btn" @click="addBox">+ Контейнер</button>
            <button type="button" class="btn" @click="editBox">✎ Изменить</button>
            <button type="button" class="btn" @click="deleteBox">✕ Удалить</button>
          </div>
          <div class="fill">
            <BoxTree />
          </div>
        </section>
        <div class="vsep" />
        <section class="items-pane">
          <h2>{{ warehouse.header }}</h2>
          <div class="toolbar">
            <button type="button" class="btn" @click="itemTypeOpen = true">+ Тип товара</button>
            <button type="button" class="btn" @click="addItem">+ Товар</button>
            <button type="button" class="btn" @click="editItem">✎ Изменить</button>
            <button type="button" class="btn" @click="deleteItem">✕ Удалить</button>
            <button type="button" class="btn" @click="showQr">QR</button>
          </div>
          <div class="fill">
            <ItemsTable />
          </div>
        </section>
      </div>
    </div>
    <div class="sep" />
    <footer class="status">{{ warehouse.statusText }}</footer>

    <AboutDialog v-if="aboutOpen" @close="aboutOpen = false" />
    <ServerDialog v-if="serverOpen" @close="serverOpen = false" />
    <ItemTypeDialog v-if="itemTypeOpen" @close="itemTypeOpen = false" @saved="onSaved('type')" />
    <BoxDialog
      v-if="boxDialog"
      :mode="boxDialog.mode"
      :box="boxDialog.box"
      :parent-id="boxDialog.parentId"
      @close="boxDialog = null"
      @saved="onSaved('box')"
    />
    <ItemDialog
      v-if="itemDialog"
      :mode="itemDialog.mode"
      :item="itemDialog.item"
      :default-box-id="itemDialog.defaultBoxId"
      @close="itemDialog = null"
      @saved="onSaved('item')"
    />
    <QrDialog v-if="qrItemId != null" :item-id="qrItemId" @close="qrItemId = null" />
  </div>
</template>

<style scoped lang="scss">
.body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 10px 14px 6px;
}

.search {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.search-field {
  width: 300px;
}

.workspace {
  flex: 1;
  min-height: 0;
  display: flex;
}

.tree-pane {
  width: 330px;
  flex: none;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.items-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

h2 {
  margin: 2px 0 6px;
  font-size: 14px;
  font-weight: 700;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.fill {
  flex: 1;
  min-height: 0;
}

.vsep {
  width: 1px;
  margin: 0 10px 0 8px;
  background: var(--border);
}

.status {
  height: 32px;
  flex: none;
  display: flex;
  align-items: center;
  padding: 0 14px;
  background: var(--panel-bg);
  color: var(--muted);
}
</style>
