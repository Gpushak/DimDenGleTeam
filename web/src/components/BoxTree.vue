<script setup lang="ts">
import { computed } from 'vue'
import { buildTree, toggleGlyph, visibleTreeRows, type TreeRow } from '@/lib/tree'
import { useWarehouseStore } from '@/stores/warehouse'

const warehouse = useWarehouseStore()

const rows = computed(() => visibleTreeRows(buildTree(warehouse.boxes), warehouse.expanded))

function isSelected(row: TreeRow): boolean {
  return warehouse.selectedId === row.selectId
}

function onToggle(row: TreeRow) {
  if (!row.hasChildren || row.selectId == null || row.selectId <= 0) return
  warehouse.toggleExpanded(row.selectId)
}
</script>

<template>
  <div class="tree">
    <div
      v-for="row in rows"
      :key="row.key"
      class="node"
      :style="{ paddingLeft: `${row.level * 18}px` }"
    >
      <button
        v-if="row.selectId != null && row.selectId > 0"
        type="button"
        class="toggle"
        :aria-label="row.hasChildren ? 'Свернуть или развернуть' : 'Нет вложенных контейнеров'"
        @click="onToggle(row)"
      >
        {{ toggleGlyph(row, warehouse.expanded) }}
      </button>
      <button
        type="button"
        class="label"
        :class="{ selected: isSelected(row) }"
        @click="warehouse.selectNode(row.selectId)"
      >
        {{ row.label }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.tree {
  height: 100%;
  overflow: auto;
  padding-right: 4px;
}

.node {
  display: flex;
  align-items: center;
  gap: 2px;
  margin: 1px 0;
}

.toggle,
.label {
  height: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
}

.toggle {
  width: 24px;
  flex: none;
  color: var(--muted);
}

.label {
  flex: 1;
  min-width: 0;
  padding: 0 8px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toggle:hover,
.label:hover {
  background: var(--hover);
}

.label.selected {
  background: var(--selected);
  color: var(--selected-text);
}

.label.selected:hover {
  background: var(--selected);
}
</style>
