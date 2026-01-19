"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DateRangeSelector, DateRange } from "@/components/discount/DateRangeSelector"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
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
  const { t } = useLocale()
  const [activeTab, setActiveTab] = useState("overview")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // 时间范围状态
  const [dateRange, setDateRange] = useState<DateRange>({ startDate: null, endDate: null })
  
  // Data states for different analyses
  const [quarterlyData, setQuarterlyData] = useState<QuarterlyResponse | null>(null)
  const [yearlyData, setYearlyData] = useState<YearlyResponse | null>(null)
  const [productTrends, setProductTrends] = useState<ProductTrendsResponse | null>(null)
  const [regionsData, setRegionsData] = useState<RegionsResponse | null>(null)
  const [subscriptionData, setSubscriptionData] = useState<SubscriptionTypesResponse | null>(null)
  const [suggestions, setSuggestions] = useState<OptimizationSuggestionsResponse | null>(null)
  const [anomalies, setAnomaliesData] = useState<AnomaliesResponse | null>(null)
  const [insights, setInsights] = useState<any>(null)

  // 构建时间范围查询参数
  const getDateRangeParams = () => {
    let params = ''
    if (dateRange.startDate) {
      params += `&start_date=${dateRange.startDate}`
    }
    if (dateRange.endDate) {
      params += `&end_date=${dateRange.endDate}`
    }
    return params
  }

  const fetchAllData = async (forceRefresh = false) => {
    if (!currentAccount) return
    
    setLoading(true)
    setError(null)
    
    const dateParams = getDateRangeParams()
    const baseApiOptions = { timeout: 30000, retries: 1 } as any // 降低超时时间，更快失败
    
    // 定义所有API调用，每个都独立处理错误
    const apiCalls = {
      quarterly: () => apiGet<QuarterlyResponse>(`/discounts/quarterly?account=${currentAccount}&quarters=8${dateParams}`, {}, baseApiOptions),
      yearly: () => apiGet<YearlyResponse>(`/discounts/yearly?account=${currentAccount}${dateParams}`, {}, baseApiOptions),
      products: () => apiGet<ProductTrendsResponse>(`/discounts/product-trends?account=${currentAccount}&months=19&top_n=10${dateParams}`, {}, baseApiOptions),
      regions: () => apiGet<RegionsResponse>(`/discounts/regions?account=${currentAccount}${dateParams}`, {}, baseApiOptions),
      subscription: () => apiGet<SubscriptionTypesResponse>(`/discounts/subscription-types?account=${currentAccount}${dateParams}`, {}, baseApiOptions),
      opts: () => apiGet<OptimizationSuggestionsResponse>(`/discounts/optimization-suggestions?account=${currentAccount}${dateParams}`, {}, baseApiOptions),
      anom: () => apiGet<AnomaliesResponse>(`/discounts/anomalies?account=${currentAccount}&threshold=0.10${dateParams}`, {}, baseApiOptions),
      insights: () => apiGet(`/discounts/insights?account=${currentAccount}${dateParams}`, {}, { timeout: 20000, retries: 0 } as any),
    }
    
    // 使用 Promise.allSettled 让每个API独立加载，互不阻塞
    const results = await Promise.allSettled([
      apiCalls.quarterly(),
      apiCalls.yearly(),
      apiCalls.products(),
      apiCalls.regions(),
      apiCalls.subscription(),
      apiCalls.opts(),
      apiCalls.anom(),
      apiCalls.insights(),
    ])
    
    // 处理每个结果，成功则设置数据，失败则记录错误但不阻塞其他数据
    const [quarterlyResult, yearlyResult, productsResult, regionsResult, subscriptionResult, optsResult, anomResult, insightsResult] = results
    
    // 处理季度数据
    if (quarterlyResult.status === 'fulfilled') {
      setQuarterlyData(quarterlyResult.value)
    } else {
      console.warn("季度数据加载失败:", quarterlyResult.reason)
    }
    
    // 处理年度数据
    if (yearlyResult.status === 'fulfilled') {
      setYearlyData(yearlyResult.value)
    } else {
      console.warn("年度数据加载失败:", yearlyResult.reason)
    }
    
    // 处理产品趋势数据
    if (productsResult.status === 'fulfilled') {
      setProductTrends(productsResult.value)
    } else {
      console.warn("产品趋势数据加载失败:", productsResult.reason)
      // 如果产品趋势失败，设置一个空数据避免UI错误
      setProductTrends({ success: false, data: { products: [] } } as any)
    }
    
    // 处理区域数据
    if (regionsResult.status === 'fulfilled') {
      setRegionsData(regionsResult.value)
    } else {
      console.warn("区域数据加载失败:", regionsResult.reason)
    }
    
    // 处理订阅类型数据
    if (subscriptionResult.status === 'fulfilled') {
      setSubscriptionData(subscriptionResult.value)
    } else {
      console.warn("订阅类型数据加载失败:", subscriptionResult.reason)
    }
    
    // 处理优化建议数据
    if (optsResult.status === 'fulfilled') {
      setSuggestions(optsResult.value)
    } else {
      console.warn("优化建议数据加载失败:", optsResult.reason)
    }
    
    // 处理异常数据
    if (anomResult.status === 'fulfilled') {
      setAnomaliesData(anomResult.value)
    } else {
      console.warn("异常数据加载失败:", anomResult.reason)
    }
    
    // 处理Insights数据
    if (insightsResult.status === 'fulfilled') {
      setInsights(insightsResult.value)
    } else {
      console.warn("Insights数据加载失败:", insightsResult.reason)
      setInsights(null)
    }
    
    // 检查是否有任何数据加载成功
    const hasAnyData = quarterlyResult.status === 'fulfilled' || 
                      yearlyResult.status === 'fulfilled' || 
                      productsResult.status === 'fulfilled' ||
                      regionsResult.status === 'fulfilled'
    
    if (!hasAnyData) {
      // 如果所有核心数据都失败了，显示错误
      const firstError = results.find(r => r.status === 'rejected')
      if (firstError && firstError.status === 'rejected') {
        setError(firstError.reason?.message || t.discountAdvanced.loadFailed)
      } else {
        setError(t.discountAdvanced.loadFailed)
      }
    } else {
      // 至少有一些数据加载成功，清除错误
      setError(null)
    }
    
    setLoading(false)
  }

  const handleExport = (exportType: string) => {
    const dateParams = getDateRangeParams()
    window.open(`http://localhost:8000/api/discounts/export?account=${currentAccount}&export_type=${exportType}${dateParams}`, '_blank')
  }

  // 当账号或时间范围改变时，重新加载数据
  useEffect(() => {
    fetchAllData()
  }, [currentAccount, dateRange])

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
            <p className="text-muted-foreground">{t.discountAdvanced.loading}</p>
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
              <p className="font-semibold">{t.discountAdvanced.loadFailed}</p>
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
            <h2 className="text-3xl font-bold tracking-tight">{t.discountAdvanced.title}</h2>
            <p className="text-muted-foreground mt-1">
              {t.discountAdvanced.description}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => handleExport('all')}
              variant="outline"
              size="sm"
            >
              <DollarSign className="mr-2 h-4 w-4" />
              {t.discountAdvanced.exportExcel}
            </Button>
            <Button
              onClick={() => fetchAllData(true)}
              disabled={loading}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {t.discountAdvanced.refresh}
            </Button>
          </div>
        </div>

        {/* 时间范围选择器 */}
        <Card>
          <CardContent className="pt-6">
            <DateRangeSelector
              onChange={(range) => setDateRange(range)}
              className="w-full"
            />
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="overview">{t.discountAdvanced.tabs.overview}</TabsTrigger>
            <TabsTrigger value="time">{t.discountAdvanced.tabs.timeAnalysis}</TabsTrigger>
            <TabsTrigger value="products">{t.discountAdvanced.tabs.productAnalysis}</TabsTrigger>
            <TabsTrigger value="regions">{t.discountAdvanced.tabs.regionAnalysis}</TabsTrigger>
            <TabsTrigger value="billing">{t.discountAdvanced.tabs.billingAnalysis}</TabsTrigger>
            <TabsTrigger value="advanced">{t.discountAdvanced.tabs.advancedAnalysis}</TabsTrigger>
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
              insights={insights}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
              t={t}
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
              t={t}
            />
          </TabsContent>

          {/* Tab 3: Product Analysis */}
          <TabsContent value="products" className="space-y-6">
            <ProductAnalysisTab
              products={productTrends}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
              t={t}
            />
          </TabsContent>

          {/* Tab 4: Region Analysis */}
          <TabsContent value="regions" className="space-y-6">
            <RegionAnalysisTab
              regions={regionsData}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
              t={t}
            />
          </TabsContent>

          {/* Tab 5: Billing Analysis */}
          <TabsContent value="billing" className="space-y-6">
            <BillingAnalysisTab
              subscription={subscriptionData}
              suggestions={suggestions}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
              t={t}
            />
          </TabsContent>

          {/* Tab 6: Advanced Analysis (Phase 2) */}
          <TabsContent value="advanced" className="space-y-6">
            <AdvancedAnalysisTab
              currentAccount={currentAccount}
              formatCurrency={formatCurrency}
              formatPercent={formatPercent}
              t={t}
            />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}

