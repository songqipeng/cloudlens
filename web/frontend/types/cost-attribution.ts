export type AttributionCompareType = "mom" | "yoy" | "custom"

export type AttributionCategoryKey =
  | "resource_count"
  | "discount"
  | "price"
  | "product_mix"
  | "other"

export interface AttributionDetail {
  product_code: string
  product_name: string
  status: "existing" | "new" | "removed"
  current_count: number
  compare_count: number
  current_usage: number
  compare_usage: number
  current_discount_rate: number
  compare_discount_rate: number
  current_pretax: number
  compare_pretax: number
  cost_impact: number
  description: string
}

export interface AttributionCategory {
  category: AttributionCategoryKey
  label: string
  impact: number
  impact_pct: number
  details: AttributionDetail[]
}

export interface AttributionRecommendation {
  priority: "high" | "medium" | "low"
  category: string
  title: string
  description: string
  estimated_savings: number
  effort: "low" | "medium" | "high"
  action: string
}

export interface AttributionProduct {
  product_code: string
  product_name: string
  status: "existing" | "new" | "removed"
  current_pretax: number
  compare_pretax: number
  delta: number
  current_count: number
  compare_count: number
}

export interface CostAttributionReport {
  current_cycle: string
  compare_cycle: string
  compare_type: AttributionCompareType
  current_total: number
  compare_total: number
  delta: number
  delta_pct: number
  attributions: AttributionCategory[]
  products: AttributionProduct[]
  recommendations: AttributionRecommendation[]
  data_source: string
  message?: string
  available_cycles?: string[]
}
