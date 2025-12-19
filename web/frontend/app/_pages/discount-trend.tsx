"use client"

import { useEffect, useMemo, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableColumn } from "@/components/ui/table"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"
import { TrendingUp, TrendingDown, Minus, AlertCircle } from "lucide-react"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from "recharts"

interface TrendAnalysis {
  timeline: Array<{
    period: string
    official_price: number
    discount_amount: number
    discount_rate: number
    payable_amount: number
  }>
  latest_period: string
  latest_discount_rate: number
  discount_rate_change: number
  discount_rate_change_pct: number
  discount_amount_change: number
  trend_direction: string
  average_discount_rate: number
  max_discount_rate: number
  min_discount_rate: number
  total_savings_6m: number
}

interface ProductAnalysis {
  [product: string]: {
    total_discount: number
    avg_discount_rate: number
    latest_discount_rate: number
    rate_change: number
    trend: string
    periods: string[]
    discount_rates: number[]
  }
}

interface ContractAnalysis {
  [contract: string]: {
    discount_name: string
    total_discount: number
    avg_discount_rate: number
    latest_discount_rate: number
    periods: string[]
    discount_amounts: number[]
  }
}

interface TopInstanceDiscount {
  instance_id: string
  instance_name: string
  product_name: string
  official_price: number
  discount_amount: number
  payable_amount: number
  discount_rate: number
  discount_pct: number
}

interface DiscountTrendResponse {
  success: boolean
  data?: {
    account_name: string
    analysis_periods: string[]
    trend_analysis: TrendAnalysis
    product_analysis: ProductAnalysis
    contract_analysis: ContractAnalysis
    top_instance_discounts: TopInstanceDiscount[]
    generated_at: string
  }
  error?: string
  cached?: boolean
}

