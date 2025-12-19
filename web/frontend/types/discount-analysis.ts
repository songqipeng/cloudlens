// Phase 1: 核心分析类型定义

export interface QuarterData {
  year: string
  quarter: string
  period: string
  total_original: number
  total_paid: number
  total_discount: number
  avg_discount_rate: number
  month_count: number
  rate_change?: number
}

export interface YearData {
  year: string
  month_count: number
  total_original: number
  total_paid: number
  total_discount: number
  avg_discount_rate: number
  yoy_consumption_growth?: number
  yoy_discount_growth?: number
  yoy_rate_change?: number
}

export interface ProductTrend {
  month: string
  official_price: number
  paid_amount: number
  discount_amount: number
  discount_rate: number
  record_count: number
  instance_count: number
}

export interface ProductStats {
  product_name: string
  trends: ProductTrend[]
  avg_discount_rate: number
  min_discount_rate: number
  max_discount_rate: number
  volatility: number
  trend_change_pct: number
  total_consumption: number
  total_discount: number
}

export interface RegionData {
  region: string
  region_name: string
  total_original: number
  total_paid: number
  total_discount: number
  avg_discount_rate: number
  instance_count: number
  product_count: number
  month_count: number
  consumption_percentage: number
}

export interface SubscriptionTypeData {
  type: string
  type_name: string
  total_original: number
  total_paid: number
  total_discount: number
  avg_discount_rate: number
  instance_count: number
  avg_instance_cost: number
  consumption_percentage: number
}

export interface SubscriptionTypeComparison {
  subscription_types: {
    [key: string]: SubscriptionTypeData
  }
  rate_difference: number
  monthly_trends: Array<{
    month: string
    subscription: {
      total_paid?: number
      discount_rate?: number
    }
    pay_as_you_go: {
      total_paid?: number
      discount_rate?: number
    }
  }>
}

export interface OptimizationSuggestion {
  instance_id: string
  product_name: string
  region: string
  region_name: string
  first_month: string
  last_month: string
  running_months: number
  total_cost: number
  avg_monthly_cost: number
  current_discount_rate: number
  estimated_subscription_rate: number
  annual_potential_savings: number
  suggestion: string
}

export interface Anomaly {
  month: string
  prev_month: string
  current_rate: number
  prev_rate: number
  change_pct: number
  anomaly_type: string
  severity: string
  description: string
}

// API Response types
export interface QuarterlyResponse {
  success: boolean
  data: {
    quarters: QuarterData[]
    total_quarters: number
  }
  account: string
  source: string
}

export interface YearlyResponse {
  success: boolean
  data: {
    years: YearData[]
    total_years: number
  }
  account: string
  source: string
}

export interface ProductTrendsResponse {
  success: boolean
  data: {
    products: ProductStats[]
    total_products: number
  }
  account: string
  source: string
}

export interface RegionsResponse {
  success: boolean
  data: {
    regions: RegionData[]
    total_regions: number
  }
  account: string
  source: string
}

export interface SubscriptionTypesResponse {
  success: boolean
  data: SubscriptionTypeComparison
  account: string
  source: string
}

export interface OptimizationSuggestionsResponse {
  success: boolean
  data: {
    suggestions: OptimizationSuggestion[]
    total_suggestions: number
    total_potential_savings: number
  }
  account: string
  source: string
}

export interface AnomaliesResponse {
  success: boolean
  data: {
    anomalies: Anomaly[]
    total_anomalies: number
    threshold: number
  }
  account: string
  source: string
}

// Phase 2: Advanced Analysis Types

export interface ProductRegionMatrix {
  discount_rate: number
  total_paid: number
}

export interface ProductRegionMatrixResponse {
  success: boolean
  data: {
    products: string[]
    regions: Array<{
      code: string
      name: string
    }>
    matrix: {
      [product: string]: {
        [region: string]: ProductRegionMatrix
      }
    }
  }
  account: string
  source: string
}

export interface MovingAverageData {
  month: string
  ma: number | null
  original?: number
}

export interface MovingAverageResponse {
  success: boolean
  data: {
    moving_averages: {
      [key: string]: MovingAverageData[]
    }
    original_data: Array<{
      month: string
      rate: number
    }>
  }
  account: string
  source: string
}

export interface CumulativeDiscountData {
  month: string
  monthly_discount: number
  cumulative_discount: number
}

export interface CumulativeDiscountResponse {
  success: boolean
  data: {
    cumulative_data: CumulativeDiscountData[]
    total_discount: number
  }
  account: string
  source: string
}

export interface InstanceLifecycleData {
  instance_id: string
  product_name: string
  region: string
  region_name: string
  subscription_type: string
  first_month: string
  last_month: string
  lifecycle_months: number
  total_cost: number
  total_discount: number
  avg_discount_rate: number
  monthly_trends: Array<{
    month: string
    monthly_cost: number
    discount_rate: number
  }>
}

export interface InstanceLifecycleResponse {
  success: boolean
  data: {
    instances: InstanceLifecycleData[]
    total_instances: number
  }
  account: string
  source: string
}


