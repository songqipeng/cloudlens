"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowUpRight, ArrowDownRight, Activity, DollarSign, CloudOff, Server, AlertTriangle, Tag, TrendingDown } from 'lucide-react'
import { useLocale } from "@/contexts/locale-context"

interface SummaryProps {
    totalCost: number
    idleCount: number
    trend: string
    trendPct: number
    totalResources?: number
    resourceBreakdown?: {
        ecs: number
        rds: number
        redis: number
    }
    alertCount?: number
    tagCoverage?: number
    savingsPotential?: number
}

// 数字格式化（支持动画）- Finout 风格：等宽字体
function AnimatedNumber({ value, decimals = 2, useWan = false }: { value: number; decimals?: number; useWan?: boolean }) {
    if (useWan && value >= 10000) {
        // 以万为单位，保留一位小数，使用w代替万避免换行
        const wanValue = value / 10000
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
            ¥{value.toLocaleString(undefined, { 
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
    const { t } = useLocale()
    
    // 转换趋势文本
    const getTrendText = (trend: string) => {
        if (trend === "上升" || trend === "Up") return t.trend.up
        if (trend === "下降" || trend === "Down") return t.trend.down
        if (trend === "平稳" || trend === "Stable") return t.trend.stable
        if (trend === "N/A" || trend === "数据不足" || trend === "Insufficient Data") return t.trend.insufficientData
        return t.trend.unknown
    }
    
    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-7">
            <Card className="group hover:shadow-xl hover:shadow-primary/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{t.dashboard.totalCost}</CardTitle>
                    <div className="p-2.5 bg-primary/10 rounded-xl group-hover:bg-primary/20 transition-colors">
                        <DollarSign className="h-5 w-5 text-primary" />
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Finout 风格：大数字显示（48px），等宽字体，超过1万以万为单位 */}
                    <div className="text-[48px] font-bold tracking-tight mb-2 font-mono tabular-nums leading-none">
                        <AnimatedNumber value={totalCost} useWan={true} />
                    </div>
                    <p className="text-xs text-muted-foreground">
                        {t.dashboard.monthlyEstimate}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-blue-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{t.dashboard.costTrend}</CardTitle>
                    <div className="p-2.5 bg-blue-500/10 rounded-xl group-hover:bg-blue-500/20 transition-colors">
                        <Activity className="h-5 w-5 text-blue-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Finout 风格：趋势指示器 */}
                    <div className="text-3xl font-bold tracking-tight mb-2">{getTrendText(trend)}</div>
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        {trendPct > 0 ? (
                            <span className="text-[#ef4444] flex items-center gap-1 font-semibold">
                                <ArrowUpRight className="h-3.5 w-3.5" /> {trendPct.toFixed(1)}%
                            </span>
                        ) : trendPct < 0 ? (
                            <span className="text-[#10b981] flex items-center gap-1 font-semibold">
                                <ArrowDownRight className="h-3.5 w-3.5" /> {Math.abs(trendPct).toFixed(1)}%
                            </span>
                        ) : (
                            <span className="text-muted-foreground">—</span>
                        )}
                        <span>{t.dashboard.comparedToLastMonth}</span>
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-orange-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{t.dashboard.idleResources}</CardTitle>
                    <div className="p-2.5 bg-orange-500/10 rounded-xl group-hover:bg-orange-500/20 transition-colors">
                        <CloudOff className="h-5 w-5 text-orange-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Finout 风格：大数字，等宽字体 */}
                    <div className="text-[48px] font-bold tracking-tight text-[#f59e0b] mb-2 font-mono tabular-nums leading-none animate-count-up">{idleCount}</div>
                    <p className="text-xs text-muted-foreground">
                        {t.dashboard.suggestHandle}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-green-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{t.dashboard.totalResources}</CardTitle>
                    <div className="p-2.5 bg-green-500/10 rounded-xl group-hover:bg-green-500/20 transition-colors">
                        <Server className="h-5 w-5 text-green-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-[48px] font-bold tracking-tight mb-2 font-mono tabular-nums leading-none animate-count-up">{totalResources}</div>
                    <p className="text-xs text-muted-foreground">
                        ECS: {resourceBreakdown.ecs} | RDS: {resourceBreakdown.rds} | Redis: {resourceBreakdown.redis}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-red-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{t.dashboard.alertCount}</CardTitle>
                    <div className="p-2.5 bg-red-500/10 rounded-xl group-hover:bg-red-500/20 transition-colors">
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-[48px] font-bold tracking-tight text-[#ef4444] mb-2 font-mono tabular-nums leading-none animate-count-up">{alertCount}</div>
                    <p className="text-xs text-muted-foreground">
                        {t.dashboard.needAttention}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-purple-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{t.dashboard.tagCoverage}</CardTitle>
                    <div className="p-2.5 bg-purple-500/10 rounded-xl group-hover:bg-purple-500/20 transition-colors">
                        <Tag className="h-5 w-5 text-purple-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-[48px] font-bold tracking-tight mb-2 font-mono tabular-nums leading-none animate-count-up">{tagCoverage.toFixed(1)}%</div>
                    <p className="text-xs text-muted-foreground">
                        {t.dashboard.resourceTagCompleteness}
                    </p>
                </CardContent>
            </Card>

            <Card className="group hover:shadow-xl hover:shadow-emerald-500/20 transition-all duration-300 hover:-translate-y-1">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{t.dashboard.savingsPotential}</CardTitle>
                    <div className="p-2.5 bg-emerald-500/10 rounded-xl group-hover:bg-emerald-500/20 transition-colors">
                        <TrendingDown className="h-5 w-5 text-emerald-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-[48px] font-bold tracking-tight text-[#10b981] mb-2 font-mono tabular-nums leading-none">
                        <AnimatedNumber value={savingsPotential} useWan={true} />
                    </div>
                    <p className="text-xs text-muted-foreground">
                        {t.dashboard.monthlySavingsPotential}
                    </p>
                </CardContent>
            </Card>

        </div>
    )
}