// ==================== Tab Components ====================

function OverviewTab({ quarterly, yearly, products, regions, subscription, suggestions, anomalies, insights, formatCurrency, formatPercent, t }: any) {
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
            <CardTitle className="text-sm font-medium">{t.discountAdvanced.overview.latestQuarterDiscount}</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercent(latestQuarter?.avg_discount_rate || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {latestQuarter?.period} • {latestQuarter?.month_count}{t.discountAdvanced.overview.months}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t.discountAdvanced.overview.quarterTotalSavings}</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(latestQuarter?.total_discount || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {t.discountAdvanced.overview.momChange} {latestQuarter?.rate_change > 0 ? '+' : ''}{latestQuarter?.rate_change?.toFixed(1)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t.discountAdvanced.overview.optimizationOpportunities}</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{suggestions?.data?.total_suggestions || 0}{t.discountAdvanced.overview.instances}</div>
            <p className="text-xs text-muted-foreground">
              {t.discountAdvanced.overview.yearSavings} {formatCurrency(suggestions?.data?.total_potential_savings || 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t.discountAdvanced.overview.anomalyDetection}</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{anomalies?.data?.total_anomalies || 0}{t.discountAdvanced.overview.monthsUnit}</div>
            <p className="text-xs text-muted-foreground">
              {t.discountAdvanced.overview.fluctuation} {'>'}10%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* 季度趋势 */}
        <Card>
          <CardHeader>
            <CardTitle>{t.discountAdvanced.overview.quarterlyTrend}</CardTitle>
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
                <Bar yAxisId="left" dataKey="total_discount" fill="#8884d8" name={t.discountAdvanced.overview.discountAmount} />
                <Line yAxisId="right" type="monotone" dataKey="avg_discount_rate" stroke="#82ca9d" name={t.discountAdvanced.overview.discountRate} />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* TOP产品 */}
        <Card>
          <CardHeader>
            <CardTitle>{t.discountAdvanced.overview.top5ProductDiscount}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topProducts} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={formatPercent} />
                <YAxis dataKey="product_name" type="category" width={120} />
                <Tooltip formatter={(value: any) => formatPercent(value as number)} />
                <Bar dataKey="avg_discount_rate" fill="#8884d8" name={t.discountAdvanced.overview.avgDiscountRate} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* 智能洞察 (Phase 3) */}
      <Card>
        <CardHeader>
          <CardTitle>{t.discountAdvanced.overview.aiInsights}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {insights?.data?.insights?.map((insight: any, idx: number) => {
              // 根据类型确定颜色主题
              const getColorTheme = () => {
                if (insight.level === 'success') {
                  return {
                    border: 'border-green-500/50',
                    labelBg: 'bg-green-500/20',
                    labelText: 'text-green-400',
                    accent: 'text-green-400'
                  }
                }
                if (insight.level === 'warning') {
                  return {
                    border: 'border-yellow-500/50',
                    labelBg: 'bg-yellow-500/20',
                    labelText: 'text-yellow-400',
                    accent: 'text-yellow-400'
                  }
                }
                return {
                  border: 'border-blue-500/50',
                  labelBg: 'bg-blue-500/20',
                  labelText: 'text-blue-400',
                  accent: 'text-blue-400'
                }
              }
              const theme = getColorTheme()
              
              return (
                <div
                  key={idx}
                  className={`p-4 rounded-lg border ${theme.border} bg-[rgba(15,15,20,0.6)] backdrop-blur-[10px] hover:bg-[rgba(15,15,20,0.8)] transition-colors`}
                >
                  <div className="flex items-start gap-3">
                    <span className={`text-xs px-2.5 py-1 rounded-full ${theme.labelBg} ${theme.labelText} font-semibold border ${theme.border} shrink-0`}>
                      {insight.category}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-white text-[15px] leading-tight mb-2">{insight.title}</p>
                      <p className="text-sm text-gray-300 leading-relaxed mb-2">{insight.description}</p>
                      <p className="text-sm text-gray-400 flex items-start gap-1.5">
                        <span className={theme.accent}>💡</span>
                        <span>{insight.recommendation}</span>
                      </p>
                    </div>
                  </div>
                </div>
              )
            })}
            {(!insights || !insights.data?.insights?.length) && (
              <div className="text-sm text-muted-foreground">
                <p>{t.discountAdvanced.overview.generatingInsights}</p>
                <p className="mt-2 text-xs text-muted-foreground/70">
                  {insights === null ? "（Insights数据加载超时，其他数据已正常加载）" : ""}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  )
}