const fmtCny = (n: number) => `¥${(Number.isFinite(n) ? n : 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const fmtPct = (n: number) => `${(Number.isFinite(n) ? n * 100 : 0).toFixed(2)}%`

const getTrendIcon = (trend: string, t: any) => {
  if (trend === "上升" || trend === "Rising") return <TrendingUp className="w-4 h-4 text-green-500" />
  if (trend === "下降" || trend === "Falling") return <TrendingDown className="w-4 h-4 text-red-500" />
  return <Minus className="w-4 h-4 text-gray-500" />
}

const getTrendColor = (trend: string) => {
  if (trend === "上升" || trend === "Rising") return "text-green-600 dark:text-green-400"
  if (trend === "下降" || trend === "Falling") return "text-red-600 dark:text-red-400"
  return "text-gray-600 dark:text-gray-400"
}

export default function DiscountTrendPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [months, setMonths] = useState(99) // 默认显示全部数据
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DiscountTrendResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"overview" | "products" | "contracts" | "instances">("overview")
  const [customStartMonth, setCustomStartMonth] = useState("")
  const [customEndMonth, setCustomEndMonth] = useState("")
  const [timeRangeMode, setTimeRangeMode] = useState<"preset" | "custom">("preset")

  useEffect(() => {
    if (!currentAccount) {
      setLoading(false)
      return
    }
    fetchData(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount, months])

  const fetchData = async (forceRefresh: boolean) => {
    setLoading(true)
    setError(null)
    
    try {
      const res = await apiGet<DiscountTrendResponse>(
        "/discounts/trend",
        { months: months.toString(), force_refresh: forceRefresh ? "true" : "false" }
      )
      
      if (res?.success && res.data) {
        setData(res)
      } else {
        setError(res?.error || "加载失败")
      }
    } catch (e: any) {
      console.error("Failed to fetch discount trend:", e)
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const trendData = data?.data?.trend_analysis
  const productData = data?.data?.product_analysis
  const contractData = data?.data?.contract_analysis
  const instanceData = data?.data?.top_instance_discounts

  // 准备图表数据
  const chartData = useMemo(() => {
    if (!trendData?.timeline) return []
    return trendData.timeline.map((t) => ({
      period: t.period,
      折扣率: (t.discount_rate * 100).toFixed(2),
      官网价: t.official_price,
      折扣金额: t.discount_amount,
      应付金额: t.payable_amount,
    }))
  }, [trendData])

  // 产品数据表格
  const productColumns: TableColumn<{ product: string; data: ProductAnalysis[string] }>[] = [
    {
      key: "product",
      label: t.discountTrend.productName,
      sortable: true,
      render: (value) => <span className="font-medium">{value}</span>,
    },
    {
      key: "total_discount",
      label: t.discountTrend.totalDiscount,
      sortable: true,
      render: (_, row) => <span className="font-mono text-green-600 dark:text-green-400">{fmtCny(row.data.total_discount)}</span>,
    },
    {
      key: "avg_discount_rate",
      label: t.discountTrend.avgDiscountRate,
      sortable: true,
      render: (_, row) => <span className="font-mono">{fmtPct(row.data.avg_discount_rate)}</span>,
    },
    {
      key: "latest_discount_rate",
      label: t.discountTrend.latestDiscountRate,
      sortable: true,
      render: (_, row) => <span className="font-mono">{fmtPct(row.data.latest_discount_rate)}</span>,
    },
    {
      key: "rate_change",
      label: t.discountTrend.discountRateChange,
      sortable: true,
      render: (_, row) => (
        <span className={`font-mono ${row.data.rate_change > 0 ? 'text-green-600' : row.data.rate_change < 0 ? 'text-red-600' : ''}`}>
          {row.data.rate_change > 0 ? '+' : ''}{fmtPct(row.data.rate_change)}
        </span>
      ),
    },
    {
      key: "trend",
      label: t.discountTrend.trend,
      sortable: true,
      render: (_, row) => (
        <div className="flex items-center gap-1">
          {getTrendIcon(row.data.trend, t)}
          <span className={getTrendColor(row.data.trend)}>{row.data.trend}</span>
        </div>
      ),
    },
  ]

  const productRows = useMemo(() => {
    if (!productData) return []
    return Object.entries(productData).map(([product, data]) => ({
      product,
      data,
      total_discount: data.total_discount,
      avg_discount_rate: data.avg_discount_rate,
      latest_discount_rate: data.latest_discount_rate,
      rate_change: data.rate_change,
      trend: data.trend,
    }))
  }, [productData])

  // 实例数据表格
  const instanceColumns: TableColumn<TopInstanceDiscount>[] = [
    {
      key: "instance_id",
      label: t.discountTrend.instanceId,
      render: (value) => <code className="text-xs">{value}</code>,
    },
    {
      key: "instance_name",
      label: t.discountTrend.instanceName,
      render: (value) => <span className="text-sm">{value || "-"}</span>,
    },
    {
      key: "product_name",
      label: t.discountTrend.product,
      render: (value) => <span className="text-sm">{value}</span>,
    },
    {
      key: "official_price",
      label: t.discountTrend.officialPrice,
      sortable: true,
      render: (value) => <span className="font-mono text-xs">{fmtCny(Number(value))}</span>,
    },
    {
      key: "discount_amount",
      label: t.discountTrend.discountAmount,
      sortable: true,
      render: (value) => <span className="font-mono text-xs text-green-600 dark:text-green-400">{fmtCny(Number(value))}</span>,
    },
    {
      key: "discount_pct",
      label: t.discountTrend.discountRate,
      sortable: true,
      render: (value) => {
        const pct = Number(value)
        const badgeClass = pct >= 50 ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
          pct >= 30 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' :
          'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
        return (
          <span className={`px-2 py-1 rounded text-xs font-medium ${badgeClass}`}>
            {pct.toFixed(1)}%
          </span>
        )
      },
    },
    {
      key: "payable_amount",
      label: t.discountTrend.payableAmount,
      sortable: true,
      render: (value) => <span className="font-mono text-xs">{fmtCny(Number(value))}</span>,
    },
  ]

  if (!currentAccount) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-[50vh]">
          <div className="text-center space-y-4">
            <AlertCircle className="w-12 h-12 mx-auto text-muted-foreground" />
            <p className="text-muted-foreground">{t.discounts.selectAccountFirst}</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h2 className="text-3xl font-bold tracking-tight">{t.discountTrend.title}</h2>
              <p className="text-muted-foreground mt-1">
                {months >= 99 ? t.discountTrend.showAllHistory : t.discountTrend.showRecentMonths.replace('{months}', months.toString())}
                {trendData?.timeline && ` (${trendData.timeline.length}${t.discountTrend.months})`}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => fetchData(false)}
                disabled={loading}
                className="px-4 py-2 rounded-lg border border-border hover:bg-muted/40 transition-colors text-sm disabled:opacity-50"
              >
                {t.discountTrend.loadCache}
              </button>
              <button
                onClick={() => fetchData(true)}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm disabled:opacity-50"
              >
                {t.discountTrend.forceRefresh}
              </button>
            </div>
          </div>

          {/* 时间范围选择器 */}
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                {/* 预设时间范围 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">{t.discountTrend.timeRange}</label>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(3); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months === 3
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {t.discountTrend.last3Months}
                    </button>
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(6); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months === 6
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {t.discountTrend.last6Months}
                    </button>
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(12); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months === 12
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {t.discountTrend.last1Year}
                    </button>
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(99); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months >= 99
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {t.discountTrend.allTime}
                    </button>
                    <button
                      onClick={() => setTimeRangeMode("custom")}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "custom"
                          ? "bg-purple-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {t.discountTrend.customRange}
                    </button>
                  </div>
                </div>

                {/* 自定义时间范围 */}
                {timeRangeMode === "custom" && (
                  <div className="flex flex-col sm:flex-row gap-3 items-end pt-2 border-t">
                    <div className="flex-1">
                      <label className="text-sm font-medium mb-1 block">{t.discountTrend.startMonth}</label>
                      <input
                        type="month"
                        value={customStartMonth}
                        onChange={(e) => setCustomStartMonth(e.target.value)}
                        max={customEndMonth || undefined}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-sm font-medium mb-1 block">{t.discountTrend.endMonth}</label>
                      <input
                        type="month"
                        value={customEndMonth}
                        onChange={(e) => setCustomEndMonth(e.target.value)}
                        min={customStartMonth || undefined}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700"
                      />
                    </div>
                    <button
                      onClick={() => {
                        if (customStartMonth && customEndMonth) {
                          // 计算月份差
                          const start = new Date(customStartMonth + "-01")
                          const end = new Date(customEndMonth + "-01")
                          const monthsDiff = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth()) + 1
                          setMonths(monthsDiff > 0 ? monthsDiff : 1)
                        }
                      }}
                      disabled={!customStartMonth || !customEndMonth}
                      className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {t.discountTrend.apply}
                    </button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-[40vh]">
            <div className="text-center space-y-2">
              <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
              <div className="text-sm text-muted-foreground">{t.discountTrend.analyzing}</div>
            </div>
          </div>
        ) : error ? (
          <Card className="border-destructive/30 bg-destructive/5">
            <CardContent className="p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-destructive mt-0.5" />
                <div>
                  <div className="font-medium text-destructive mb-1">{t.discountTrend.loadFailed}</div>
                  <div className="text-sm text-muted-foreground">{error}</div>
                  <div className="mt-4 text-sm space-y-1">
                    <p className="font-medium">{t.discountTrend.possibleReasons}</p>
                    <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                      <li>{t.discountTrend.noBillData}</li>
                      <li>{t.discountTrend.runCommand}</li>
                      <li>{t.discountTrend.waitSync}</li>
                      <li>{t.discountTrend.contactAdmin}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ) : trendData ? (
          <>
            {/* 核心指标卡片 */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.discountTrend.latestDiscountRateTitle}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-primary">{fmtPct(trendData.latest_discount_rate)}</div>
                  <div className={`text-sm mt-2 flex items-center gap-1 ${trendData.discount_rate_change > 0 ? 'text-green-600' : trendData.discount_rate_change < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                    {trendData.discount_rate_change > 0 ? <TrendingUp className="w-4 h-4" /> : trendData.discount_rate_change < 0 ? <TrendingDown className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
                    <span>{trendData.discount_rate_change > 0 ? '+' : ''}{trendData.discount_rate_change_pct.toFixed(2)}% {t.discountTrend.vsFirstMonth}</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.discountTrend.avgDiscountRateTitle}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{fmtPct(trendData.average_discount_rate)}</div>
                  <div className="text-sm text-muted-foreground mt-2">
                    {t.discountTrend.recentMonths.replace('{count}', (data?.data?.analysis_periods.length || 6).toString())}
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.discountTrend.discountTrendTitle}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${getTrendColor(trendData.trend_direction)}`}>
                    {trendData.trend_direction}
                  </div>
                  <div className="text-sm text-muted-foreground mt-2">
                    {t.discountTrend.range} {fmtPct(trendData.min_discount_rate)} - {fmtPct(trendData.max_discount_rate)}
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.discountTrend.cumulativeSavingsTitle}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-600 dark:text-green-400">
                    {fmtCny(trendData.total_savings_6m)}
                  </div>
                  <div className="text-sm text-muted-foreground mt-2">
                    {t.discountTrend.recentMonths.replace('{count}', (data?.data?.analysis_periods.length || 6).toString())}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-border">
              {[
                { key: "overview" as const, label: "趋势总览" },
                { key: "products" as const, label: "产品分析" },
                { key: "contracts" as const, label: "合同分析" },
                { key: "instances" as const, label: "TOP实例" },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === tab.key
                      ? "border-b-2 border-primary text-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {/* 折扣率趋势图 */}
                <Card className="glass border border-border/50 shadow-xl">
                  <CardHeader>
                    <CardTitle>{t.discountTrend.discountRateTrend}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="period" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" label={{ value: t.discountTrend.discountRateUnit, angle: -90, position: 'insideLeft' }} />
                        <Tooltip
                          contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                          formatter={(value: any) => [`${Number(value).toFixed(2)}%`, '折扣率']}
                        />
                        <Line
                          type="monotone"
                          dataKey="折扣率"
                          stroke="#667eea"
                          strokeWidth={3}
                          dot={{ fill: '#667eea', r: 4 }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                {/* 折扣金额趋势图 */}
                <Card className="glass border border-border/50 shadow-xl">
                  <CardHeader>
                    <CardTitle>{t.discountTrend.discountAmountComparison}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="period" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" label={{ value: t.discountTrend.amountUnit, angle: -90, position: 'insideLeft' }} />
                        <Tooltip
                          contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                          formatter={(value: any) => [fmtCny(Number(value)), '']}
                        />
                        <Legend />
                        <Bar dataKey="官网价" fill="#93c5fd" />
                        <Bar dataKey="折扣金额" fill="#34d399" />
                        <Line type="monotone" dataKey="应付金额" stroke="#f59e0b" strokeWidth={2} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === "products" && productData && (
              <Card className="glass border border-border/50 shadow-xl">
                <CardHeader>
                  <CardTitle>{t.discountTrend.productAnalysis}</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table data={productRows.slice(0, 20)} columns={productColumns} />
                </CardContent>
              </Card>
            )}

            {activeTab === "contracts" && contractData && (
              <Card className="glass border border-border/50 shadow-xl">
                <CardHeader>
                  <CardTitle>{t.discountTrend.contractAnalysis}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(contractData).slice(0, 10).map(([contract, data], idx) => (
                      <div key={contract} className="p-4 rounded-lg border border-border/50 hover:bg-muted/20 transition-colors">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-lg font-bold text-primary">#{idx + 1}</span>
                              <span className="font-medium">{data.discount_name}</span>
                            </div>
                            <code className="text-xs text-muted-foreground mt-1 block">{contract}</code>
                          </div>
                          <div className="text-right">
                            <div className="text-xl font-bold text-green-600 dark:text-green-400">{fmtCny(data.total_discount)}</div>
                            <div className="text-xs text-muted-foreground">{t.discountTrend.cumulativeSavings}</div>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-border/50">
                          <div>
                            <div className="text-xs text-muted-foreground">{t.discountTrend.avgDiscountRateLabel}</div>
                            <div className="font-mono text-sm font-medium">{fmtPct(data.avg_discount_rate)}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t.discountTrend.latestDiscountRateLabel}</div>
                            <div className="font-mono text-sm font-medium">{fmtPct(data.latest_discount_rate)}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t.discountTrend.coverageMonths}</div>
                            <div className="font-mono text-sm font-medium">{data.periods.length}{t.discountTrend.monthsUnit}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "instances" && instanceData && (
              <Card className="glass border border-border/50 shadow-xl">
                <CardHeader>
                  <CardTitle>{t.discountTrend.topInstances}</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table data={instanceData.slice(0, 50)} columns={instanceColumns} />
                </CardContent>
              </Card>
            )}
          </>
        ) : (
          <Card className="border-muted bg-muted/5">
            <CardContent className="p-6 text-center">
              <div className="text-muted-foreground">{t.discountTrend.noData}</div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}


