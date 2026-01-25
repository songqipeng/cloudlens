"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowUpRight, ArrowDownRight, Activity, DollarSign, CloudOff, Server, AlertTriangle, Tag, TrendingDown } from 'lucide-react'
import { useLocale } from "@/contexts/locale-context"

interface SummaryProps {
    totalCost?: number | null
    idleCount?: number | null
    trend?: string
    trendPct?: number | null
    totalResources?: number | null
    resourceBreakdown?: {
        ecs: number
        rds: number
        redis: number
    }
    alertCount?: number | null
    tagCoverage?: number | null
    savingsPotential?: number | null
}

// 数字格式化（支持动画）- Finout 风格：等宽字体
function AnimatedNumber({ value, decimals = 2, useWan = false }: { value: number | undefined | null; decimals?: number; useWan?: boolean }) {
    // 处理 undefined/null 的情况，默认为 0
    const safeValue = value ?? 0
    
    // 确保 safeValue 是数字类型
    const numValue = typeof safeValue === 'number' ? safeValue : Number(safeValue) || 0
    
    if (useWan && numValue >= 10000) {
        // 以万为单位，保留一位小数，使用w代替万避免换行
        const wanValue = numValue / 10000
        return (
            <span className="animate-count-up font-mono tabular-nums">
                ¥{wanValue.toLocaleString(undefined, { 
                    minimumFractionDigits: 1, 
                    maximumFractionDigits: 1 
                })}w
            </span>
        )
    }
    return (
        <span className="animate-count-up font-mono tabular-nums">
            ¥{numValue.toLocaleString(undefined, { 
                minimumFractionDigits: decimals, 
                maximumFractionDigits: decimals 
            })}
        </span>
    )
}

