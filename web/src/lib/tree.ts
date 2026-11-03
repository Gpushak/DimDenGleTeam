import type { BoxDto } from '@/api/types'
import { compareNatural } from '@/lib/sort'

export interface TreeRow {
  key: string
  selectId: number | null
  label: string
  level: number
  hasChildren: boolean
}

/** Плоский обход: специальные узлы, затем родитель раньше потомков. */
export function buildTree(boxes: BoxDto[]): TreeRow[] {
  const rows: TreeRow[] = [
    { key: 'all', selectId: null, label: 'Все товары', level: 0, hasChildren: false },
    { key: 'unboxed', selectId: -1, label: 'Без расположения', level: 0, hasChildren: false },
  ]

  const byId = new Map(boxes.map((box) => [box.id, box]))
  const children = new Map<number | null, BoxDto[]>()
  for (const box of boxes) {
    let parent: number | null = box.parent_id
    if (parent != null && !byId.has(parent)) parent = null
    const list = children.get(parent) ?? []
    list.push(box)
    children.set(parent, list)
  }
  for (const list of children.values()) {
    list.sort((a, b) => compareNatural(a.name, b.name))
  }

  const visited = new Set<number>()
  const walk = (parentId: number | null, level: number) => {
    for (const box of children.get(parentId) ?? []) {
      if (visited.has(box.id)) continue
      visited.add(box.id)
      const hasChildren = (children.get(box.id) ?? []).length > 0
      rows.push({
        key: `box:${box.id}`,
        selectId: box.id,
        label: box.name,
        level,
        hasChildren,
      })
      if (hasChildren) walk(box.id, level + 1)
    }
  }
  walk(null, 0)

  const leftovers = boxes
    .filter((box) => !visited.has(box.id))
    .sort((a, b) => compareNatural(a.name, b.name))
  for (const box of leftovers) {
    rows.push({
      key: `box:${box.id}`,
      selectId: box.id,
      label: box.name,
      level: 0,
      hasChildren: (children.get(box.id) ?? []).length > 0,
    })
  }
  return rows
}

export function visibleTreeRows(
  rows: TreeRow[],
  expanded: Readonly<Record<number, boolean>>,
): TreeRow[] {
  return rows.filter((_, index) => isVisible(rows, index, expanded))
}

export function toggleGlyph(row: TreeRow, expanded: Readonly<Record<number, boolean>>): string {
  if (!row.hasChildren || row.selectId == null || row.selectId <= 0) return '•'
  return expanded[row.selectId] === false ? '▶' : '▼'
}

function findParentIndex(rows: TreeRow[], index: number): number | null {
  const level = rows[index]?.level ?? 0
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    const candidate = rows[cursor]
    if (!candidate) continue
    if (candidate.level === level - 1) return cursor
    if (candidate.level < level - 1) return null
  }
  return null
}

function isVisible(
  rows: TreeRow[],
  index: number,
  expanded: Readonly<Record<number, boolean>>,
): boolean {
  let current = index
  while ((rows[current]?.level ?? 0) > 0) {
    const parentIndex = findParentIndex(rows, current)
    if (parentIndex == null) break
    const parent = rows[parentIndex]
    if (!parent) break
    const parentId = parent.selectId
    if (parent.hasChildren && parentId != null && parentId > 0 && expanded[parentId] === false) {
      return false
    }
    current = parentIndex
  }
  return true
}
