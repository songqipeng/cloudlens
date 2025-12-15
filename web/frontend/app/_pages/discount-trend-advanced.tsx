"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAccount } from "@/contexts/account-context"
import { apiGet } from "@/lib/api"
import { RefreshCw, TrendingUp, TrendingDown, AlertTriangle, DollarSign } from "lucide-react"
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
  Area,
} from "recharts"
import type {
  QuarterlyResponse,
  YearlyResponse,
  ProductTrendsResponse,
  RegionsResponse,
  SubscriptionTypesResponse,
  OptimizationSuggestionsResponse,
  AnomaliesResponse,
} from "@/types/discount-analysis"

export default function AdvancedDiscountTrendPage() {
  const { currentAccount } = useAccount()
  const [activeTab, setActiveTab] = useState("overview")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Data states for different analyses
  const [quarterlyData, setQuarterlyData] = useState<QuarterlyResponse | null>(null)
  const [yearlyData, setYearlyData] = useState<YearlyResponse | null>(null)
  const [productTrends, setProductTrends] = useState<ProductTrendsResponse | null>(null)
  const [regionsData, setRegionsData] = useState<RegionsResponse | null>(null)
  const [subscriptionData, setSubscriptionData] = useState<SubscriptionTypesResponse | null>(null)
  const [suggestions, setSuggestions] = useState<OptimizationSuggestionsResponse | null>(null)
  const [anomalies, setAnomaliesData] = useState<AnomaliesResponse | null>(null)
  const [insights, setInsights] = useState<any>(null)

  const fetchAllData = async (forceRefresh = false) => {
    if (!currentAccount) return
    
    setLoading(true)
    setError(null)
    
    try {
      const [quarterly, yearly, products, regions, subscription, opts, anom, insightsData] = await Promise.all([
        apiGet<QuarterlyResponse>(`/discounts/quarterly?account=${currentAccount}&quarters=8`),
        apiGet<YearlyResponse>(`/discounts/yearly?account=${currentAccount}`),
        apiGet<ProductTrendsResponse>(`/discounts/product-trends?account=${currentAccount}&months=19&top_n=10`),
        apiGet<RegionsResponse>(`/discounts/regions?account=${currentAccount}`),
        apiGet<SubscriptionTypesResponse>(`/discounts/subscription-types?account=${currentAccount}`),
        apiGet<OptimizationSuggestionsResponse>(`/discounts/optimization-suggestions?account=${currentAccount}`),
        apiGet<AnomaliesResponse>(`/discounts/anomalies?account=${currentAccount}&threshold=0.10`),
        apiGet(`/discounts/insights?account=${currentAccount}`),
      ])
      
      setQuarterlyData(quarterly)
      setYearlyData(yearly)
      setProductTrends(products)
      setRegionsData(regions)
      setSubscriptionData(subscription)
      setSuggestions(opts)
      setAnomaliesData(anom)
      setInsights(insightsData)
    } catch (err: any) {
      console.error("加载折扣分析数据失败:", err)
      setError(err.message || "加载失败")
    } finally {
      setLoading(false)
    }
  }

  const handleExport = (exportType: string) => {
    window.open(`http://localhost:8000/api/discounts/export?account=${currentAccount}&export_type=${exportType}`, '_blank')
  }

  useEffect(() => {
    fetchAllData()
  }, [currentAccount])

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `¥${(value / 1000000).toFixed(2)}M`
    if (value >= 1000) return `¥${(value / 1000).toFixed(0)}K`
    return `¥${value.toFixed(0)}`
  }

  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`

  if (loading && !quarterlyData) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-muted-foreground">正在加载高级折扣分析...</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive mb-2">
              <AlertTriangle className="h-5 w-5" />
              <p className="font-semibold">加载失败</p>
            </div>
            <p className="text-sm text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">高级折扣分析</h2>
            <p className="text-muted-foreground mt-1">
              多维度深度分析 • 8大分析维度 • 19个月历史数据
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => handleExport('all')}
              variant="outline"
              size="sm"
            >
              <DollarSign className="mr-2 h-4 w-4" />
              导出Excel
            </Button>
            <Button
              onClick={() => fetchAllData(true)}
              disabled={loading}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="overview">总览</TabsTrigger>
            <TabsTrigger value="time">时间分析</TabsTrigger>
            <TabsTrigger value="products">产品分析</TabsTrigger>
            <TabsTrigger value="regions">区域分析</TabsTrigger>
            <TabsTrigger value="billing">计费分析</TabsTrigger>
            <TabsTrigger value="advanced">高级分析</TabsTrigger>
          </TabsList>

          {/* Tab 1: Overview */}
          <TabsContent value="overview" className="space-y-6">
            <OverviewTab
              quarterly={quarterlyData}
              yearly={yearlyData}
              products={productTrends}
              regions={regionsData}
              subscription={subscriptionData}
              suggestions={suggestions}
              anomalies={anomalies}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
            />
          </TabsContent>

          {/* Tab 2: Time Analysis */}
          <TabsContent value="time" className="space-y-6">
            <TimeAnalysisTab
              quarterly={quarterlyData}
              yearly={yearlyData}
              anomalies={anomalies}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
            />
          </TabsContent>

          {/* Tab 3: Product Analysis */}
          <TabsContent value="products" className="space-y-6">
            <ProductAnalysisTab
              products={productTrends}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
            />
          </TabsContent>

          {/* Tab 4: Region Analysis */}
          <TabsContent value="regions" className="space-y-6">
            <RegionAnalysisTab
              regions={regionsData}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
            />
          </TabsContent>

          {/* Tab 5: Billing Analysis */}
          <TabsContent value="billing" className="space-y-6">
            <BillingAnalysisTab
              subscription={subscriptionData}
              suggestions={suggestions}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
            />
          </TabsContent>

          {/* Tab 6: Advanced Analysis (Phase 2) */}
          <TabsContent value="advanced" className="space-y-6">
            <AdvancedAnalysisTab
              currentAccount={currentAccount}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
            />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}

// ==================== Tab Components ====================

function OverviewTab({ quarterly, yearly, products, regions, subscription, suggestions, anomalies, formatCurrency, formatPercent }: any) {
  // 计算关键指标
  const latestQuarter = quarterly?.data?.quarters?.[quarterly.data.quarters.length - 1]
  const latestYear = yearly?.data?.years?.[yearly.data.years.length - 1]
  const topProducts = products?.data?.products?.slice(0, 5) || []
  const topRegions = regions?.data?.regions?.slice(0, 5) || []
  
  return (
    <>
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">最新季度折扣率</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercent(latestQuarter?.avg_discount_rate || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {latestQuarter?.period} • {latestQuarter?.month_count}个月
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">季度总节省</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(latestQuarter?.total_discount || 0)}</div>
            <p className="text-xs text-muted-foreground">
              环比 {latestQuarter?.rate_change > 0 ? '+' : ''}{latestQuarter?.rate_change?.toFixed(1)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">优化机会</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{suggestions?.data?.total_suggestions || 0}个实例</div>
            <p className="text-xs text-muted-foreground">
              年节省 {formatCurrency(suggestions?.data?.total_potential_savings || 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">异常检测</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{anomalies?.data?.total_anomalies || 0}个月份</div>
            <p className="text-xs text-muted-foreground">
              波动 {'>'}10%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* 季度趋势 */}
        <Card>
          <CardHeader>
            <CardTitle>季度折扣趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={quarterly?.data?.quarters || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip formatter={(value: any) => typeof value === 'number' && value < 1 ? formatPercent(value) : formatCurrency(value)} />
                <Legend />
                <Bar yAxisId="left" dataKey="total_discount" fill="#8884d8" name="折扣金额" />
                <Line yAxisId="right" type="monotone" dataKey="avg_discount_rate" stroke="#82ca9d" name="折扣率" />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* TOP产品 */}
        <Card>
          <CardHeader>
            <CardTitle>TOP 5产品折扣率</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topProducts} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={formatPercent} />
                <YAxis dataKey="product_name" type="category" width={120} />
                <Tooltip formatter={(value: any) => formatPercent(value as number)} />
                <Bar dataKey="avg_discount_rate" fill="#8884d8" name="平均折扣率" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* 智能洞察 (Phase 3) */}
      <Card>
        <CardHeader>
          <CardTitle>🤖 AI智能洞察</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {insights?.data?.insights?.map((insight: any, idx: number) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border ${
                  insight.level === 'success' ? 'border-green-500 bg-green-50' :
                  insight.level === 'warning' ? 'border-yellow-500 bg-yellow-50' :
                  'border-blue-500 bg-blue-50'
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-xs px-2 py-1 rounded-full bg-white/80 font-medium">
                    {insight.category}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium">{insight.title}</p>
                    <p className="text-sm text-muted-foreground mt-1">{insight.description}</p>
                    <p className="text-xs text-muted-foreground mt-2">💡 {insight.recommendation}</p>
                  </div>
                </div>
              </div>
            ))}
            {(!insights || !insights.data?.insights?.length) && (
              <p className="text-sm text-muted-foreground">正在生成智能洞察...</p>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  )
}

function TimeAnalysisTab({ quarterly, yearly, anomalies, formatCurrency, formatPercent }: any) {
  return (
    <>
      {/* 季度对比 */}
      <Card>
        <CardHeader>
          <CardTitle>季度对比</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={quarterly?.data?.quarters || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis yAxisId="left" tickFormatter={formatCurrency} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={formatPercent} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="total_paid" fill="#8884d8" name="实付金额" />
              <Bar yAxisId="left" dataKey="total_discount" fill="#82ca9d" name="折扣金额" />
              <Line yAxisId="right" type="monotone" dataKey="avg_discount_rate" stroke="#ff7300" name="折扣率" strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 年度对比 */}
      <Card>
        <CardHeader>
          <CardTitle>年度对比</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={yearly?.data?.years || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis yAxisId="left" tickFormatter={formatCurrency} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={formatPercent} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="total_paid" fill="#8884d8" name="实付金额" />
              <Bar yAxisId="left" dataKey="total_discount" fill="#82ca9d" name="折扣金额" />
              <Line yAxisId="right" type="monotone" dataKey="avg_discount_rate" stroke="#ff7300" name="折扣率" strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 异常检测 */}
      {anomalies?.data?.anomalies && anomalies.data.anomalies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>折扣异常检测</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {anomalies.data.anomalies.map((anomaly: any, idx: number) => (
                <div key={idx} className={`p-3 rounded-lg border ${anomaly.severity === '严重' ? 'border-red-500 bg-red-50' : 'border-yellow-500 bg-yellow-50'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{anomaly.month}</span>
                    <span className={`text-sm ${anomaly.change_pct > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {anomaly.change_pct > 0 ? '+' : ''}{anomaly.change_pct.toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{anomaly.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  )
}

function ProductAnalysisTab({ products, formatCurrency, formatPercent }: any) {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([])
  const topProducts = products?.data?.products || []
  
  useEffect(() => {
    // 默认选择TOP 5产品
    if (topProducts.length > 0 && selectedProducts.length === 0) {
      setSelectedProducts(topProducts.slice(0, 5).map((p: any) => p.product_name))
    }
  }, [topProducts])

  // 准备多产品趋势数据
  const trendData: any[] = []
  if (topProducts.length > 0) {
    const allMonths = new Set<string>()
    topProducts.forEach((product: any) => {
      product.trends.forEach((t: any) => allMonths.add(t.month))
    })
    
    Array.from(allMonths).sort().forEach((month) => {
      const dataPoint: any = { month }
      topProducts.forEach((product: any) => {
        if (selectedProducts.includes(product.product_name)) {
          const trend = product.trends.find((t: any) => t.month === month)
          if (trend) {
            dataPoint[product.product_name] = trend.discount_rate
          }
        }
      })
      trendData.push(dataPoint)
    })
  }

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d0', '#ffb366', '#a4de6c']

  return (
    <>
      {/* 产品选择器 */}
      <Card>
        <CardHeader>
          <CardTitle>选择产品（多选对比）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {topProducts.map((product: any) => (
              <Button
                key={product.product_name}
                variant={selectedProducts.includes(product.product_name) ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setSelectedProducts(prev => 
                    prev.includes(product.product_name)
                      ? prev.filter(p => p !== product.product_name)
                      : [...prev, product.product_name]
                  )
                }}
              >
                {product.product_name}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 多产品折扣趋势对比图 */}
      <Card>
        <CardHeader>
          <CardTitle>产品折扣趋势对比</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={formatPercent} />
              <Tooltip formatter={(value: any) => formatPercent(value as number)} />
              <Legend />
              {selectedProducts.map((productName, idx) => (
                <Line
                  key={productName}
                  type="monotone"
                  dataKey={productName}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 产品排行表 */}
      <Card>
        <CardHeader>
          <CardTitle>产品详细排行</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">产品名称</th>
                  <th className="text-right p-2">总消费</th>
                  <th className="text-right p-2">总折扣</th>
                  <th className="text-right p-2">平均折扣率</th>
                  <th className="text-right p-2">波动率</th>
                  <th className="text-right p-2">趋势</th>
                </tr>
              </thead>
              <tbody>
                {topProducts.map((product: any, idx: number) => (
                  <tr key={idx} className="border-b hover:bg-muted/50">
                    <td className="p-2 font-medium">{product.product_name}</td>
                    <td className="p-2 text-right">{formatCurrency(product.total_consumption)}</td>
                    <td className="p-2 text-right">{formatCurrency(product.total_discount)}</td>
                    <td className="p-2 text-right">{formatPercent(product.avg_discount_rate)}</td>
                    <td className="p-2 text-right">{formatPercent(product.volatility)}</td>
                    <td className="p-2 text-right">
                      <span className={product.trend_change_pct > 0 ? 'text-green-600' : 'text-red-600'}>
                        {product.trend_change_pct > 0 ? '+' : ''}{product.trend_change_pct.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  )
}

function RegionAnalysisTab({ regions, formatCurrency, formatPercent }: any) {
  const regionsData = regions?.data?.regions || []

  return (
    <>
      {/* 区域折扣排行 */}
      <Card>
        <CardHeader>
          <CardTitle>区域折扣排行</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={regionsData.slice(0, 10)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={formatPercent} />
              <YAxis dataKey="region_name" type="category" width={150} />
              <Tooltip formatter={(value: any) => formatPercent(value as number)} />
              <Bar dataKey="avg_discount_rate" fill="#8884d8" name="平均折扣率" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 区域详细表 */}
      <Card>
        <CardHeader>
          <CardTitle>区域详细数据</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">区域</th>
                  <th className="text-right p-2">消费金额</th>
                  <th className="text-right p-2">折扣金额</th>
                  <th className="text-right p-2">折扣率</th>
                  <th className="text-right p-2">实例数</th>
                  <th className="text-right p-2">产品数</th>
                  <th className="text-right p-2">占比</th>
                </tr>
              </thead>
              <tbody>
                {regionsData.map((region: any, idx: number) => (
                  <tr key={idx} className="border-b hover:bg-muted/50">
                    <td className="p-2 font-medium">{region.region_name}</td>
                    <td className="p-2 text-right">{formatCurrency(region.total_paid)}</td>
                    <td className="p-2 text-right">{formatCurrency(region.total_discount)}</td>
                    <td className="p-2 text-right">{formatPercent(region.avg_discount_rate)}</td>
                    <td className="p-2 text-right">{region.instance_count}</td>
                    <td className="p-2 text-right">{region.product_count}</td>
                    <td className="p-2 text-right">{region.consumption_percentage.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  )
}

function BillingAnalysisTab({ subscription, suggestions, formatCurrency, formatPercent }: any) {
  const subscriptionTypes = subscription?.data?.subscription_types || {}
  const subscriptionData = subscriptionTypes['Subscription']
  const payAsYouGoData = subscriptionTypes['PayAsYouGo']
  const rateDiff = subscription?.data?.rate_difference || 0
  const suggestionsData = suggestions?.data?.suggestions || []

  return (
    <>
      {/* 计费方式对比 */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>包年包月</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">消费金额:</span>
              <span className="font-medium">{formatCurrency(subscriptionData?.total_paid || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">折扣率:</span>
              <span className="font-medium">{formatPercent(subscriptionData?.avg_discount_rate || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">实例数:</span>
              <span className="font-medium">{subscriptionData?.instance_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">消费占比:</span>
              <span className="font-medium">{subscriptionData?.consumption_percentage?.toFixed(1) || 0}%</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>按量付费</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">消费金额:</span>
              <span className="font-medium">{formatCurrency(payAsYouGoData?.total_paid || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">折扣率:</span>
              <span className="font-medium">{formatPercent(payAsYouGoData?.avg_discount_rate || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">实例数:</span>
              <span className="font-medium">{payAsYouGoData?.instance_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">消费占比:</span>
              <span className="font-medium">{payAsYouGoData?.consumption_percentage?.toFixed(1) || 0}%</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 折扣率差异 */}
      <Card>
        <CardHeader>
          <CardTitle>折扣率对比</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground mb-2">包年包月折扣率优势</p>
            <p className="text-4xl font-bold text-primary">{formatPercent(rateDiff)}</p>
            <p className="text-sm text-muted-foreground mt-2">
              包年包月折扣率高出 {formatPercent(Math.abs(rateDiff))}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 优化建议列表 */}
      <Card>
        <CardHeader>
          <CardTitle>
            优化建议 ({suggestionsData.length}个实例 • 年节省 {formatCurrency(suggestions?.data?.total_potential_savings || 0)})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">实例ID</th>
                  <th className="text-left p-2">产品</th>
                  <th className="text-left p-2">区域</th>
                  <th className="text-right p-2">运行月数</th>
                  <th className="text-right p-2">总成本</th>
                  <th className="text-right p-2">当前折扣</th>
                  <th className="text-right p-2">预计折扣</th>
                  <th className="text-right p-2">年节省</th>
                </tr>
              </thead>
              <tbody>
                {suggestionsData.slice(0, 20).map((suggestion: any, idx: number) => (
                  <tr key={idx} className="border-b hover:bg-muted/50">
                    <td className="p-2 font-mono text-xs">{suggestion.instance_id.substring(0, 20)}...</td>
                    <td className="p-2">{suggestion.product_name}</td>
                    <td className="p-2">{suggestion.region_name}</td>
                    <td className="p-2 text-right">{suggestion.running_months}</td>
                    <td className="p-2 text-right">{formatCurrency(suggestion.total_cost)}</td>
                    <td className="p-2 text-right">{formatPercent(suggestion.current_discount_rate)}</td>
                    <td className="p-2 text-right text-green-600">{formatPercent(suggestion.estimated_subscription_rate)}</td>
                    <td className="p-2 text-right font-medium text-green-600">{formatCurrency(suggestion.annual_potential_savings)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  )
}

// ==================== Phase 2: Advanced Analysis Tab ====================

function AdvancedAnalysisTab({ currentAccount, formatCurrency, formatPercent }: any) {
  const [movingAvgData, setMovingAvgData] = useState<any>(null)
  const [cumulativeData, setCumulativeData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!currentAccount) return
    
    const fetchData = async () => {
      setLoading(true)
      try {
        const [movingAvg, cumulative] = await Promise.all([
          apiGet(`/discounts/moving-average?account=${currentAccount}&windows=3,6,12`),
          apiGet(`/discounts/cumulative?account=${currentAccount}`),
        ])
        setMovingAvgData(movingAvg)
        setCumulativeData(cumulative)
      } catch (err) {
        console.error("加载Phase 2数据失败:", err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [currentAccount])

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    )
  }

  // 准备移动平均数据
  const ma3Data = movingAvgData?.data?.moving_averages?.ma_3 || []
  const ma6Data = movingAvgData?.data?.moving_averages?.ma_6 || []
  const ma12Data = movingAvgData?.data?.moving_averages?.ma_12 || []
  
  // 合并数据
  const combinedMAData = ma3Data.map((item: any, idx: number) => ({
    month: item.month,
    original: item.original,
    ma_3: item.ma,
    ma_6: ma6Data[idx]?.ma,
    ma_12: ma12Data[idx]?.ma,
  }))

  const cumulativeChartData = cumulativeData?.data?.cumulative_data || []

  return (
    <>
      {/* 移动平均分析 */}
      <Card>
        <CardHeader>
          <CardTitle>折扣率移动平均（平滑趋势）</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={combinedMAData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={formatPercent} />
              <Tooltip formatter={(value: any) => formatPercent(value as number)} />
              <Legend />
              <Line type="monotone" dataKey="original" stroke="#ccc" strokeWidth={1} dot={false} name="原始数据" />
              <Line type="monotone" dataKey="ma_3" stroke="#8884d8" strokeWidth={2} dot={false} name="3月移动平均" />
              <Line type="monotone" dataKey="ma_6" stroke="#82ca9d" strokeWidth={2} dot={false} name="6月移动平均" />
              <Line type="monotone" dataKey="ma_12" stroke="#ffc658" strokeWidth={2} dot={false} name="12月移动平均" />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-4 text-sm text-muted-foreground">
            <p>💡 移动平均可以平滑短期波动，显示长期趋势：</p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>3月移动平均：反映短期趋势</li>
              <li>6月移动平均：反映中期趋势</li>
              <li>12月移动平均：反映长期趋势</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* 累计折扣曲线 */}
      <Card>
        <CardHeader>
          <CardTitle>累计折扣金额（爬升曲线）</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={cumulativeChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis yAxisId="left" tickFormatter={formatCurrency} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={formatCurrency} />
              <Tooltip />
              <Legend />
              <Area yAxisId="right" type="monotone" dataKey="cumulative_discount" fill="#8884d8" stroke="#8884d8" name="累计折扣" fillOpacity={0.6} />
              <Bar yAxisId="left" dataKey="monthly_discount" fill="#82ca9d" name="月度折扣" />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">累计总折扣</p>
              <p className="text-2xl font-bold text-primary">{formatCurrency(cumulativeData?.data?.total_discount || 0)}</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">月均折扣</p>
              <p className="text-2xl font-bold text-primary">
                {formatCurrency((cumulativeData?.data?.total_discount || 0) / (cumulativeChartData.length || 1))}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Phase 2 洞察 */}
      <Card>
        <CardHeader>
          <CardTitle>Phase 2 高级洞察</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <p>• <strong>趋势平滑:</strong> 12月移动平均显示折扣率整体{ma12Data[ma12Data.length-1]?.ma > ma12Data[0]?.ma ? '上升' : '下降'}趋势</p>
            <p>• <strong>累计节省:</strong> 19个月累计节省{formatCurrency(cumulativeData?.data?.total_discount || 0)}，月均{formatCurrency((cumulativeData?.data?.total_discount || 0) / 19)}</p>
            <p>• <strong>数据洞察:</strong> Phase 2提供更深入的趋势分析和数据可视化</p>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
