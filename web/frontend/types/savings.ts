export type SavingsOpportunityType =
  | "framework_out_of_scope"
  | "framework_wrong_purchase"
  | "idle_low_util"
  | "weak_subscription"
  | string

export interface SavingsOpportunity {
  id?: string
  type: SavingsOpportunityType
  category?: string
  priority: "high" | "medium" | "low" | string
  title: string
  description: string
  annual_savings: number
  savings_potential?: number
  resource_count?: number
  action?: string
  recommendation?: string
  evidence?: Record<string, unknown>
  resources?: Array<Record<string, unknown>>
}

export interface FrameworkContractRules {
  framework_discount?: number
  products?: Array<{
    product_keys?: string[]
    subscription_required?: boolean
    allowed_months?: number[]
    regions?: string[]
    instance_families?: string[]
    exclude_gpu?: boolean
    label?: string
  }>
}

export interface FrameworkContract {
  id: string
  account_name: string
  title?: string
  contract_no?: string
  cloud_uid?: string
  effective_from?: string | null
  effective_to?: string | null
  status: "draft" | "active" | "archived" | string
  priority?: number
  rules: FrameworkContractRules
  source_pdf_name?: string | null
  parse_meta?: { warnings?: string[] }
  notes?: string | null
  created_at?: string
  updated_at?: string
}

export interface SavingsOpportunitiesData {
  contract?: {
    id?: string | null
    title?: string | null
    contract_no?: string | null
    effective_from?: string | null
    effective_to?: string | null
    status?: string | null
    configured?: boolean
    period_miss?: boolean
    billing_cycle?: string | null
  }
  opportunities: SavingsOpportunity[]
  suggestions?: SavingsOpportunity[]
  summary: {
    total_opportunities?: number
    total_suggestions?: number
    annual_savings_total?: number
    total_savings_potential?: number
    by_type_annual_savings?: Record<string, number>
    high_priority_count?: number
    medium_priority_count?: number
    low_priority_count?: number
    note?: string
  }
}
