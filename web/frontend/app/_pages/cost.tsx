"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CostChart } from "@/components/cost-chart"
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"

export default function CostPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [overview, setOverview] = useState<any>(null)
  const [trend, setTrend] = useState<any>(null)
  const [breakdown, setBreakdown] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!currentAccount) {
      setLoading(false)
      return
    }
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount])

  const fetchData = async () => {
    if (!currentAccount) return

    try {
      const [overviewData, trendData, breakdownData] = await Promise.all([
        apiGet("/cost/overview", { account: currentAccount }).catch((e) => {
          console.error("获取成本概览失败:", e)
          return { success: false, data: null, error: String(e) }
        }),
        apiGet("/dashboard/trend", { account: currentAccount, days: 30 }).catch((e) => {
          console.error("获取成本趋势失败:", e)
          return { chart_data: null }
        }),
        apiGet("/cost/breakdown", { account: currentAccount }).catch((e) => {
          console.error("获取成本构成失败:", e)
          return { data: null }
        }),
      ])

      if (overviewData?.data) {
        setOverview(overviewData.data)
        // 如果上月成本为0，记录警告
        if (overviewData.data.last_month === 0 && overviewData.data.last_cycle) {
          console.warn(`⚠️ 上月成本为0: 账期=${overviewData.data.last_cycle}, 可能原因：1) 数据库中没有该账期数据 2) API查询失败 3) 该账期确实无成本`)
        }
      } else if (overviewData?.error) {
        console.error("成本概览API返回错误:", overviewData.error)
      }

      if (trendData?.chart_data) {
        setTrend(trendData.chart_data)
      }

      if (breakdownData?.data) {
        setBreakdown(breakdownData.data)
      }
    } catch (e) {
      console.error("Failed to fetch cost data:", e)
    } finally {
      setLoading(false)
    }
  }

  const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

  // 产品码 → 更友好的展示名称（账单 ProductCode）
  const PRODUCT_NAME_MAP: Record<string, string> = {
    ecs: "云服务器 ECS",
    rds: "云数据库 RDS",
    kvstore: "云数据库 Redis",
    redis: "云数据库 Redis",
    yundisk: "云盘",
    snapshot: "快照",
    slb: "负载均衡",
    nat_gw: "NAT 网关",
    eip: "弹性公网 IP",
    oss: "对象存储 OSS",
    sls: "日志服务 SLS",
    arms: "应用监控 ARMS",
    csk: "容器服务 ACK",
    emr: "E-MapReduce",
    rdc: "云效",
    cas: "SSL 证书服务",
    cdt: "云数据传输 CDT",
    prometheus: "Prometheus",
    kms: "KMS",
    nas: "文件存储 NAS",
  }

  const currency = (n: number) => `¥${(n || 0).toLocaleString()}`

  // 账单口径：优先使用后端返回的 categories（带 code/name/amount）
  const rawCategories: Array<{ code: string; name?: string; amount: number }> =
    (breakdown?.categories as any[])?.map((c: any) => ({
      code: String(c?.code || ""),
      name: String(c?.name || ""),
      amount: Number(c?.amount || 0),
    })) ||
    (breakdown?.by_type
      ? Object.entries(breakdown.by_type).map(([code, amount]) => ({
          code,
          name: "",
          amount: Number(amount || 0),
        }))
      : [])

  const normalized = rawCategories
    .filter((c) => c.code && c.amount > 0)
    .map((c) => ({
      code: c.code,
      name: PRODUCT_NAME_MAP[c.code] || c.name || c.code,
      value: c.amount,
    }))
    .sort((a, b) => b.value - a.value)

  // TopN + 其他（让饼图更像商业产品）
  const TOP_N = 6
  const breakdownData = (() => {
    const top = normalized.slice(0, TOP_N)
    const rest = normalized.slice(TOP_N)
    const restSum = rest.reduce((s, x) => s + x.value, 0)
    if (restSum <= 0) return top
    return [...top, { code: "other", name: t.costAnalysis.other, value: restSum }]
  })()

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">{t.costAnalysis.title}</h2>
          <p className="text-muted-foreground mt-1">{t.costAnalysis.description}</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-pulse">{t.common.loading}</div>
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-4">
              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.costAnalysis.currentMonthCost}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">¥{overview?.current_month?.toLocaleString() || 0}</div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.costAnalysis.lastMonthCost}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">¥{overview?.last_month?.toLocaleString() || 0}</div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.costAnalysis.momGrowth}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${(overview?.mom || 0) > 0 ? "text-red-500" : "text-green-500"}`}>
                    {(overview?.mom || 0) > 0 ? "+" : ""}{overview?.mom?.toFixed(1) || 0}%
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">{t.costAnalysis.yoyGrowth}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${(overview?.yoy || 0) > 0 ? "text-red-500" : "text-green-500"}`}>
                    {(overview?.yoy || 0) > 0 ? "+" : ""}{overview?.yoy?.toFixed(1) || 0}%
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              {trend && <CostChart data={trend} account={currentAccount || undefined} />}

              <Card className="glass border border-border/50 shadow-xl">
                <CardHeader>
                  <CardTitle>{t.costAnalysis.costBreakdown}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[450px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={breakdownData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={(props: any) => `${props.name || ""} ${((props.percent || 0) * 100).toFixed(0)}%`}
                          outerRadius={120}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {breakdownData.map((entry: any, index: number) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: any, name: any) => [currency(Number(value || 0)), name]}
                          contentStyle={{
                            background: "rgba(9, 9, 11, 0.9)",
                            border: "1px solid #27272a",
                            borderRadius: "8px",
                            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.5)",
                          }}
                        />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  )
}







