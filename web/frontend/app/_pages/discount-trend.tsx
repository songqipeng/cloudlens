"use client"

import { useEffect, useMemo, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableColumn } from "@/components/ui/table"
import { useAccount } from "@/contexts/account-context"
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

const getTrendIcon = (trend: string) => {
  if (trend === "上升") return <TrendingUp className="w-4 h-4 text-green-500" />
  if (trend === "下降") return <TrendingDown className="w-4 h-4 text-red-500" />
  return <Minus className="w-4 h-4 text-gray-500" />
}

const getTrendColor = (trend: string) => {
  if (trend === "上升") return "text-green-600 dark:text-green-400"
  if (trend === "下降") return "text-red-600 dark:text-red-400"
  return "text-gray-600 dark:text-gray-400"
}

export default function DiscountTrendPage() {
  const { currentAccount } = useAccount()
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
      label: "产品名称",
      sortable: true,
      render: (value) => <span className="font-medium">{value}</span>,
    },
    {
      key: "total_discount",
      label: "累计折扣",
      sortable: true,
      render: (_, row) => <span className="font-mono text-green-600 dark:text-green-400">{fmtCny(row.data.total_discount)}</span>,
    },
    {
      key: "avg_discount_rate",
      label: "平均折扣率",
      sortable: true,
      render: (_, row) => <span className="font-mono">{fmtPct(row.data.avg_discount_rate)}</span>,
    },
    {
      key: "latest_discount_rate",
      label: "最新折扣率",
      sortable: true,
      render: (_, row) => <span className="font-mono">{fmtPct(row.data.latest_discount_rate)}</span>,
    },
    {
      key: "rate_change",
      label: "折扣率变化",
      sortable: true,
      render: (_, row) => (
        <span className={`font-mono ${row.data.rate_change > 0 ? 'text-green-600' : row.data.rate_change < 0 ? 'text-red-600' : ''}`}>
          {row.data.rate_change > 0 ? '+' : ''}{fmtPct(row.data.rate_change)}
        </span>
      ),
    },
    {
      key: "trend",
      label: "趋势",
      sortable: true,
      render: (_, row) => (
        <div className="flex items-center gap-1">
          {getTrendIcon(row.data.trend)}
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
      label: "实例ID",
      render: (value) => <code className="text-xs">{value}</code>,
    },
    {
      key: "instance_name",
      label: "实例名称",
      render: (value) => <span className="text-sm">{value || "-"}</span>,
    },
    {
      key: "product_name",
      label: "产品",
      render: (value) => <span className="text-sm">{value}</span>,
    },
    {
      key: "official_price",
      label: "官网价",
      sortable: true,
      render: (value) => <span className="font-mono text-xs">{fmtCny(Number(value))}</span>,
    },
    {
      key: "discount_amount",
      label: "折扣金额",
      sortable: true,
      render: (value) => <span className="font-mono text-xs text-green-600 dark:text-green-400">{fmtCny(Number(value))}</span>,
    },
    {
      key: "discount_pct",
      label: "折扣率",
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
      label: "应付金额",
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
            <p className="text-muted-foreground">请先选择账号</p>
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
              <h2 className="text-3xl font-bold tracking-tight">折扣趋势分析</h2>
              <p className="text-muted-foreground mt-1">
                {months >= 99 ? "显示全部历史数据" : `显示最近${months}个月数据`}
                {trendData?.timeline && ` (${trendData.timeline.length}个月)`}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => fetchData(false)}
                disabled={loading}
                className="px-4 py-2 rounded-lg border border-border hover:bg-muted/40 transition-colors text-sm disabled:opacity-50"
              >
                加载缓存
              </button>
              <button
                onClick={() => fetchData(true)}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm disabled:opacity-50"
              >
                强制刷新
              </button>
            </div>
          </div>

          {/* 时间范围选择器 */}
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                {/* 预设时间范围 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">时间范围</label>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(3); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months === 3
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      近3个月
                    </button>
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(6); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months === 6
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      近6个月
                    </button>
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(12); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months === 12
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      近1年
                    </button>
                    <button
                      onClick={() => { setTimeRangeMode("preset"); setMonths(99); }}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "preset" && months >= 99
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      全部时间
                    </button>
                    <button
                      onClick={() => setTimeRangeMode("custom")}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        timeRangeMode === "custom"
                          ? "bg-purple-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      自定义范围
                    </button>
                  </div>
                </div>

                {/* 自定义时间范围 */}
                {timeRangeMode === "custom" && (
                  <div className="flex flex-col sm:flex-row gap-3 items-end pt-2 border-t">
                    <div className="flex-1">
                      <label className="text-sm font-medium mb-1 block">开始月份</label>
                      <input
                        type="month"
                        value={customStartMonth}
                        onChange={(e) => setCustomStartMonth(e.target.value)}
                        max={customEndMonth || undefined}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-sm font-medium mb-1 block">结束月份</label>
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
                      应用
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
              <div className="text-sm text-muted-foreground">正在分析账单数据...</div>
            </div>
          </div>
        ) : error ? (
          <Card className="border-destructive/30 bg-destructive/5">
            <CardContent className="p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-destructive mt-0.5" />
                <div>
                  <div className="font-medium text-destructive mb-1">加载失败</div>
                  <div className="text-sm text-muted-foreground">{error}</div>
                  <div className="mt-4 text-sm space-y-1">
                    <p className="font-medium">提示:</p>
                    <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                      <li>请确保已从阿里云控制台下载账单CSV文件</li>
                      <li>将CSV文件放在项目根目录的账号文件夹中（如: 1844634015852583-ydzn/）</li>
                      <li>或联系管理员配置账单数据源</li>
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
                  <CardTitle className="text-sm text-muted-foreground">最新折扣率</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-primary">{fmtPct(trendData.latest_discount_rate)}</div>
                  <div className={`text-sm mt-2 flex items-center gap-1 ${trendData.discount_rate_change > 0 ? 'text-green-600' : trendData.discount_rate_change < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                    {trendData.discount_rate_change > 0 ? <TrendingUp className="w-4 h-4" /> : trendData.discount_rate_change < 0 ? <TrendingDown className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
                    <span>{trendData.discount_rate_change > 0 ? '+' : ''}{trendData.discount_rate_change_pct.toFixed(2)}% vs 首月</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">平均折扣率</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{fmtPct(trendData.average_discount_rate)}</div>
                  <div className="text-sm text-muted-foreground mt-2">
                    最近 {data?.data?.analysis_periods.length || 6} 个月
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">折扣趋势</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${getTrendColor(trendData.trend_direction)}`}>
                    {trendData.trend_direction}
                  </div>
                  <div className="text-sm text-muted-foreground mt-2">
                    范围: {fmtPct(trendData.min_discount_rate)} - {fmtPct(trendData.max_discount_rate)}
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">累计节省</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-600 dark:text-green-400">
                    {fmtCny(trendData.total_savings_6m)}
                  </div>
                  <div className="text-sm text-muted-foreground mt-2">
                    最近 {data?.data?.analysis_periods.length || 6} 个月
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
                    <CardTitle>折扣率变化趋势</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="period" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" label={{ value: '折扣率 (%)', angle: -90, position: 'insideLeft' }} />
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
                    <CardTitle>折扣金额与官网价对比</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="period" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" label={{ value: '金额 (¥)', angle: -90, position: 'insideLeft' }} />
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
                  <CardTitle>产品折扣分析 (TOP 20)</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table data={productRows.slice(0, 20)} columns={productColumns} />
                </CardContent>
              </Card>
            )}

            {activeTab === "contracts" && contractData && (
              <Card className="glass border border-border/50 shadow-xl">
                <CardHeader>
                  <CardTitle>合同折扣分析 (TOP 10)</CardTitle>
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
                            <div className="text-xs text-muted-foreground">累计节省</div>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-border/50">
                          <div>
                            <div className="text-xs text-muted-foreground">平均折扣率</div>
                            <div className="font-mono text-sm font-medium">{fmtPct(data.avg_discount_rate)}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">最新折扣率</div>
                            <div className="font-mono text-sm font-medium">{fmtPct(data.latest_discount_rate)}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">覆盖月份</div>
                            <div className="font-mono text-sm font-medium">{data.periods.length}个月</div>
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
                  <CardTitle>高折扣实例 TOP 50（最近一个月）</CardTitle>
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
              <div className="text-muted-foreground">暂无折扣趋势数据</div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}
