/** Ключ естественной сортировки: «Ячейка 2» < «Ячейка 10». */
export function compareNatural(a: string, b: string): number {
  const left = naturalKey(a)
  const right = naturalKey(b)
  const length = Math.max(left.length, right.length)
  for (let index = 0; index < length; index += 1) {
    const leftPart = left[index]
    const rightPart = right[index]
    if (leftPart === undefined) return -1
    if (rightPart === undefined) return 1
    if (typeof leftPart === 'number' && typeof rightPart === 'number') {
      if (leftPart !== rightPart) return leftPart - rightPart
      continue
    }
    const leftText = String(leftPart)
    const rightText = String(rightPart)
    if (leftText < rightText) return -1
    if (leftText > rightText) return 1
  }
  return 0
}

function naturalKey(text: string): Array<string | number> {
  return String(text)
    .split(/(\d+)/)
    .filter((part) => part !== '')
    .map((part) => (/^\d+$/.test(part) ? Number(part) : part.toLowerCase()))
}

/** Разбор подписи веса таблицы: «1.50 кг» → граммы, «300 г» → граммы. */
export function weightLabelGrams(label: string): number {
  const match = /^([\d.,]+)\s*(кг|г)?$/.exec(label.trim())
  if (!match) return 0
  const value = Number(match[1].replace(',', '.'))
  if (!Number.isFinite(value)) return 0
  return match[2] === 'кг' ? value * 1000 : value
}
