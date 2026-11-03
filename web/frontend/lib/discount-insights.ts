/**
 * 用页面已加载的折扣数据生成洞察，避免再打一遍慢接口。
 */

export interface DiscountInsightItem {
  category: string
  level: "info" | "warning" | "success"
  title: string
  description: string
  recommendation: string
}

interface QuarterLite {
  period?: string
  avg_discount_rate?: number
}

interface ProductLite {
  product_name?: string
  total_consumption?: number
  avg_discount_rate?: number
}

export function buildDiscountInsights(input: {
  quarters?: QuarterLite[]
  products?: ProductLite[]
  suggestionCount?: number
  potentialSavings?: number
  anomalyCount?: number
  rateDifference?: number
}): DiscountInsightItem[] {
  const insights: DiscountInsightItem[] = []
  const quarters = input.quarters || []
  const products = input.products || []

  if (quarters.length >= 2) {
    const latest = quarters[quarters.length - 1]
    const prev = quarters[quarters.length - 2]
    const latestRate = Number(latest.avg_discount_rate) || 0
    const prevRate = Number(prev.avg_discount_rate) || 0
    const change = latestRate - prevRate
    insights.push({
      category: "趋势分析",
      level: change >= 0 ? "info" : "warning",
      title: `季度折扣率${change >= 0 ? "上升" : "下降"}`,
      description: `最新季度${latest.period || "-"}折扣率为${(latestRate * 100).toFixed(1)}%，较上季度${(change * 100).toFixed(1)}个百分点`,
      recommendation: change >= 0 ? "持续优化" : "需要与商务团队沟通合同续约",
    })
  }

  if (products.length > 0) {
    const topProduct = products[0]
    const consumption = Number(topProduct.total_consumption) || 0
    const topRate = Number(topProduct.avg_discount_rate) || 0
    insights.push({
      category: "产品分析",
      level: "success",
      title: `最大消费产品: ${topProduct.product_name || "-"}`,
      description: `消费${consumption.toLocaleString()}元，平均折扣率${(topRate * 100).toFixed(1)}%`,
      recommendation: "保持当前折扣策略",
    })

    const lowest = products.reduce((min, item) =>
      Number(item.avg_discount_rate) < Number(min.avg_discount_rate) ? item : min
    )
    const lowestRate = Number(lowest.avg_discount_rate) || 0
    if (lowestRate < 0.4) {
      insights.push({
        category: "产品分析",
        level: "warning",
        title: `低折扣产品: ${lowest.product_name || "-"}`,
        description: `折扣率仅${(lowestRate * 100).toFixed(1)}%`,
        recommendation: "建议与商务沟通提升该产品折扣率",
      })
    }
  }

  if ((input.suggestionCount || 0) > 0) {
    const savings = Number(input.potentialSavings) || 0
    insights.push({
      category: "优化机会",
      level: "success",
      title: `发现${input.suggestionCount}个优化机会`,
      description: `转为包年包月可年节省${savings.toLocaleString()}元`,
      recommendation: "优先转换运行时间长、成本高的实例",
    })
  }

  if ((input.anomalyCount || 0) > 0) {
    insights.push({
      category: "异常检测",
      level: "warning",
      title: `检测到${input.anomalyCount}个异常月份`,
      description: "折扣率波动超过阈值",
      recommendation: "查看异常月份的大额订单或合同变更",
    })
  }

  if ((input.rateDifference || 0) > 0.1) {
    insights.push({
      category: "计费优化",
      level: "info",
      title: `包年包月折扣率优势${((input.rateDifference || 0) * 100).toFixed(1)}%`,
      description: "包年包月折扣率显著高于按量付费",
      recommendation: "评估长期运行资源，转为包年包月",
    })
  }

  return insights
}
