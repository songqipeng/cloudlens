"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { CostTrendChart } from "@/components/cost-trend-chart"
import { CostDateRangeSelector, CostDateRange } from "@/components/cost-date-range-selector"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"
import { RabbitLoading } from "@/components/loading"
import { Download, RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react"
import { Button } from "@/components/ui/button"

type Granularity = 'daily' | 'monthly'
type ChartType = 'area' | 'line' | 'bar' | 'stacked'

export default function CostTrendPage() {
    const { currentAccount } = useAccount()
    const { t, locale } = useLocale()
    const [loading, setLoading] = useState(true)
    const [granularity, setGranularity] = useState<Granularity>('daily')
    const [chartType, setChartType] = useState<ChartType>('area')
    const [showBreakdown, setShowBreakdown] = useState(false)
    const [dateRange, setDateRange] = useState<CostDateRange>({ startDate: null, endDate: null })
    const [days, setDays] = useState(30)
    const [summary, setSummary] = useState<any>(null)

    // 获取统计数据
    useEffect(() => {
        if (!currentAccount) {
            setLoading(false)
            return
        }

        async function loadSummary() {
            try {
                setLoading(true)
                const params: any = { account: currentAccount, granularity }
                
                if (dateRange.startDate && dateRange.endDate) {
                    params.start_date = dateRange.startDate
                    params.end_date = dateRange.endDate
                } else if (granularity === 'daily') {
                    params.days = days
                }

                const result = await apiGet('/dashboard/trend', params)
                if (result?.summary) {
                    setSummary(result.summary)
                }
            } catch (e) {
                console.error("Failed to fetch summary:", e)
            } finally {
                setLoading(false)
            }
        }

        loadSummary()
    }, [currentAccount, granularity, days, dateRange])

    // 处理日期范围变化
    const handleDateRangeChange = (range: CostDateRange) => {
        setDateRange(range)
        // 根据日期范围推断days
        if (range.startDate && range.endDate) {
            const start = new Date(range.startDate)
            const end = new Date(range.endDate)
            const diffDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
            setDays(diffDays)
        } else if (!range.startDate && !range.endDate) {
            setDays(0)  // 全部
        }
    }

    // 处理视图切换
    const handleGranularityChange = (gran: Granularity) => {
        setGranularity(gran)
        // 切换视图时，重置图表类型
        if (gran === 'daily') {
            setChartType('area')
        } else {
            setChartType('bar')
        }
    }

    // 处理图表类型切换
    const handleChartTypeChange = (type: ChartType) => {
        setChartType(type)
    }

    // 导出功能
    const handleExport = async (format: 'csv' | 'excel') => {
        if (!currentAccount) return
        
        try {
            const params: any = { account: currentAccount, granularity, format }
            
            if (dateRange.startDate && dateRange.endDate) {
                params.start_date = dateRange.startDate
                params.end_date = dateRange.endDate
            } else if (granularity === 'daily') {
                params.days = days
            }

            const response = await fetch(
                `/api/cost/export?${new URLSearchParams(params)}`,
                { method: 'GET' }
            )
            
            if (response.ok) {
                const blob = await response.blob()
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `cost-trend-${new Date().toISOString().split('T')[0]}.${format === 'csv' ? 'csv' : 'xlsx'}`
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                window.URL.revokeObjectURL(url)
            }
        } catch (e) {
            console.error("Export failed:", e)
        }
    }

    // 刷新数据
    const handleRefresh = () => {
        if (!currentAccount) return
        setLoading(true)
        // 重新触发数据加载
        const params: any = { account: currentAccount, granularity }
        if (dateRange.startDate && dateRange.endDate) {
            params.start_date = dateRange.startDate
            params.end_date = dateRange.endDate
        } else if (granularity === 'daily') {
            params.days = days
        }
        apiGet('/dashboard/trend', params).then(result => {
            if (result?.summary) {
                setSummary(result.summary)
            }
            setLoading(false)
        }).catch(e => {
            console.error("Failed to refresh:", e)
            setLoading(false)
        })
    }

    // 获取趋势图标和颜色
    const getTrendInfo = () => {
        if (!summary) return { icon: Minus, color: 'text-muted-foreground', text: locale === 'zh' ? '平稳' : 'Stable' }
        const trend = summary.trend || ''
        const isUp = trend.includes('上升') || trend.includes('Up') || trend.includes('↑')
        const isDown = trend.includes('下降') || trend.includes('Down') || trend.includes('↓')
        
        if (isUp) {
            return { icon: TrendingUp, color: 'text-red-500', text: locale === 'zh' ? '上升' : 'Up' }
        } else if (isDown) {
            return { icon: TrendingDown, color: 'text-green-500', text: locale === 'zh' ? '下降' : 'Down' }
        } else {
            return { icon: Minus, color: 'text-muted-foreground', text: locale === 'zh' ? '平稳' : 'Stable' }
        }
    }

    const trendInfo = getTrendInfo()
    const TrendIcon = trendInfo.icon

    if (loading && !summary) {
        return (
            <DashboardLayout>
                <RabbitLoading />
            </DashboardLayout>
        )
    }

    return (
        <DashboardLayout>
            <div className="space-y-6">
                {/* 页面标题 - 按照设计文档 */}
                <div>
                    <h1 className="text-3xl font-bold">📊 {locale === 'zh' ? '成本趋势分析' : 'Cost Trend Analysis'}</h1>
                    <p className="text-muted-foreground mt-2">
                        {locale === 'zh' ? '查看和管理所有云资源的成本趋势' : 'View and manage cost trends for all cloud resources'}
                    </p>
                </div>

                {/* 控制面板 - 按照设计文档布局 */}
                <Card className="glass border border-border/50 shadow-xl">
                    <CardContent className="pt-6">
                        <div className="space-y-4">
                            {/* 时间范围选择 */}
                            <div>
                                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                                    {locale === 'zh' ? '时间范围' : 'Time Range'}
                                </label>
                                <CostDateRangeSelector onChange={handleDateRangeChange} />
                            </div>

                            {/* 视图切换和图表类型 - 并排显示 */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* 视图切换 */}
                                <div>
                                    <label className="text-sm font-medium text-muted-foreground mb-2 block">
                                        {locale === 'zh' ? '视图切换' : 'View Toggle'}
                                    </label>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleGranularityChange('daily')}
                                            className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                granularity === 'daily'
                                                    ? 'bg-primary text-primary-foreground shadow-md shadow-primary/20'
                                                    : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                                            }`}
                                        >
                                            📈 {locale === 'zh' ? '按天' : 'Daily'}
                                        </button>
                                        <button
                                            onClick={() => handleGranularityChange('monthly')}
                                            className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                granularity === 'monthly'
                                                    ? 'bg-primary text-primary-foreground shadow-md shadow-primary/20'
                                                    : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                                            }`}
                                        >
                                            📊 {locale === 'zh' ? '按月' : 'Monthly'}
                                        </button>
                                    </div>
                                </div>

                                {/* 图表类型选择 */}
                                <div>
                                    <label className="text-sm font-medium text-muted-foreground mb-2 block">
                                        {locale === 'zh' ? '图表类型' : 'Chart Type'}
                                    </label>
                                    <div className="flex gap-2 flex-wrap">
                                        {granularity === 'daily' ? (
                                            <>
                                                <button
                                                    onClick={() => handleChartTypeChange('area')}
                                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                        chartType === 'area'
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                                                    }`}
                                                >
                                                    {locale === 'zh' ? '面积图' : 'Area'}
                                                </button>
                                                <button
                                                    onClick={() => handleChartTypeChange('line')}
                                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                        chartType === 'line'
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                                                    }`}
                                                >
                                                    {locale === 'zh' ? '折线图' : 'Line'}
                                                </button>
                                                <button
                                                    onClick={() => handleChartTypeChange('stacked')}
                                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                        chartType === 'stacked'
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                                                    }`}
                                                >
                                                    {locale === 'zh' ? '堆叠' : 'Stacked'}
                                                </button>
                                            </>
                                        ) : (
                                            <>
                                                <button
                                                    onClick={() => handleChartTypeChange('bar')}
                                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                        chartType === 'bar'
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                                                    }`}
                                                >
                                                    {locale === 'zh' ? '柱状图' : 'Bar'}
                                                </button>
                                                <button
                                                    onClick={() => handleChartTypeChange('line')}
                                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                        chartType === 'line'
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                                                    }`}
                                                >
                                                    {locale === 'zh' ? '折线图' : 'Line'}
                                                </button>
                                                <button
                                                    onClick={() => handleChartTypeChange('stacked')}
                                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                                                        chartType === 'stacked'
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                                                    }`}
                                                >
                                                    {locale === 'zh' ? '堆叠' : 'Stacked'}
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* 显示选项 */}
                            <div>
                                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                                    {locale === 'zh' ? '显示选项' : 'Display Options'}
                                </label>
                                <div className="flex items-center gap-4">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={showBreakdown}
                                            onChange={(e) => setShowBreakdown(e.target.checked)}
                                            className="rounded border-border"
                                        />
                                        <span className="text-sm text-muted-foreground">
                                            {locale === 'zh' ? '显示资源类型分解' : 'Show Resource Type Breakdown'}
                                        </span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* 成本趋势图表区域 - 按照设计文档 */}
                {currentAccount && (
                    <Card className="glass border border-border/50 shadow-xl">
                        <CardHeader>
                            <CardTitle className="text-xl font-semibold">
                                {locale === 'zh' ? '成本趋势' : 'Cost Trend'}
                            </CardTitle>
                            <CardDescription>
                                {granularity === 'daily' 
                                    ? (locale === 'zh' ? `最近${days || 30}天成本趋势` : `Cost trend for the last ${days || 30} days`)
                                    : (locale === 'zh' ? '从有数据以来的月度成本趋势' : 'Monthly cost trend since data available')
                                }
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <CostTrendChart
                                account={currentAccount}
                                granularity={granularity}
                                days={days}
                                startDate={dateRange.startDate || undefined}
                                endDate={dateRange.endDate || undefined}
                                chartType={chartType}
                                showBreakdown={showBreakdown}
                            />
                        </CardContent>
                    </Card>
                )}

                {/* 统计摘要卡片 - 按照设计文档 */}
                {summary && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                        <Card className="glass border border-border/50 shadow-xl">
                            <CardContent className="pt-6">
                                <div className="text-sm text-muted-foreground mb-2">
                                    {locale === 'zh' ? '总成本' : 'Total Cost'}
                                </div>
                                <div className="text-2xl font-bold">
                                    ¥{summary.total_cost?.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) || '0'}
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="glass border border-border/50 shadow-xl">
                            <CardContent className="pt-6">
                                <div className="text-sm text-muted-foreground mb-2">
                                    {granularity === 'daily' 
                                        ? (locale === 'zh' ? '日均成本' : 'Avg Daily Cost')
                                        : (locale === 'zh' ? '月均成本' : 'Avg Monthly Cost')
                                    }
                                </div>
                                <div className="text-2xl font-bold">
                                    ¥{(granularity === 'daily' ? summary.avg_daily_cost : summary.avg_monthly_cost)?.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) || '0'}
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="glass border border-border/50 shadow-xl">
                            <CardContent className="pt-6">
                                <div className="text-sm text-muted-foreground mb-2">
                                    {granularity === 'daily' 
                                        ? (locale === 'zh' ? '最高日成本' : 'Max Daily Cost')
                                        : (locale === 'zh' ? '最高月成本' : 'Max Monthly Cost')
                                    }
                                </div>
                                <div className="text-2xl font-bold">
                                    ¥{(granularity === 'daily' ? summary.max_daily_cost : summary.max_monthly_cost)?.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) || '0'}
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="glass border border-border/50 shadow-xl">
                            <CardContent className="pt-6">
                                <div className="text-sm text-muted-foreground mb-2">
                                    {granularity === 'daily' 
                                        ? (locale === 'zh' ? '最低日成本' : 'Min Daily Cost')
                                        : (locale === 'zh' ? '最低月成本' : 'Min Monthly Cost')
                                    }
                                </div>
                                <div className="text-2xl font-bold">
                                    ¥{(granularity === 'daily' ? summary.min_daily_cost : summary.min_monthly_cost)?.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) || '0'}
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="glass border border-border/50 shadow-xl">
                            <CardContent className="pt-6">
                                <div className="text-sm text-muted-foreground mb-2">
                                    {locale === 'zh' ? '趋势' : 'Trend'}
                                </div>
                                <div className={`text-2xl font-bold flex items-center gap-2 ${trendInfo.color}`}>
                                    <TrendIcon className="w-6 h-6" />
                                    {summary.trend_pct?.toFixed(1) || '0.0'}%
                                </div>
                                <div className={`text-xs mt-1 ${trendInfo.color}`}>
                                    {trendInfo.text}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* 操作按钮 - 按照设计文档 */}
                <Card className="glass border border-border/50 shadow-xl">
                    <CardContent className="pt-6">
                        <div className="flex gap-2 flex-wrap">
                            <Button
                                variant="outline"
                                onClick={() => handleExport('csv')}
                                className="flex items-center gap-2"
                            >
                                <Download className="w-4 h-4" />
                                {locale === 'zh' ? '导出CSV' : 'Export CSV'}
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => handleExport('excel')}
                                className="flex items-center gap-2"
                            >
                                <Download className="w-4 h-4" />
                                {locale === 'zh' ? '导出Excel' : 'Export Excel'}
                            </Button>
                            <Button
                                variant="outline"
                                onClick={handleRefresh}
                                className="flex items-center gap-2"
                            >
                                <RefreshCw className="w-4 h-4" />
                                {locale === 'zh' ? '刷新数据' : 'Refresh Data'}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    )
}
