"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiGet } from "@/lib/api"
import { CostDateRangeSelector, CostDateRange } from "@/components/cost-date-range-selector"
import { useLocale } from "@/contexts/locale-context"

interface ChartData {
    dates: string[]
    costs: number[]
}

interface CostChartProps {
    data: ChartData
    account?: string
}

export function CostChart({ data, account }: CostChartProps) {
    const { t, locale } = useLocale()
    
    // 初始化默认30天
    const getDefaultRange = (): CostDateRange => {
        const now = new Date()
        const thirtyDaysAgo = new Date(now)
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
        return {
            startDate: thirtyDaysAgo.toISOString().split('T')[0],
            endDate: now.toISOString().split('T')[0]
        }
    }
    
    const [dateRange, setDateRange] = useState<CostDateRange>(getDefaultRange())
    const [chartData, setChartData] = useState(data)
    
    useEffect(() => {
        let cancelled = false
        async function load() {
            try {
                // 构建请求参数
                const params: any = { account }
                
                // 如果提供了日期范围，使用日期范围；否则使用days参数（从快捷选项推断）
                if (dateRange.startDate && dateRange.endDate) {
                    // 自定义日期范围
                    params.start_date = dateRange.startDate
                    params.end_date = dateRange.endDate
                    // 如果日期范围超过90天，使用月度粒度
                    const start = new Date(dateRange.startDate)
                    const end = new Date(dateRange.endDate)
                    const diffDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
                    if (diffDays > 90) {
                        params.granularity = 'monthly'
                    }
                } else if (!dateRange.startDate && !dateRange.endDate) {
                    // 全部历史数据，默认使用月度粒度
                    params.days = 0
                    params.granularity = 'monthly'
                } else {
                    // 默认30天（不应该到达这里，但作为fallback）
                    params.days = 30
                }
                
                const result = await apiGet('/dashboard/trend', params)
                if (!cancelled && result?.chart_data) {
                    // 处理新格式：chart_data 可能是数组格式 [{date, total_cost, ...}] 或旧格式 {dates, costs}
                    if (Array.isArray(result.chart_data) && result.chart_data.length > 0) {
                        // 新格式：转换为旧格式
                        const dates = result.chart_data.map((item: any) => item.date || '')
                        const costs = result.chart_data.map((item: any) => Number(item.total_cost) || Number(item.cost) || 0)
                        setChartData({ dates, costs })
                    } else if (result.chart_data.dates && result.chart_data.costs) {
                        // 旧格式：直接使用
                        setChartData(result.chart_data)
                    } else {
                        console.warn("[CostChart] ⚠️ 数据格式异常:", result.chart_data)
                    }
                }
            } catch (e) {
                if (!cancelled) console.error("Failed to fetch trend:", e)
            }
        }
        if (account) load()
        return () => { cancelled = true }
    }, [dateRange, account])
    
    
    // 处理日期范围变化
    const handleDateRangeChange = (range: CostDateRange) => {
        setDateRange(range)
    }
    
    if (!chartData || !chartData.dates) return null;

    // 判断是否为月度数据（通过日期格式判断：YYYY-MM 或数据量较少）
    const isMonthlyData = chartData.dates.length <= 24 && chartData.dates.some(d => d.length === 7 && d.includes('-'))
    // 根据数据量决定日期显示格式
    const dateFormat = chartData.dates.length > 90 || isMonthlyData ? 'YYYY-MM' : 'MM-DD'
    const processedData = chartData.dates.map((date, index) => ({
        date: dateFormat === 'YYYY-MM' 
            ? (date.length === 7 ? date : date.substring(0, 7))  // YYYY-MM
            : date.substring(5),     // MM-DD
        fullDate: date,  // 保存完整日期用于工具提示
        cost: chartData.costs[index]
    }));

    return (
        <Card className="animate-fade-in">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-xl font-semibold">{t.cost.costTrend}</CardTitle>
                        <CardDescription className="mt-1.5">
                            {dateRange.startDate && dateRange.endDate
                                ? `${dateRange.startDate} ${t.common.to} ${dateRange.endDate} ${t.cost.costTrend}`
                                : !dateRange.startDate && !dateRange.endDate
                                    ? t.dashboard.costTrendChart
                                    : t.cost.costTrend}
                        </CardDescription>
                    </div>
                    {/* Finout 风格：日期范围选择器 */}
                    <CostDateRangeSelector 
                        onChange={handleDateRangeChange}
                        className="flex-shrink-0"
                    />
                </div>
            </CardHeader>
            <CardContent>
                <div className="h-[450px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        {isMonthlyData ? (
                            // 月度数据使用柱状图
                            <BarChart 
                                data={processedData} 
                                margin={{ 
                                    top: 10, 
                                    right: 20, 
                                    left: 0, 
                                    bottom: 40
                                }}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    angle={-45}
                                    textAnchor="end"
                                    height={60}
                                    tick={{ fill: '#94a3b8' }}
                                />
                                <YAxis
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    tick={{ fill: '#94a3b8' }}
                                    tickFormatter={(value) => {
                                        if (value >= 10000) return `¥${(value / 10000).toFixed(1)}万`
                                        return `¥${value}`
                                    }}
                                />
                                <Tooltip
                                    contentStyle={{ 
                                        background: 'rgba(15, 15, 20, 0.95)', 
                                        border: '1px solid rgba(255,255,255,0.1)', 
                                        borderRadius: '12px', 
                                        color: '#fff', 
                                        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                                        padding: '12px 16px',
                                        backdropFilter: 'blur(20px)'
                                    }}
                                    itemStyle={{ color: '#fff', padding: '4px 0', fontSize: '14px' }}
                                    labelStyle={{ color: '#94a3b8', marginBottom: '8px', fontWeight: 600, fontSize: '12px' }}
                                    formatter={(value: any, name: any, props: any) => {
                                        const fullDate = props.payload?.fullDate || props.payload?.date
                                        return [`¥${Number(value).toLocaleString()}`, locale === 'zh' ? '成本' : 'Cost']
                                    }}
                                    labelFormatter={(label: any, payload: any) => {
                                        const fullDate = payload?.[0]?.payload?.fullDate || label
                                        return fullDate ? `日期: ${fullDate}` : label
                                    }}
                                />
                                <Bar 
                                    dataKey="cost" 
                                    fill="#3b82f6"
                                    radius={[4, 4, 0, 0]}
                                />
                            </BarChart>
                        ) : (
                            // 日度数据使用面积图
                            <AreaChart 
                                data={processedData} 
                                margin={{ 
                                    top: 10, 
                                    right: 20, 
                                    left: 0, 
                                    bottom: chartData.dates.length > 90 ? 60 : 0 
                                }}
                            >
                                <defs>
                                    {/* Finout 风格：蓝色渐变 */}
                                    <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                        <stop offset="50%" stopColor="#3b82f6" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                {/* Finout 风格：更淡的网格线 */}
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    minTickGap={chartData.dates.length > 90 ? 20 : 30}
                                    angle={chartData.dates.length > 90 ? -45 : 0}
                                    textAnchor={chartData.dates.length > 90 ? 'end' : 'middle'}
                                    height={chartData.dates.length > 90 ? 60 : 30}
                                    tick={{ fill: '#94a3b8' }}
                                />
                                <YAxis
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    tick={{ fill: '#94a3b8' }}
                                    tickFormatter={(value) => {
                                        if (value >= 10000) return `¥${(value / 10000).toFixed(1)}万`
                                        return `¥${value}`
                                    }}
                                />
                                {/* Finout 风格：更专业的工具提示 */}
                                <Tooltip
                                    contentStyle={{ 
                                        background: 'rgba(15, 15, 20, 0.95)', 
                                        border: '1px solid rgba(255,255,255,0.1)', 
                                        borderRadius: '12px', 
                                        color: '#fff', 
                                        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                                        padding: '12px 16px',
                                        backdropFilter: 'blur(20px)'
                                    }}
                                    itemStyle={{ color: '#fff', padding: '4px 0', fontSize: '14px' }}
                                    labelStyle={{ color: '#94a3b8', marginBottom: '8px', fontWeight: 600, fontSize: '12px' }}
                                    formatter={(value: any, name: any, props: any) => {
                                        const fullDate = props.payload?.fullDate || props.payload?.date
                                        return [`¥${Number(value).toLocaleString()}`, locale === 'zh' ? '成本' : 'Cost']
                                    }}
                                    labelFormatter={(label: any, payload: any) => {
                                        const fullDate = payload?.[0]?.payload?.fullDate || label
                                        return fullDate ? `日期: ${fullDate}` : label
                                    }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="cost"
                                    stroke="#3b82f6"
                                    strokeWidth={2}
                                    fillOpacity={1}
                                    fill="url(#colorCost)"
                                    dot={false}
                                    activeDot={{ r: 6, fill: '#3b82f6', strokeWidth: 2, stroke: '#fff', strokeOpacity: 0.8 }}
                                />
                            </AreaChart>
                        )}
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    )
}
