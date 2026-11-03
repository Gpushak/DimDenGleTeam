<script setup lang="ts">
import { useWarehouseStore, type SortColumn } from '@/stores/warehouse'

const warehouse = useWarehouseStore()

const columns: { id: SortColumn; title: string; className: string }[] = [
  { id: 'type', title: 'Тип товара', className: 'type' },
  { id: 'quantity', title: 'Количество', className: 'quantity' },
  { id: 'weight', title: 'Вес', className: 'weight' },
  { id: 'location', title: 'Расположение', className: 'location' },
]

function heading(column: { id: SortColumn; title: string }): string {
  if (warehouse.sortColumn !== column.id) return column.title
  return `${column.title}${warehouse.sortReverse ? ' ▲' : ' ▼'}`
}
</script>

<template>
  <div class="scroll">
    <table>
      <colgroup>
        <col class="type" />
        <col class="quantity" />
        <col class="weight" />
        <col class="location" />
      </colgroup>
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.id">
            <button type="button" @click="warehouse.sortBy(column.id)">
              {{ heading(column) }}
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="warehouse.sortedRows.length === 0">
          <td class="empty" colspan="4">Нет позиций</td>
        </tr>
        <tr
          v-for="(row, index) in warehouse.sortedRows"
          :key="row.id"
          :class="{ alt: index % 2 === 1, selected: row.id === warehouse.selectedItemId }"
          @click="warehouse.selectedItemId = row.id"
        >
          <td>{{ row.typeName }}</td>
          <td class="num">{{ row.quantity }}</td>
          <td>{{ row.weightLabel }}</td>
          <td :title="row.location">{{ row.location }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.scroll {
  height: 100%;
  overflow: auto;
  background: var(--panel-bg);
  border-radius: 6px;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

col.type { width: 28%; }
col.quantity { width: 14%; }
col.weight { width: 16%; }
col.location { width: 42%; }

th,
td {
  padding: 0 8px;
  height: 28px;
  border-right: 1px solid var(--border);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

th:last-child,
td:last-child {
  border-right: 0;
}

th {
  position: sticky;
  top: 0;
  z-index: 1;
  height: 34px;
  background: var(--header-bg);
  font-weight: 700;
}

th button {
  width: 100%;
  height: 34px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text);
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

th button:hover {
  background: var(--hover);
}

tbody tr {
  background: var(--panel-bg);
  cursor: pointer;
}

tbody tr.alt {
  background: var(--row-alt);
}

tbody tr:hover {
  background: var(--hover);
}

tbody tr.selected,
tbody tr.selected:hover {
  background: var(--selected);
  color: var(--selected-text);
}

td.num {
  font-variant-numeric: tabular-nums;
}

td.empty {
  color: var(--muted);
  cursor: default;
  text-align: center;
}
</style>
