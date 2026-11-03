import type { BoxDto } from '@/api/types'

export const NO_LOCATION = 'Без расположения'

export interface BoxIndex {
  get(id: number | null | undefined): BoxDto | undefined
  all(): BoxDto[]
  fullPath(id: number | null | undefined): string
  descendantIds(id: number): Set<number>
}

export function createBoxIndex(list: BoxDto[]): BoxIndex {
  const boxes = new Map(list.map((box) => [box.id, box]))
  const paths = new Map<number, string>()

  function childrenOf(id: number | null): BoxDto[] {
    return [...boxes.values()].filter((box) => box.parent_id === id)
  }

  return {
    get(id) {
      if (id == null) return undefined
      return boxes.get(id)
    },
    all() {
      return [...boxes.values()]
    },
    fullPath(id) {
      if (id == null) return NO_LOCATION
      const cached = paths.get(id)
      if (cached != null) return cached

      const parts: string[] = []
      const seen = new Set<number>()
      let current = boxes.get(id)
      while (current && !seen.has(current.id)) {
        seen.add(current.id)
        parts.push(current.name)
        current = current.parent_id != null ? boxes.get(current.parent_id) : undefined
      }
      const path = parts.length ? parts.reverse().join(' / ') : NO_LOCATION
      paths.set(id, path)
      return path
    },
    descendantIds(id) {
      const result = new Set<number>()
      const queue = childrenOf(id)
      while (queue.length) {
        const child = queue.pop()
        if (!child || result.has(child.id)) continue
        result.add(child.id)
        queue.push(...childrenOf(child.id))
      }
      return result
    },
  }
}
