export interface BoxTypeDto {
  id: number
  name: string
}

export interface BoxDto {
  id: number
  name: string
  box_type_id: number
  box_type_name: string
  parent_id: number | null
}

export interface ItemTypeDto {
  id: number
  name: string
  weight_g: number | null
}

export interface ItemDto {
  id: number
  item_type_id: number
  item_type_name: string
  weight_g: number | null
  box_id: number | null
  box_name: string | null
  quantity: number
  total_weight_g: number | null
}

export interface HealthDto {
  status: string
  database: string
  database_path: string
  schema_version: number
  schema_version_expected: number
}

export interface ScaleDto {
  weight_g: number | null
  updated_at: string | null
  source: string
  stale: boolean
}

export interface DeleteBoxResult {
  message?: string
  unboxed?: number
}

export interface ItemQuery {
  box_id?: number
  include_children?: boolean
  unboxed?: boolean
}