function TimeAnalysisTab({ quarterly, yearly, anomalies, formatCurrency, formatPercent, t }: any) {
  return (
    <>
      {/* 季度对比 */}
      <Card>
        <CardHeader>
          <CardTitle>{t.discountAdvanced.timeAnalysis.quarterComparison}</CardTitle>
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
              <Bar yAxisId="left" dataKey="total_paid" fill="#8884d8" name={t.discountAdvanced.timeAnalysis.paidAmount} />
              <Bar yAxisId="left" dataKey="total_discount" fill="#82ca9d" name={t.discountAdvanced.overview.discountAmount} />
              <Line yAxisId="right" type="monotone" dataKey="avg_discount_rate" stroke="#ff7300" name={t.discountAdvanced.overview.discountRate} strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 年度对比 */}
      <Card>
        <CardHeader>
          <CardTitle>{t.discountAdvanced.timeAnalysis.yearlyComparison}</CardTitle>
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
              <Bar yAxisId="left" dataKey="total_paid" fill="#8884d8" name={t.discountAdvanced.timeAnalysis.paidAmount} />
              <Bar yAxisId="left" dataKey="total_discount" fill="#82ca9d" name={t.discountAdvanced.overview.discountAmount} />
              <Line yAxisId="right" type="monotone" dataKey="avg_discount_rate" stroke="#ff7300" name={t.discountAdvanced.overview.discountRate} strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 异常检测 */}
      {anomalies?.data?.anomalies && anomalies.data.anomalies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t.discountAdvanced.timeAnalysis.discountAnomaly}</CardTitle>
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

