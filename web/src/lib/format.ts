import type { ItemDto, ItemTypeDto } from '@/api/types'

/** Граммы в вид «450 г» / «1.25 кг». */
export function formatWeight(grams: number): string {
  if (grams >= 1000) return `${(grams / 1000).toFixed(2)} кг`
  return `${grams} г`
}

export function totalWeightG(item: ItemDto): number {
  if (item.total_weight_g != null) return item.total_weight_g
  if (item.weight_g) return item.weight_g * item.quantity
  return 0
}

export function itemTypeLabel(type: ItemTypeDto): string {
  return type.weight_g ? `${type.name} (${type.weight_g}г)` : type.name
}

export function itemQrPayload(itemId: number): string {
  return `qwentory:item:${itemId}`
}
