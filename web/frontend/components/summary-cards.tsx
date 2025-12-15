
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowUpRight, ArrowDownRight, Activity, DollarSign, CloudOff, Server, AlertTriangle, Tag, TrendingDown } from 'lucide-react'

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
    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-7 animate-fade-in">
            <Card className="glass border border-border/50 hover:shadow-2xl hover:shadow-primary/20 transition-all duration-300 hover:-translate-y-1.5 border-l-4 border-l-primary group">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">总预估成本</CardTitle>
                    <div className="p-2.5 bg-primary/10 rounded-xl group-hover:bg-primary/20 transition-colors">
                        <DollarSign className="h-5 w-5 text-primary" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-3xl font-bold tracking-tight mb-1">¥{totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    <p className="text-xs text-muted-foreground">
                        本月预估支出
                    </p>
                </CardContent>
            </Card>

            <Card className="glass border border-border/50 hover:shadow-2xl hover:shadow-blue-500/20 transition-all duration-300 hover:-translate-y-1.5 group">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">成本趋势</CardTitle>
                    <div className="p-2.5 bg-blue-500/10 rounded-xl group-hover:bg-blue-500/20 transition-colors">
                        <Activity className="h-5 w-5 text-blue-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-3xl font-bold tracking-tight mb-1">{trend}</div>
                    <p className="flex items-center text-xs text-muted-foreground">
                        {trendPct > 0 ? (
                            <span className="text-red-400 flex items-center mr-1">
                                <ArrowUpRight className="h-3 w-3 mr-0.5" /> {trendPct.toFixed(1)}%
                            </span>
                        ) : (
                            <span className="text-emerald-400 flex items-center mr-1">
                                <ArrowDownRight className="h-3 w-3 mr-0.5" /> {Math.abs(trendPct).toFixed(1)}%
                            </span>
                        )}
                        较上期
                    </p>
                </CardContent>
            </Card>

            <Card className="glass border border-border/50 hover:shadow-2xl hover:shadow-orange-500/20 transition-all duration-300 hover:-translate-y-1.5 border-l-4 border-l-orange-500 group">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">闲置资源</CardTitle>
                    <div className="p-2.5 bg-orange-500/10 rounded-xl group-hover:bg-orange-500/20 transition-colors">
                        <CloudOff className="h-5 w-5 text-orange-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-3xl font-bold tracking-tight text-orange-500 mb-1">{idleCount}</div>
                    <p className="text-xs text-muted-foreground">
                        建议尽快处理
                    </p>
                </CardContent>
            </Card>

            <Card className="glass border border-border/50 hover:shadow-2xl hover:shadow-green-500/20 transition-all duration-300 hover:-translate-y-1.5 group">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">资源总数</CardTitle>
                    <div className="p-2.5 bg-green-500/10 rounded-xl group-hover:bg-green-500/20 transition-colors">
                        <Server className="h-5 w-5 text-green-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-3xl font-bold tracking-tight mb-1">{totalResources}</div>
                    <p className="text-xs text-muted-foreground">
                        ECS: {resourceBreakdown.ecs} | RDS: {resourceBreakdown.rds} | Redis: {resourceBreakdown.redis}
                    </p>
                </CardContent>
            </Card>

            <Card className="glass border border-border/50 hover:shadow-2xl hover:shadow-red-500/20 transition-all duration-300 hover:-translate-y-1.5 group">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">告警数量</CardTitle>
                    <div className="p-2.5 bg-red-500/10 rounded-xl group-hover:bg-red-500/20 transition-colors">
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-3xl font-bold tracking-tight text-red-500 mb-1">{alertCount}</div>
                    <p className="text-xs text-muted-foreground">
                        需要关注
                    </p>
                </CardContent>
            </Card>

            <Card className="glass border border-border/50 hover:shadow-2xl hover:shadow-purple-500/20 transition-all duration-300 hover:-translate-y-1.5 group">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">标签覆盖率</CardTitle>
                    <div className="p-2.5 bg-purple-500/10 rounded-xl group-hover:bg-purple-500/20 transition-colors">
                        <Tag className="h-5 w-5 text-purple-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-3xl font-bold tracking-tight mb-1">{tagCoverage.toFixed(1)}%</div>
                    <p className="text-xs text-muted-foreground">
                        资源标签完整度
                    </p>
                </CardContent>
            </Card>

            <Card className="glass border border-border/50 hover:shadow-2xl hover:shadow-emerald-500/20 transition-all duration-300 hover:-translate-y-1.5 group">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">节省潜力</CardTitle>
                    <div className="p-2.5 bg-emerald-500/10 rounded-xl group-hover:bg-emerald-500/20 transition-colors">
                        <TrendingDown className="h-5 w-5 text-emerald-500" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-3xl font-bold tracking-tight text-emerald-500 mb-1">¥{savingsPotential.toLocaleString()}</div>
                    <p className="text-xs text-muted-foreground">
                        月度节省潜力
                    </p>
                </CardContent>
            </Card>

        </div>
    )
}