export function SummaryCards({ 
    totalCost, 
    idleCount, 
    trend, 
    trendPct,
    totalResources = 0,
    resourceBreakdown = { ecs: 0, rds: 0, redis: 0 },
    alertCount = 0,
    tagCoverage = 0,
    savingsPotential = 0,
}: SummaryProps) {
    // 确保所有数值都有安全的默认值
    const safeTotalCost = totalCost ?? 0
    const safeIdleCount = idleCount ?? 0
    const safeTrendPct = trendPct ?? 0
    const safeTotalResources = totalResources ?? 0
    const safeAlertCount = alertCount ?? 0
    const safeTagCoverage = tagCoverage ?? 0
    const safeSavingsPotential = savingsPotential ?? 0
    const safeTrend = trend ?? "N/A"
    const { t } = useLocale()
    
    // 转换趋势文本
    const getTrendText = (trend: string | undefined) => {
        if (!trend) return t.trend.insufficientData
        if (trend === "上升" || trend === "Up") return t.trend.up
        if (trend === "下降" || trend === "Down") return t.trend.down
        if (trend === "平稳" || trend === "Stable") return t.trend.stable
        if (trend === "N/A" || trend === "数据不足" || trend === "Insufficient Data") return t.trend.insufficientData
        return t.trend.unknown
    }
    
    return (
        <div className="grid gap-3 sm:gap-4 grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
            <Card className="group hover:shadow-xl hover:shadow-primary/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2 p-3 sm:p-6">
                    <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{t.dashboard.totalCost}</CardTitle>
                    <div className="p-1.5 sm:p-2.5 bg-primary/10 rounded-lg sm:rounded-xl group-hover:bg-primary/20 transition-colors">
                        <DollarSign className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                    </div>
                </CardHeader>
                <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
                    {/* 响应式数字：移动端28px，桌面端48px */}
                    <div className="text-[28px] sm:text-[36px] lg:text-[48px] font-bold tracking-tight mb-1 sm:mb-2 font-mono tabular-nums leading-none">
                        <AnimatedNumber value={safeTotalCost} useWan={true} />
                    </div>
                    <p className="text-[10px] sm:text-xs text-muted-foreground">
                        {t.dashboard.monthlyEstimate}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-blue-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2 p-3 sm:p-6">
                    <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{t.dashboard.costTrend}</CardTitle>
                    <div className="p-1.5 sm:p-2.5 bg-blue-500/10 rounded-lg sm:rounded-xl group-hover:bg-blue-500/20 transition-colors">
                        <Activity className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500" />
                    </div>
                </CardHeader>
                <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
                    {/* 响应式趋势文字 */}
                    <div className="text-xl sm:text-2xl lg:text-3xl font-bold tracking-tight mb-1 sm:mb-2">{getTrendText(safeTrend)}</div>
                    <p className="flex items-center gap-1 text-[10px] sm:text-xs text-muted-foreground flex-wrap">
                        {safeTrendPct > 0 ? (
                            <span className="text-[#ef4444] flex items-center gap-0.5 font-semibold">
                                <ArrowUpRight className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> {safeTrendPct.toFixed(1)}%
                            </span>
                        ) : safeTrendPct < 0 ? (
                            <span className="text-[#10b981] flex items-center gap-0.5 font-semibold">
                                <ArrowDownRight className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> {Math.abs(safeTrendPct).toFixed(1)}%
                            </span>
                        ) : (
                            <span className="text-muted-foreground">—</span>
                        )}
                        <span className="hidden sm:inline">{t.dashboard.comparedToLastMonth}</span>
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-orange-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2 p-3 sm:p-6">
                    <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{t.dashboard.idleResources}</CardTitle>
                    <div className="p-1.5 sm:p-2.5 bg-orange-500/10 rounded-lg sm:rounded-xl group-hover:bg-orange-500/20 transition-colors">
                        <CloudOff className="h-4 w-4 sm:h-5 sm:w-5 text-orange-500" />
                    </div>
                </CardHeader>
                <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
                    {/* 响应式数字 */}
                    <div className="text-[28px] sm:text-[36px] lg:text-[48px] font-bold tracking-tight text-[#f59e0b] mb-1 sm:mb-2 font-mono tabular-nums leading-none animate-count-up">{safeIdleCount}</div>
                    <p className="text-[10px] sm:text-xs text-muted-foreground">
                        {t.dashboard.suggestHandle}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-green-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2 p-3 sm:p-6">
                    <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{t.dashboard.totalResources}</CardTitle>
                    <div className="p-1.5 sm:p-2.5 bg-green-500/10 rounded-lg sm:rounded-xl group-hover:bg-green-500/20 transition-colors">
                        <Server className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
                    </div>
                </CardHeader>
                <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
                    <div className="text-[28px] sm:text-[36px] lg:text-[48px] font-bold tracking-tight mb-1 sm:mb-2 font-mono tabular-nums leading-none animate-count-up">{safeTotalResources}</div>
                    <p className="text-[10px] sm:text-xs text-muted-foreground truncate">
                        <span className="hidden sm:inline">ECS: {resourceBreakdown.ecs} | RDS: {resourceBreakdown.rds} | Redis: {resourceBreakdown.redis}</span>
                        <span className="sm:hidden">{resourceBreakdown.ecs + resourceBreakdown.rds + resourceBreakdown.redis} 实例</span>
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-red-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2 p-3 sm:p-6">
                    <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{t.dashboard.alertCount}</CardTitle>
                    <div className="p-1.5 sm:p-2.5 bg-red-500/10 rounded-lg sm:rounded-xl group-hover:bg-red-500/20 transition-colors">
                        <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-red-500" />
                    </div>
                </CardHeader>
                <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
                    <div className="text-[28px] sm:text-[36px] lg:text-[48px] font-bold tracking-tight text-[#ef4444] mb-1 sm:mb-2 font-mono tabular-nums leading-none animate-count-up">{safeAlertCount}</div>
                    <p className="text-[10px] sm:text-xs text-muted-foreground">
                        {t.dashboard.needAttention}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-purple-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2 p-3 sm:p-6">
                    <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{t.dashboard.tagCoverage}</CardTitle>
                    <div className="p-1.5 sm:p-2.5 bg-purple-500/10 rounded-lg sm:rounded-xl group-hover:bg-purple-500/20 transition-colors">
                        <Tag className="h-4 w-4 sm:h-5 sm:w-5 text-purple-500" />
                    </div>
                </CardHeader>
                <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
                    <div className="text-[28px] sm:text-[36px] lg:text-[48px] font-bold tracking-tight mb-1 sm:mb-2 font-mono tabular-nums leading-none animate-count-up">{safeTagCoverage.toFixed(1)}%</div>
                    <p className="text-[10px] sm:text-xs text-muted-foreground">
                        {t.dashboard.resourceTagCompleteness}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-emerald-500/20 transition-all duration-300 hover:-translate-y-1 col-span-2 sm:col-span-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2 p-3 sm:p-6">
                    <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{t.dashboard.savingsPotential}</CardTitle>
                    <div className="p-1.5 sm:p-2.5 bg-emerald-500/10 rounded-lg sm:rounded-xl group-hover:bg-emerald-500/20 transition-colors">
                        <TrendingDown className="h-4 w-4 sm:h-5 sm:w-5 text-emerald-500" />
                    </div>
                </CardHeader>
                <CardContent className="p-3 pt-0 sm:p-6 sm:pt-0">
                    <div className="text-[28px] sm:text-[36px] lg:text-[48px] font-bold tracking-tight text-[#10b981] mb-1 sm:mb-2 font-mono tabular-nums leading-none">
                        <AnimatedNumber value={safeSavingsPotential} useWan={true} />
                    </div>
                    <p className="text-[10px] sm:text-xs text-muted-foreground">
                        {t.dashboard.monthlySavingsPotential}
                    </p>
                </CardContent>
            </Card>

        </div>
    )
}
