"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"
import { ArrowLeft } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { EmptyState } from "@/components/ui/empty-state"
import { RabbitLoading } from "@/components/loading"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, ApiError } from "@/lib/api"
import { toastError } from "@/components/ui/toast"
import type {
  AttributionCategoryKey,
  AttributionCompareType,
  CostAttributionReport,
} from "@/types/cost-attribution"

const PIE_COLORS = ["#ef4444", "#f59e0b", "#3b82f6", "#8b5cf6", "#64748b"]

const CATEGORY_LABEL: Record<"zh" | "en", Record<AttributionCategoryKey, string>> = {
  zh: {
    resource_count: "资源数量/用量变化",
    discount: "折扣率变化",
    price: "单价变化",
    product_mix: "产品结构变化",
    other: "其他/舍入",
  },
  en: {
    resource_count: "Quantity / usage",
    discount: "Discount rate",
    price: "Unit price",
    product_mix: "Product mix",
    other: "Other / rounding",
  },
}

function money(value: number): string {
  const amount = Math.round(value || 0)
  return `¥${amount.toLocaleString("zh-CN")}`
}

function signedMoney(value: number): string {
  const prefix = value > 0 ? "+" : ""
  return `${prefix}${money(value)}`
}

export default function CostAttributionPage() {
  const { currentAccount, loading: accountLoading } = useAccount()
  const { t, locale } = useLocale()
  const copy = t.costAttribution
  const [report, setReport] = useState<CostAttributionReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [compareType, setCompareType] = useState<AttributionCompareType>("mom")
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    if (accountLoading) {
      setLoading(true)
      return
    }
    if (!currentAccount) {
      setLoading(false)
      setReport(null)
      return
    }
    void fetchReport(compareType)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount, accountLoading, compareType])

  async function fetchReport(type: AttributionCompareType) {
    if (!currentAccount) return
    setLoading(true)
    try {
      const response = await apiGet<{ success?: boolean; data?: CostAttributionReport }>(
        "/cost/attribution",
        { account: currentAccount, compare_type: type }
      )
      if (response?.data) {
        setReport(response.data)
      } else {
        setReport(null)
      }
    } catch (error) {
      console.error("获取成本归因失败:", error)
      if (error instanceof ApiError) {
        toastError(error.message || copy.noData)
      } else {
        toastError(copy.noData)
      }
      setReport(null)
    } finally {
      setLoading(false)
    }
  }

  const costHref = currentAccount
    ? `/a/${encodeURIComponent(currentAccount)}/cost`
    : "/cost"
  const labels = CATEGORY_LABEL[locale === "en" ? "en" : "zh"]
  const hasData = Boolean(report && (report.current_total > 0 || report.compare_total > 0))
  const pieData = (report?.attributions || [])
    .filter((item) => Math.abs(item.impact) >= 0.01)
    .map((item) => ({
      name: labels[item.category] || item.label,
      value: Math.abs(item.impact),
      impact: item.impact,
    }))

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link
              href={costHref}
              className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2"
            >
              <ArrowLeft className="h-4 w-4" />
              {copy.backToCost}
            </Link>
            <h2 className="text-3xl font-bold tracking-tight">{copy.title}</h2>
            <p className="text-muted-foreground mt-1">{copy.description}</p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setCompareType("mom")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                compareType === "mom"
                  ? "bg-primary text-primary-foreground"
                  : "bg-white/5 text-muted-foreground hover:text-foreground"
              }`}
            >
              {copy.mom}
            </button>
            <button
              type="button"
              onClick={() => setCompareType("yoy")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                compareType === "yoy"
                  ? "bg-primary text-primary-foreground"
                  : "bg-white/5 text-muted-foreground hover:text-foreground"
              }`}
            >
              {copy.yoy}
            </button>
          </div>
        </div>

        {loading || accountLoading ? (
          <div className="flex items-center justify-center h-64">
            <RabbitLoading delay={3000} />
          </div>
        ) : !hasData ? (
          <Card>
            <EmptyState title={copy.noData} description={report?.message || copy.noDataDesc} />
          </Card>
        ) : (
          report && (
            <>
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm text-muted-foreground">
                      {copy.comparePeriod} {report.compare_cycle}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{money(report.compare_total)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm text-muted-foreground">
                      {copy.currentPeriod} {report.current_cycle}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{money(report.current_total)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm text-muted-foreground">{copy.delta}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-3xl font-bold ${report.delta > 0 ? "text-red-500" : "text-green-500"}`}>
                      {signedMoney(report.delta)}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm text-muted-foreground">{copy.shareOfChange}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-3xl font-bold ${report.delta_pct > 0 ? "text-red-500" : "text-green-500"}`}>
                      {report.delta_pct > 0 ? "+" : ""}
                      {report.delta_pct.toFixed(1)}%
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>{copy.whyChanged}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[360px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            outerRadius={110}
                            dataKey="value"
                            labelLine={false}
                            label={(props: { name?: string; percent?: number }) =>
                              `${props.name || ""} ${((props.percent || 0) * 100).toFixed(0)}%`
                            }
                          >
                            {pieData.map((entry, index) => (
                              <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(value: number | string) => money(Number(value || 0))}
                            contentStyle={{
                              background: "rgba(15, 15, 20, 0.95)",
                              border: "1px solid rgba(255, 255, 255, 0.1)",
                              borderRadius: "12px",
                              color: "#ffffff",
                            }}
                          />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <div className="space-y-4">
                  {report.attributions.map((item) => {
                    const open = expanded === item.category
                    return (
                      <Card key={item.category}>
                        <button
                          type="button"
                          className="w-full text-left"
                          onClick={() => setExpanded(open ? null : item.category)}
                        >
                          <CardHeader className="flex flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-base">
                              {labels[item.category] || item.label}
                            </CardTitle>
                            <div className="text-right">
                              <div className={`text-lg font-bold ${item.impact > 0 ? "text-red-500" : "text-green-500"}`}>
                                {signedMoney(item.impact)}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {copy.shareOfChange} {item.impact_pct.toFixed(0)}%
                              </div>
                            </div>
                          </CardHeader>
                        </button>
                        {open && (
                          <CardContent className="space-y-3">
                            {item.details.map((detail) => (
                              <div
                                key={`${item.category}-${detail.product_code}-${detail.description}`}
                                className="border-l-2 border-white/10 pl-3"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <span className="font-medium">
                                    {detail.product_name || detail.product_code}
                                  </span>
                                  <span className={detail.cost_impact > 0 ? "text-red-400" : "text-green-400"}>
                                    {signedMoney(detail.cost_impact)}
                                  </span>
                                </div>
                                <p className="text-sm text-muted-foreground">{detail.description}</p>
                              </div>
                            ))}
                          </CardContent>
                        )}
                      </Card>
                    )
                  })}
                </div>
              </div>

              {report.recommendations.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>{copy.recommendations}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {report.recommendations.map((rec) => (
                      <div key={rec.title} className="rounded-lg border border-white/10 p-4">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <Badge
                            variant={
                              rec.priority === "high"
                                ? "danger"
                                : rec.priority === "medium"
                                  ? "warning"
                                  : "info"
                            }
                          >
                            {rec.priority === "high"
                              ? copy.highPriority
                              : rec.priority === "medium"
                                ? copy.mediumPriority
                                : copy.lowPriority}
                          </Badge>
                          <h4 className="font-semibold">{rec.title}</h4>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">{rec.description}</p>
                        <p className="text-sm">{rec.action}</p>
                        {rec.estimated_savings > 0 && (
                          <p className="text-sm text-green-400 mt-2">
                            {copy.estimatedSavings}: {money(rec.estimated_savings)}/月
                          </p>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {report.products.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>{copy.products}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="text-muted-foreground">
                          <tr className="border-b border-white/10">
                            <th className="text-left py-2 font-medium">{locale === "en" ? "Product" : "产品"}</th>
                            <th className="text-right py-2 font-medium">{report.compare_cycle}</th>
                            <th className="text-right py-2 font-medium">{report.current_cycle}</th>
                            <th className="text-right py-2 font-medium">{copy.delta}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {report.products.map((product) => (
                            <tr key={product.product_code} className="border-b border-white/5">
                              <td className="py-2">
                                {product.product_name || product.product_code}
                                {product.status !== "existing" && (
                                  <span className="ml-2 text-xs text-muted-foreground">
                                    {product.status === "new" ? copy.newProduct : copy.removedProduct}
                                  </span>
                                )}
                              </td>
                              <td className="text-right">{money(product.compare_pretax)}</td>
                              <td className="text-right">{money(product.current_pretax)}</td>
                              <td className={`text-right ${product.delta > 0 ? "text-red-400" : "text-green-400"}`}>
                                {signedMoney(product.delta)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )
        )}
      </div>
    </DashboardLayout>
  )
}
