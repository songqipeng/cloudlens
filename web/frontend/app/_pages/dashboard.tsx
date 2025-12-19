"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { SummaryCards } from "@/components/summary-cards"
import { CostChart } from "@/components/cost-chart"
import { IdleTable } from "@/components/idle-table"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"
import { toastError } from "@/components/ui/toast"

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<any>(null)
  const [chartData, setChartData] = useState<any>(null)
  const [idleData, setIdleData] = useState<any>([])
  const [error, setError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const { currentAccount } = useAccount()

  const { t } = useLocale()

  async function handleScan() {
    if (!currentAccount) {
      toastError(t.dashboard.selectAccount)
      return
    }

    setScanning(true)
    try {
      const res = await fetch("http://127.0.0.1:8000/api/analyze/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account: currentAccount,
          days: 7,
          force: true,
        }),
      })
      if (!res.ok) throw new Error("Scan failed")
      // Reload data
      window.location.reload()
    } catch (e) {
      console.error(e)
      toastError(t.dashboard.scanFailed + ": " + String(e))
      setScanning(false)
    }
  }

  useEffect(() => {
    async function fetchData() {
      if (!currentAccount) {
        setLoading(false)
        return
      }

      // 账号切换时先清空旧数据，避免短暂显示上一账号内容
      setLoading(true)
      setError(null)
      setSummary(null)
      setChartData(null)
      setIdleData([])

      console.log("[Dashboard] 当前账号:", currentAccount)

      try {
        const sumData = await apiGet("/dashboard/summary", { account: currentAccount })
        console.log("[Dashboard] Summary 数据:", sumData)
        setSummary(sumData)

        try {
          const idleD = await apiGet("/dashboard/idle", { account: currentAccount })
          console.log("[Dashboard] Idle 数据:", idleD)
          setIdleData(idleD.data || idleD || [])
        } catch (e) {
          console.error("Failed to fetch idle data:", e)
        }

        try {
          const trendD = await apiGet("/dashboard/trend", { account: currentAccount, days: 30 })
          console.log("[Dashboard] Trend 数据:", trendD)
          setChartData(trendD.chart_data)
        } catch (e) {
          console.error("Failed to fetch trend data:", e)
        }

        setLoading(false)
      } catch (e) {
        console.error(e)
        setError(String(e))
        setLoading(false)
      }
    }

    fetchData()
  }, [currentAccount])

  if (!currentAccount) {
    return (
      <DashboardLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center space-y-4 max-w-md mx-auto p-6">
            <div className="w-16 h-16 bg-yellow-500/10 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-8 h-8 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-foreground mb-2">{t.dashboard.selectAccount}</h3>
              <p className="text-muted-foreground text-sm mb-4">{t.dashboard.selectAccountDesc}</p>
              <Link
                href="/settings/accounts"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                {t.dashboard.goToAccountManagement}
              </Link>
            </div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
          {/* Header Skeleton */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div className="space-y-2">
              <div className="h-9 w-48 bg-muted/50 rounded-lg animate-pulse"></div>
              <div className="h-5 w-32 bg-muted/50 rounded animate-pulse"></div>
            </div>
            <div className="h-10 w-32 bg-muted/50 rounded-lg animate-pulse"></div>
          </div>
          
          {/* Summary Cards Skeleton */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-7">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-border/50 bg-card/75 p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="h-4 w-24 bg-muted/50 rounded animate-pulse"></div>
                  <div className="h-10 w-10 bg-muted/50 rounded-xl animate-pulse"></div>
                </div>
                <div className="h-10 w-32 bg-muted/50 rounded animate-pulse"></div>
                <div className="h-3 w-20 bg-muted/50 rounded animate-pulse"></div>
              </div>
            ))}
          </div>
          
          {/* Chart Skeleton */}
          <div className="rounded-xl border border-border/50 bg-card/75 p-6">
            <div className="h-8 w-48 bg-muted/50 rounded mb-4 animate-pulse"></div>
            <div className="h-[450px] w-full bg-muted/30 rounded-lg animate-pulse"></div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center space-y-4 max-w-md mx-auto p-6">
            <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-foreground mb-2">加载失败</h3>
              <p className="text-muted-foreground text-sm">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                重新加载
              </button>
            </div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">{t.dashboard.title}</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleScan}
              disabled={scanning}
              className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-all duration-200 shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap hover:-translate-y-0.5"
            >
            {scanning ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                {t.dashboard.scanning}
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {t.dashboard.scanNow}
              </>
            )}
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        {summary && (
          <SummaryCards
            totalCost={summary.total_cost}
            idleCount={summary.idle_count}
            trend={summary.cost_trend}
            trendPct={summary.trend_pct}
            totalResources={summary.total_resources || 0}
            resourceBreakdown={summary.resource_breakdown || { ecs: 0, rds: 0, redis: 0 }}
            alertCount={summary.alert_count || 0}
            tagCoverage={summary.tag_coverage || 0}
            savingsPotential={summary.savings_potential || 0}
          />
        )}

        {/* 成本趋势图表 - 全宽 */}
        <div className="w-full">{chartData && <CostChart data={chartData} account={currentAccount} />}</div>

        {/* 闲置资源表格 */}
        <div className="w-full">
          <IdleTable data={idleData} />
        </div>
      </div>
    </DashboardLayout>
  )
}






