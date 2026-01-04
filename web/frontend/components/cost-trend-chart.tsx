"use client"

import { useState, useEffect, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { 
    AreaChart, Area, LineChart, Line, BarChart, Bar, 
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend 
} from 'recharts'
import { apiGet } from "@/lib/api"
import { useLocale } from "@/contexts/locale-context"
import { Button } from "@/components/ui/button"

// 资源类型颜色配置
const RESOURCE_COLORS: Record<string, string> = {
    'ECS': '#3b82f6',
    'RDS': '#10b981',
    'Redis': '#f59e0b',
    'OSS': '#ef4444',
    'SLB': '#8b5cf6',
    'EIP': '#06b6d4',
    'NAT': '#f97316',
    'Disk': '#84cc16',
    'MongoDB': '#ec4899',
    'ACK': '#6366f1',
    '其他': '#6b7280'
}

interface CostTrendChartProps {
    account?: string
    granularity?: 'daily' | 'monthly'  // 粒度：按天或按月
    days?: number  // 天数（按天视图时使用）
    startDate?: string  // 开始日期 YYYY-MM-DD
    endDate?: string  // 结束日期 YYYY-MM-DD
    chartType?: 'area' | 'line' | 'bar' | 'stacked'  // 图表类型
    showBreakdown?: boolean  // 是否显示资源类型分解
}

interface ChartDataPoint {
    date: string
    total_cost: number
    breakdown?: Record<string, number>  // 按资源类型分解
}

export function CostTrendChart({
    account,
    granularity = 'daily',
    days = 30,
    startDate,
    endDate,
    chartType = 'area',
    showBreakdown = false
}: CostTrendChartProps) {
    const { t, locale } = useLocale()
    const [data, setData] = useState<ChartDataPoint[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // 获取数据
    useEffect(() => {
        if (!account) {
            setLoading(false)
            return
        }

        let cancelled = false
        async function load() {
            try {
                setLoading(true)
                setError(null)

                const params: any = { account, granularity }
                
                if (startDate && endDate) {
                    params.start_date = startDate
                    params.end_date = endDate
                } else if (granularity === 'daily') {
                    params.days = days
                }

                const result = await apiGet('/dashboard/trend', params)
                
                if (!cancelled) {
                    if (result?.chart_data && Array.isArray(result.chart_data)) {
                        setData(result.chart_data)
                    } else if (result?.data?.chart_data) {
                        setData(result.data.chart_data)
                    } else {
                        setError('No data available')
                    }
                }
            } catch (e: any) {
                if (!cancelled) {
                    console.error("Failed to fetch cost trend:", e)
                    setError(e.message || 'Failed to load data')
                }
            } finally {
                if (!cancelled) {
                    setLoading(false)
                }
            }
        }

        load()
        return () => { cancelled = true }
    }, [account, granularity, days, startDate, endDate])

    // 处理数据格式
    const processedData = useMemo(() => {
        if (!data || data.length === 0) return []

        return data.map(item => {
            const processed: any = {
                date: granularity === 'daily' 
                    ? item.date.substring(5)  // MM-DD
                    : item.date.substring(0, 7),  // YYYY-MM
                fullDate: item.date,
                cost: item.total_cost || 0
            }

            // 如果有资源类型分解，添加到数据点
            if (showBreakdown && item.breakdown) {
                Object.entries(item.breakdown).forEach(([key, value]) => {
                    processed[key] = value || 0
                })
            }

            return processed
        })
    }, [data, granularity, showBreakdown])

    // 获取资源类型列表（用于图例）
    const resourceTypes = useMemo(() => {
        if (!showBreakdown || !data || data.length === 0) return []
        
        const types = new Set<string>()
        data.forEach(item => {
            if (item.breakdown) {
                Object.keys(item.breakdown).forEach(key => types.add(key))
            }
        })
        return Array.from(types)
    }, [data, showBreakdown])

    // 渲染图表
    const renderChart = () => {
        if (loading) {
            return (
                <div className="flex items-center justify-center h-[450px]">
                    <div className="text-muted-foreground">{locale === 'zh' ? '加载中...' : 'Loading...'}</div>
                </div>
            )
        }

        if (error || processedData.length === 0) {
            return (
                <div className="flex items-center justify-center h-[450px]">
                    <div className="text-muted-foreground">
                        {error || (locale === 'zh' ? '暂无数据' : 'No data available')}
                    </div>
                </div>
            )
        }

        const commonProps = {
            data: processedData,
            margin: { top: 10, right: 20, left: 0, bottom: granularity === 'monthly' ? 0 : 30 }
        }

        // 按天视图
        if (granularity === 'daily') {
            if (chartType === 'area' || chartType === 'stacked') {
                // 面积图（堆叠或单层）
                if (showBreakdown && resourceTypes.length > 0) {
                    // 堆叠面积图
                    return (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart {...commonProps}>
                                <defs>
                                    {resourceTypes.map((type, index) => (
                                        <linearGradient key={type} id={`color${type}`} x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor={RESOURCE_COLORS[type] || '#6b7280'} stopOpacity={0.3} />
                                            <stop offset="50%" stopColor={RESOURCE_COLORS[type] || '#6b7280'} stopOpacity={0.15} />
                                            <stop offset="95%" stopColor={RESOURCE_COLORS[type] || '#6b7280'} stopOpacity={0} />
                                        </linearGradient>
                                    ))}
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
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
                                    formatter={(value: any) => [`¥${Number(value).toLocaleString()}`, '']}
                                    labelFormatter={(label: any, payload: any) => {
                                        const fullDate = payload?.[0]?.payload?.fullDate || label
                                        return fullDate ? `日期: ${fullDate}` : label
                                    }}
                                />
                                {resourceTypes.map((type) => (
                                    <Area
                                        key={type}
                                        type="monotone"
                                        dataKey={type}
                                        stackId={chartType === 'stacked' ? '1' : undefined}
                                        stroke={RESOURCE_COLORS[type] || '#6b7280'}
                                        strokeWidth={2}
                                        fillOpacity={1}
                                        fill={chartType === 'stacked' ? `url(#color${type})` : `url(#color${type})`}
                                        dot={false}
                                        activeDot={{ r: 6, fill: RESOURCE_COLORS[type] || '#6b7280', strokeWidth: 2, stroke: '#fff', strokeOpacity: 0.8 }}
                                    />
                                ))}
                            </AreaChart>
                        </ResponsiveContainer>
                    )
                } else {
                    // 单层面积图
                    return (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart {...commonProps}>
                                <defs>
                                    <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                        <stop offset="50%" stopColor="#3b82f6" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
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
                                    formatter={(value: any) => [`¥${Number(value).toLocaleString()}`, locale === 'zh' ? '成本' : 'Cost']}
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
                        </ResponsiveContainer>
                    )
                }
            } else {
                // 折线图
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart {...commonProps}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                            <XAxis
                                dataKey="date"
                                stroke="rgba(255,255,255,0.2)"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
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
                                formatter={(value: any) => [`¥${Number(value).toLocaleString()}`, locale === 'zh' ? '成本' : 'Cost']}
                                labelFormatter={(label: any, payload: any) => {
                                    const fullDate = payload?.[0]?.payload?.fullDate || label
                                    return fullDate ? `日期: ${fullDate}` : label
                                }}
                            />
                            <Line
                                type="monotone"
                                dataKey="cost"
                                stroke="#3b82f6"
                                strokeWidth={3}
                                dot={false}
                                activeDot={{ r: 6, fill: '#3b82f6', strokeWidth: 2, stroke: '#fff', strokeOpacity: 0.8 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                )
            }
        } else {
            // 按月视图
            if (chartType === 'bar' || chartType === 'stacked') {
                // 柱状图
                if (showBreakdown && resourceTypes.length > 0) {
                    // 堆叠柱状图
                    return (
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart {...commonProps}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
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
                                    formatter={(value: any) => [`¥${Number(value).toLocaleString()}`, '']}
                                    labelFormatter={(label: any) => `月份: ${label}`}
                                />
                                {resourceTypes.map((type) => (
                                    <Bar
                                        key={type}
                                        dataKey={type}
                                        stackId={chartType === 'stacked' ? '1' : undefined}
                                        fill={RESOURCE_COLORS[type] || '#6b7280'}
                                    />
                                ))}
                            </BarChart>
                        </ResponsiveContainer>
                    )
                } else {
                    // 单层柱状图
                    return (
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart {...commonProps}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.2)"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
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
                                    formatter={(value: any) => [`¥${Number(value).toLocaleString()}`, locale === 'zh' ? '成本' : 'Cost']}
                                    labelFormatter={(label: any) => `月份: ${label}`}
                                />
                                <Bar dataKey="cost" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    )
                }
            } else {
                // 折线图
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart {...commonProps}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" opacity={0.5} />
                            <XAxis
                                dataKey="date"
                                stroke="rgba(255,255,255,0.2)"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
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
                                formatter={(value: any) => [`¥${Number(value).toLocaleString()}`, locale === 'zh' ? '成本' : 'Cost']}
                                labelFormatter={(label: any) => `月份: ${label}`}
                            />
                            <Line
                                type="monotone"
                                dataKey="cost"
                                stroke="#3b82f6"
                                strokeWidth={3}
                                dot={false}
                                activeDot={{ r: 6, fill: '#3b82f6', strokeWidth: 2, stroke: '#fff', strokeOpacity: 0.8 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                )
            }
        }
    }

    return (
        <Card className="animate-fade-in glass border border-border/50 shadow-xl">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-xl font-semibold">
                            {granularity === 'daily' 
                                ? (locale === 'zh' ? '成本趋势 - 按天视图' : 'Cost Trend - Daily View')
                                : (locale === 'zh' ? '成本趋势 - 按月视图' : 'Cost Trend - Monthly View')
                            }
                        </CardTitle>
                        <CardDescription className="mt-1.5">
                            {startDate && endDate
                                ? `${startDate} ${locale === 'zh' ? '至' : 'to'} ${endDate}`
                                : granularity === 'daily'
                                    ? (locale === 'zh' ? `最近${days}天` : `Last ${days} days`)
                                    : (locale === 'zh' ? '从有数据以来' : 'All available data')
                            }
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="h-[450px] w-full">
                    {renderChart()}
                </div>
                {/* 图例 */}
                {showBreakdown && resourceTypes.length > 0 && (
                    <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-border/50">
                        {resourceTypes.map((type) => (
                            <div key={type} className="flex items-center gap-2">
                                <div 
                                    className="w-4 h-4 rounded" 
                                    style={{ backgroundColor: RESOURCE_COLORS[type] || '#6b7280' }}
                                />
                                <span className="text-sm text-muted-foreground">{type}</span>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

