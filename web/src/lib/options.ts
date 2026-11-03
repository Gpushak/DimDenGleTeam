export interface LabeledOption {
  id: number | null
  label: string
}

/** Одинаковые подписи различаются идентификатором, чтобы выбор оставался однозначным. */
export function uniqueOptions(entries: LabeledOption[]): LabeledOption[] {
  const seen = new Map<string, number>()
  return entries.map((entry) => {
    const count = seen.get(entry.label) ?? 0
    seen.set(entry.label, count + 1)
    if (count === 0) return entry
    return { id: entry.id, label: `${entry.label} (#${entry.id})` }
  })
}

export function labelFor(options: LabeledOption[], id: number | null, fallback: string): string {
  return options.find((option) => option.id === id)?.label ?? fallback
}