function ProductAnalysisTab({ products, formatCurrency, formatPercent, t }: any) {
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
          <CardTitle>{t.discountAdvanced.productAnalysis.selectProducts}</CardTitle>
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
          <CardTitle>{t.discountAdvanced.productAnalysis.productTrendComparison}</CardTitle>
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
          <CardTitle>{t.discountAdvanced.productAnalysis.productRanking}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">{t.discountAdvanced.productAnalysis.productName}</th>
                  <th className="text-right p-2">{t.discountAdvanced.productAnalysis.totalConsumption}</th>
                  <th className="text-right p-2">{t.discountAdvanced.productAnalysis.totalDiscount}</th>
                  <th className="text-right p-2">{t.discountAdvanced.overview.avgDiscountRate}</th>
                  <th className="text-right p-2">{t.discountAdvanced.productAnalysis.volatility}</th>
                  <th className="text-right p-2">{t.discountAdvanced.productAnalysis.trend}</th>
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

function RegionAnalysisTab({ regions, formatCurrency, formatPercent, t }: any) {
  const regionsData = regions?.data?.regions || []

  return (
    <>
      {/* 区域折扣排行 */}
      <Card>
        <CardHeader>
          <CardTitle>{t.discountAdvanced.regionAnalysis.regionRanking}</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={regionsData.slice(0, 10)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={formatPercent} />
              <YAxis dataKey="region_name" type="category" width={150} />
              <Tooltip formatter={(value: any) => formatPercent(value as number)} />
              <Bar dataKey="avg_discount_rate" fill="#8884d8" name={t.discountAdvanced.overview.avgDiscountRate} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 区域详细表 */}
      <Card>
        <CardHeader>
          <CardTitle>{t.discountAdvanced.regionAnalysis.regionDetails}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">{t.discountAdvanced.regionAnalysis.region}</th>
                  <th className="text-right p-2">{t.discountAdvanced.regionAnalysis.consumptionAmount}</th>
                  <th className="text-right p-2">{t.discountAdvanced.overview.discountAmount}</th>
                  <th className="text-right p-2">{t.discountAdvanced.overview.discountRate}</th>
                  <th className="text-right p-2">{t.discountAdvanced.regionAnalysis.instanceCount}</th>
                  <th className="text-right p-2">{t.discountAdvanced.regionAnalysis.productCount}</th>
                  <th className="text-right p-2">{t.discountAdvanced.regionAnalysis.percentage}</th>
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

function BillingAnalysisTab({ subscription, suggestions, formatCurrency, formatPercent, t }: any) {
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
            <CardTitle>{t.discounts.subscription}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.billingAnalysis.consumptionAmount}:</span>
              <span className="font-medium">{formatCurrency(subscriptionData?.total_paid || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.overview.discountRate}:</span>
              <span className="font-medium">{formatPercent(subscriptionData?.avg_discount_rate || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.regionAnalysis.instanceCount}:</span>
              <span className="font-medium">{subscriptionData?.instance_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.billingAnalysis.consumptionPercentage}:</span>
              <span className="font-medium">{subscriptionData?.consumption_percentage?.toFixed(1) || 0}%</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t.discounts.payAsYouGo}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.billingAnalysis.consumptionAmount}:</span>
              <span className="font-medium">{formatCurrency(payAsYouGoData?.total_paid || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.overview.discountRate}:</span>
              <span className="font-medium">{formatPercent(payAsYouGoData?.avg_discount_rate || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.regionAnalysis.instanceCount}:</span>
              <span className="font-medium">{payAsYouGoData?.instance_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">{t.discountAdvanced.billingAnalysis.consumptionPercentage}:</span>
              <span className="font-medium">{payAsYouGoData?.consumption_percentage?.toFixed(1) || 0}%</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 折扣率差异 */}
      <Card>
        <CardHeader>
          <CardTitle>{t.discountAdvanced.billingAnalysis.discountRateComparison}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground mb-2">{t.discountAdvanced.billingAnalysis.subscriptionAdvantage}</p>
            <p className="text-4xl font-bold text-primary">{formatPercent(rateDiff)}</p>
            <p className="text-sm text-muted-foreground mt-2">
              {t.discountAdvanced.billingAnalysis.subscriptionHigher} {formatPercent(Math.abs(rateDiff))}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 优化建议列表 */}
      <Card>
        <CardHeader>
          <CardTitle>
            {t.discountAdvanced.billingAnalysis.optimizationSuggestions} ({suggestionsData.length}{t.discountAdvanced.overview.instances} • {t.discountAdvanced.overview.yearSavings} {formatCurrency(suggestions?.data?.total_potential_savings || 0)})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">{t.discountAdvanced.billingAnalysis.instanceId}</th>
                  <th className="text-left p-2">{t.discounts.product}</th>
                  <th className="text-left p-2">{t.discountAdvanced.regionAnalysis.region}</th>
                  <th className="text-right p-2">{t.discountAdvanced.billingAnalysis.runningMonths}</th>
                  <th className="text-right p-2">{t.discountAdvanced.billingAnalysis.totalCost}</th>
                  <th className="text-right p-2">{t.discountAdvanced.billingAnalysis.currentDiscount}</th>
                  <th className="text-right p-2">{t.discountAdvanced.billingAnalysis.estimatedDiscount}</th>
                  <th className="text-right p-2">{t.discountAdvanced.billingAnalysis.annualSavings}</th>
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

function AdvancedAnalysisTab({ currentAccount, formatCurrency, formatPercent, t }: any) {
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
        console.error("Failed to load Phase 2 data:", err)
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
          <CardTitle>{t.discountAdvanced.advanced.movingAverage}</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={combinedMAData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={formatPercent} />
              <Tooltip formatter={(value: any) => formatPercent(value as number)} />
              <Legend />
              <Line type="monotone" dataKey="original" stroke="#ccc" strokeWidth={1} dot={false} name={t.discountAdvanced.advanced.originalData} />
              <Line type="monotone" dataKey="ma_3" stroke="#8884d8" strokeWidth={2} dot={false} name={`3${t.discountAdvanced.advanced.monthMovingAverage}`} />
              <Line type="monotone" dataKey="ma_6" stroke="#82ca9d" strokeWidth={2} dot={false} name={`6${t.discountAdvanced.advanced.monthMovingAverage}`} />
              <Line type="monotone" dataKey="ma_12" stroke="#ffc658" strokeWidth={2} dot={false} name={`12${t.discountAdvanced.advanced.monthMovingAverage}`} />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-4 text-sm text-muted-foreground">
            <p>💡 {t.discountAdvanced.advanced.movingAverageDesc}</p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>{t.discountAdvanced.advanced.threeMonthDesc}</li>
              <li>{t.discountAdvanced.advanced.sixMonthDesc}</li>
              <li>{t.discountAdvanced.advanced.twelveMonthDesc}</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* 累计折扣曲线 */}
      <Card>
        <CardHeader>
          <CardTitle>{t.discountAdvanced.advanced.cumulativeDiscount}</CardTitle>
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
              <Area yAxisId="right" type="monotone" dataKey="cumulative_discount" fill="#8884d8" stroke="#8884d8" name={t.discountAdvanced.advanced.cumulativeDiscountAmount} fillOpacity={0.6} />
              <Bar yAxisId="left" dataKey="monthly_discount" fill="#82ca9d" name={t.discountAdvanced.advanced.monthlyDiscount} />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">{t.discountAdvanced.advanced.cumulativeTotal}</p>
              <p className="text-2xl font-bold text-primary">{formatCurrency(cumulativeData?.data?.total_discount || 0)}</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">{t.discountAdvanced.advanced.monthlyAverage}</p>
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
          <CardTitle>{t.discountAdvanced.advanced.phase2Insights}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <p>• <strong>{t.discountAdvanced.advanced.trendSmoothing}:</strong> 12{t.discountAdvanced.advanced.monthMovingAverage} {t.discountAdvanced.advanced.trendDesc} {ma12Data[ma12Data.length-1]?.ma > ma12Data[0]?.ma ? t.discountAdvanced.advanced.rising : t.discountAdvanced.advanced.falling} {t.discountAdvanced.advanced.trend}</p>
            <p>• <strong>{t.discountAdvanced.advanced.cumulativeSavings}:</strong> 19{t.discountAdvanced.overview.months} {t.discountAdvanced.advanced.cumulativeSavingsDesc} {formatCurrency(cumulativeData?.data?.total_discount || 0)}，{t.discountAdvanced.advanced.monthlyAverage} {formatCurrency((cumulativeData?.data?.total_discount || 0) / 19)}</p>
            <p>• <strong>{t.discountAdvanced.advanced.dataInsights}:</strong> {t.discountAdvanced.advanced.dataInsightsDesc}</p>
          </div>
        </CardContent>
      </Card>
    </>
  )
}



