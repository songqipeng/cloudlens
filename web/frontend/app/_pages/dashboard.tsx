"use client"

import { useEffect, useState, useRef } from "react"
import Link from "next/link"
import { SummaryCards } from "@/components/summary-cards"
import { CostChart } from "@/components/cost-chart"
import { IdleTable } from "@/components/idle-table"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiPost, ApiError } from "@/lib/api"
import { toastError, toastSuccess, toastInfo } from "@/components/ui/toast"
import { SmartLoadingProgress, LoadingProgress } from "@/components/loading-progress"

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<any>(null)
  const [chartData, setChartData] = useState<any>(null)
  const [idleData, setIdleData] = useState<any>([])
  const [error, setError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState<string>("")
  const loadingStartTime = useRef<number | null>(null)
  const [scanProgress, setScanProgress] = useState<{
    current: number
    total: number
    percent: number
    message: string
    stage: string
    status: string
  } | null>(null)
  const progressPollInterval = useRef<NodeJS.Timeout | null>(null)
  const { currentAccount } = useAccount()

  const { t } = useLocale()

  // 轮询获取扫描进度
  async function pollScanProgress(account: string) {
    try {
      const progress = await apiGet("/analyze/progress", { account }, { timeout: 5000 })
      
      if (!progress) {
        // 如果还没有进度，继续轮询
        progressPollInterval.current = setTimeout(() => {
          pollScanProgress(account)
        }, 1000)
        return
      }
      
      if (progress?.status === "running" || progress?.status === "initializing") {
        setScanProgress({
          current: progress.current || 0,
          total: progress.total || 100,
          percent: progress.percent || 0,
          message: progress.message || "正在扫描...",
          stage: progress.stage || "",
          status: progress.status || "running"
        })
        
        // 继续轮询
        progressPollInterval.current = setTimeout(() => {
          pollScanProgress(account)
        }, 1000) // 每秒轮询一次
      } else if (progress?.status === "completed") {
        // 扫描完成 - 立即停止扫描状态，清除进度条
        setScanning(false)
        setScanProgress(null)
        
        // 清除轮询
        if (progressPollInterval.current) {
          clearTimeout(progressPollInterval.current)
          progressPollInterval.current = null
        }
        
        // 显示成功消息
        const count = progress?.result?.count ?? 0
        const message = count > 0 
          ? `扫描完成！发现 ${count} 个闲置资源`
          : `扫描完成！当前账号下暂无闲置资源`
        toastSuccess(message, 2000)
        
        // 立即刷新数据（不延迟）
          async function refreshData() {
            try {
              const apiOptions = { timeout: 60000, retries: 2 } as any
            
            // 重新获取闲置资源数据
            const idleD = await apiGet("/dashboard/idle", { account: currentAccount }, apiOptions)
            console.log("[Dashboard] ✅ 扫描完成后的 Idle 数据:", idleD)
            
            // 处理不同的数据格式
            let idleArray: any[] = []
            if (idleD && typeof idleD === 'object') {
              if (Array.isArray(idleD)) {
                idleArray = idleD
              } else if (idleD.data && Array.isArray(idleD.data)) {
                idleArray = idleD.data
              } else if (idleD.success && idleD.data && Array.isArray(idleD.data)) {
                idleArray = idleD.data
              }
            }
            
            console.log(`[Dashboard] ✅ 设置 Idle 数据: ${idleArray.length} 条`)
            setIdleData(idleArray)
            
            // 重新获取摘要数据
            const sumData = await apiGet("/dashboard/summary", { account: currentAccount }, apiOptions)
            console.log("[Dashboard] ✅ 扫描完成后的 Summary 数据:", sumData)
            
            // 处理不同的数据格式
            if (sumData && typeof sumData === 'object') {
              if (sumData.success && sumData.data) {
                setSummary(sumData.data)
                console.log("[Dashboard] ✅ 设置 Summary 数据 (从 success.data)")
              } else {
                setSummary(sumData)
                console.log("[Dashboard] ✅ 设置 Summary 数据 (直接对象)")
              }
            }
          } catch (e) {
            console.error("[Dashboard] ❌ 刷新数据失败:", e)
            // 如果刷新失败，则刷新整个页面
            setTimeout(() => {
              window.location.reload()
            }, 1000)
          }
        }
        
        // 立即刷新数据
        refreshData()
      } else if (progress?.status === "failed") {
        // 扫描失败
        setScanning(false)
        setScanProgress(null)
        if (progressPollInterval.current) {
          clearTimeout(progressPollInterval.current)
          progressPollInterval.current = null
        }
        toastError(progress?.error || "扫描失败")
      } else if (progress?.status === "not_found") {
        // 任务不存在，可能是刚启动，继续轮询
        progressPollInterval.current = setTimeout(() => {
          pollScanProgress(account)
        }, 1000)
      }
    } catch (e) {
      console.warn("[Dashboard] 获取进度失败:", e)
      // 继续轮询，不中断（可能是网络问题或后端还没准备好）
      progressPollInterval.current = setTimeout(() => {
        pollScanProgress(account)
      }, 2000) // 失败后2秒再试
    }
  }

  async function handleScan() {
    if (!currentAccount) {
      toastError(t.dashboard.selectAccount)
      return
    }

    setScanning(true)
    // 立即显示初始进度条
    setScanProgress({
      current: 0,
      total: 100,
      percent: 0,
      message: "正在启动扫描任务...",
      stage: "initializing",
      status: "running"
    })
    
    // 清除之前的轮询
    if (progressPollInterval.current) {
      clearTimeout(progressPollInterval.current)
      progressPollInterval.current = null
    }
    
    // 立即开始轮询（不等待 API 响应）
    setTimeout(() => {
      pollScanProgress(currentAccount)
    }, 500) // 500ms 后开始轮询，给后端一点时间初始化
    
    try {
      // 启动扫描任务（前台执行）
      const result = await apiPost(
        "/analyze/trigger",
        {
          account: currentAccount,
          days: 7,
          force: true,
        },
        { account: currentAccount },
        {
          timeout: 300000, // 300秒超时（5分钟）
          retries: 1,
        }
      )

      console.log("[Dashboard] 扫描请求响应:", result)
      
      // 如果立即返回成功（可能是缓存）
      if (result?.status === "success") {
        const count = result?.count ?? 0
        const message = count > 0 
          ? `扫描完成！发现 ${count} 个闲置资源`
          : `扫描完成！当前账号下暂无闲置资源`
        
        toastSuccess(message, 2000)
        setTimeout(() => {
          window.location.reload()
        }, 1000)
        setScanning(false)
        setScanProgress(null)
        return
      }
      
      // 如果返回 processing，继续轮询（已经在上面开始了）
      if (result?.status === "processing") {
        console.log("[Dashboard] 扫描任务已在后台启动，继续轮询进度...")
      }
      
    } catch (e) {
      console.error("[Dashboard] 扫描失败:", e)
      
      // 清除轮询
      if (progressPollInterval.current) {
        clearTimeout(progressPollInterval.current)
        progressPollInterval.current = null
      }
      
      // 处理不同类型的错误
      let errorMessage = t.dashboard.scanFailed || "扫描失败"
      let showInstallHint = false
      
      if (e instanceof ApiError) {
        const detail = e.detail?.detail || e.detail?.error || e.message
        
        if (e.status === 408 || detail?.includes("超时") || detail?.includes("Timeout")) {
          errorMessage = detail || "请求超时，请稍后重试"
        } else if (e.status === 503 && (detail?.includes("aliyunsdkcore") || detail?.includes("缺少必要的依赖"))) {
          errorMessage = "分析服务不可用：缺少必要的依赖包"
          showInstallHint = true
        } else {
          errorMessage = `${errorMessage}: ${detail}`
        }
      } else if (e instanceof Error) {
        errorMessage = `${errorMessage}: ${e.message}`
      } else {
        errorMessage = `${errorMessage}: ${String(e)}`
      }
      
      toastError(errorMessage)
      
      if (showInstallHint) {
        console.error(`
[CloudLens] 缺少必要的依赖包，请运行以下命令安装：

pip install aliyun-python-sdk-core>=2.16.0

或者安装所有依赖：

pip install -r requirements.txt

安装完成后，请重启后端服务。
        `)
      }
      
      setScanning(false)
    }
  }
  
  // 组件卸载时清除轮询
  useEffect(() => {
    return () => {
      if (progressPollInterval.current) {
        clearTimeout(progressPollInterval.current)
        progressPollInterval.current = null
      }
    }
  }, [])

  useEffect(() => {
    async function fetchData() {
      if (!currentAccount) {
        setLoading(false)
        return
      }

      // 账号切换时先清空旧数据，避免短暂显示上一账号内容
      setLoading(true)
      loadingStartTime.current = Date.now()
      setError(null)
      setSummary(null)
      setChartData(null)
      setIdleData([])
      setLoadingMessage(t.dashboard.loading || "正在加载仪表盘数据...")

      console.log("[Dashboard] 当前账号:", currentAccount)

      try {
        // dashboard API 可能需要较长时间，增加超时时间到 180 秒（3分钟）
        // Idle API 从缓存读取，应该很快，但为了保险起见，设置较长的超时
        const apiOptions = { timeout: 180000, retries: 2 } as any
        
        setLoadingMessage(t.dashboard.loadingSummary || "正在加载摘要数据...")
        const sumData = await apiGet("/dashboard/summary", { account: currentAccount }, apiOptions)
        console.log("[Dashboard] ✅ 初始加载 Summary 数据:", sumData)
        
        // 处理不同的数据格式：可能是 {success: true, data: {...}} 或直接是对象
        if (sumData && typeof sumData === 'object') {
          if (sumData.success && sumData.data) {
            console.log("[Dashboard] ✅ 设置 Summary 数据 (从 success.data)")
            setSummary(sumData.data)
          } else {
            console.log("[Dashboard] ✅ 设置 Summary 数据 (直接对象)")
            setSummary(sumData)
          }
        } else {
          console.warn("[Dashboard] ⚠️  Summary 数据格式错误:", sumData)
          setSummary(null)
        }
        
        // 如果返回的是加载中的状态，等待一段时间后自动刷新
        if (sumData?.loading) {
          console.log("[Dashboard] 数据正在后台加载，3秒后自动刷新...")
          setTimeout(async () => {
            try {
              const refreshedData = await apiGet("/dashboard/summary", { account: currentAccount }, apiOptions)
              if (refreshedData && !refreshedData.loading) {
                console.log("[Dashboard] 数据已加载完成，更新显示")
                setSummary(refreshedData)
              }
            } catch (e) {
              console.warn("[Dashboard] 自动刷新失败:", e)
            }
          }, 3000)
        }

        setLoadingMessage(t.dashboard.loadingIdle || "正在加载闲置资源...")
        try {
          const idleD = await apiGet("/dashboard/idle", { account: currentAccount }, apiOptions)
          console.log("[Dashboard] ✅ 初始加载 Idle 数据:", idleD)
          
          // 处理不同的数据格式：可能是 {success: true, data: []} 或直接是数组
          let idleArray: any[] = []
          if (idleD && typeof idleD === 'object') {
            if (Array.isArray(idleD)) {
              idleArray = idleD
            } else if (idleD.data && Array.isArray(idleD.data)) {
              idleArray = idleD.data
            } else if (idleD.success && idleD.data && Array.isArray(idleD.data)) {
              idleArray = idleD.data
            } else {
              console.warn("[Dashboard] ⚠️  Idle 数据格式异常:", idleD)
            }
          }
          
          console.log(`[Dashboard] ✅ 设置 Idle 数据: ${idleArray.length} 条`)
          setIdleData(idleArray)
        } catch (e) {
          console.error("[Dashboard] ❌ 获取 Idle 数据失败:", e)
          setIdleData([])
        }

        setLoadingMessage(t.dashboard.loadingTrend || "正在加载成本趋势...")
        try {
          const trendD = await apiGet("/dashboard/trend", { account: currentAccount, days: 30 }, apiOptions)
          console.log("[Dashboard] Trend 数据:", trendD)
          
          // 处理新的数据格式：chart_data 可能是数组格式 [{date, total_cost, ...}] 或旧格式 {dates, costs}
          if (trendD?.chart_data) {
            if (Array.isArray(trendD.chart_data) && trendD.chart_data.length > 0) {
              // 新格式：转换为旧格式以兼容 CostChart 组件
              const dates = trendD.chart_data.map((item: any) => item.date || '')
              const costs = trendD.chart_data.map((item: any) => Number(item.total_cost) || Number(item.cost) || 0)
              const convertedData = { dates, costs }
              console.log("[Dashboard] ✅ 转换后的图表数据:", convertedData)
              setChartData(convertedData)
            } else if (trendD.chart_data.dates && trendD.chart_data.costs) {
              // 旧格式：直接使用
              console.log("[Dashboard] ✅ 使用旧格式数据")
              setChartData(trendD.chart_data)
            } else {
              console.warn("[Dashboard] ⚠️  Trend 数据格式异常:", trendD.chart_data)
              setChartData(null)
            }
          } else {
            console.warn("[Dashboard] ⚠️  没有 chart_data 字段")
            setChartData(null)
          }
        } catch (e) {
          console.error("[Dashboard] ❌ Failed to fetch trend data:", e)
          setChartData(null)
        }

        setLoadingMessage("")
        setLoading(false)
        // 延迟清除开始时间，让进度动画完成
        setTimeout(() => {
          loadingStartTime.current = null
        }, 500)
      } catch (e: any) {
        console.error("[Dashboard] 加载失败:", e)
        // 即使失败也尝试显示部分数据（如果有的话）
        const errorMsg = e?.message || e?.detail || String(e) || "加载失败"
        setError(errorMsg)
        setLoadingMessage("")
        setLoading(false)
        loadingStartTime.current = null
        
        // 如果 summary 数据已加载，至少显示这部分
        if (!summary) {
          // 如果完全没有数据，显示错误
          console.error("[Dashboard] 无法获取任何数据")
        }
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
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto">
          <SmartLoadingProgress
            message={loadingMessage || t.dashboard.loading || "正在加载仪表盘数据..."}
            subMessage={t.dashboard.loadingDesc || "正在从云端获取最新数据，请稍候..."}
            loading={loading}
            startTime={loadingStartTime.current || undefined}
            estimatedDuration={30} // 预估30秒
          />
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
              <h3 className="text-xl font-semibold text-foreground mb-2">{t.common.error}</h3>
              <p className="text-muted-foreground text-sm">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                {t.common.refresh}
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
            totalCost={summary.total_cost ?? 0}
            idleCount={summary.idle_count ?? 0}
            trend={summary.cost_trend ?? "N/A"}
            trendPct={summary.trend_pct ?? 0}
            totalResources={summary.total_resources ?? 0}
            resourceBreakdown={summary.resource_breakdown ?? { ecs: 0, rds: 0, redis: 0 }}
            alertCount={summary.alert_count ?? 0}
            tagCoverage={summary.tag_coverage ?? 0}
            savingsPotential={summary.savings_potential ?? 0}
          />
        )}

        {/* 成本趋势图表 - 全宽 */}
        <div className="w-full">{chartData && <CostChart data={chartData} account={currentAccount} />}</div>

        {/* 闲置资源表格 - 扫描时显示进度条 */}
        <div className="w-full">
          <IdleTable 
            data={idleData} 
            scanning={scanning}
            scanProgress={scanProgress}
          />
        </div>
      </div>
    </DashboardLayout>
  )
}







