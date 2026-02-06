"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useAccount } from "@/contexts/account-context"
import { apiGet } from "@/lib/api"
import { Sparkles, TrendingUp, AlertTriangle, Lightbulb, RefreshCw } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/empty-state"

interface OptimizationSuggestion {
  id: string
  type: string
  priority: string
  title: string
  description: string
  resource_id?: string
  resource_type?: string
  current_cost?: number
  potential_savings?: number
  confidence?: number
  action?: string
  estimated_savings?: number
  created_at?: string
  status: string
}

interface CostPrediction {
  predicted_cost: number
  avg_daily_cost: number
  confidence: number
  method: string
}

export default function AIOptimizerPage() {
  const { currentAccount } = useAccount()
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([])
  const [prediction, setPrediction] = useState<CostPrediction | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (currentAccount) {
      fetchData()
    } else {
      setLoading(false)
    }
  }, [currentAccount])

  const fetchData = async () => {
    try {
      setLoading(true)
      // 先尝试使用缓存（快速返回）
      try {
        const [cachedSuggestions, cachedPrediction] = await Promise.allSettled([
          apiGet("/ai-optimizer/suggestions", { account: currentAccount, limit: 20, force_refresh: false }, { timeout: 10000 } as any),
          apiGet("/ai-optimizer/predict", { account: currentAccount, days: 30, force_refresh: false }, { timeout: 10000 } as any)
        ])
        
        // 处理缓存结果
        if (cachedSuggestions.status === 'fulfilled' && cachedSuggestions.value?.success) {
          setSuggestions(cachedSuggestions.value.data || [])
        }
        if (cachedPrediction.status === 'fulfilled' && cachedPrediction.value?.success && cachedPrediction.value.data) {
          setPrediction(cachedPrediction.value.data)
        }
        
        // 如果有缓存数据，先显示，然后后台刷新
        if ((cachedSuggestions.status === 'fulfilled' && cachedSuggestions.value?.success) || 
            (cachedPrediction.status === 'fulfilled' && cachedPrediction.value?.success)) {
          setLoading(false)
          // 后台刷新最新数据（不阻塞UI）
          Promise.allSettled([
            apiGet("/ai-optimizer/suggestions", { account: currentAccount, limit: 20, force_refresh: true }, { timeout: 60000 } as any),
            apiGet("/ai-optimizer/predict", { account: currentAccount, days: 30, force_refresh: true }, { timeout: 60000 } as any)
          ]).then(([suggestionsRes, predictionRes]) => {
            if (suggestionsRes.status === 'fulfilled' && suggestionsRes.value?.success) {
              setSuggestions(suggestionsRes.value.data || [])
            }
            if (predictionRes.status === 'fulfilled' && predictionRes.value?.success && predictionRes.value.data) {
              setPrediction(predictionRes.value.data)
            }
          }).catch(err => {
            console.warn("后台刷新AI优化数据失败:", err)
          })
          return
        }
      } catch (e) {
        console.warn("获取缓存数据失败，尝试直接获取:", e)
      }
      
      // 如果没有缓存，直接获取（可能较慢）
      const [suggestionsRes, predictionRes] = await Promise.allSettled([
        apiGet("/ai-optimizer/suggestions", { account: currentAccount, limit: 20, force_refresh: true }, { timeout: 60000, retries: 1 } as any),
        apiGet("/ai-optimizer/predict", { account: currentAccount, days: 30, force_refresh: true }, { timeout: 60000, retries: 1 } as any)
      ])

      if (suggestionsRes.status === 'fulfilled' && suggestionsRes.value?.success) {
        setSuggestions(suggestionsRes.value.data || [])
      } else if (suggestionsRes.status === 'rejected') {
        console.error("获取优化建议失败:", suggestionsRes.reason)
        const errorMsg = suggestionsRes.reason?.message || String(suggestionsRes.reason)
        if (!errorMsg.includes('timeout') && !errorMsg.includes('abort')) {
          setError(`获取优化建议失败: ${errorMsg}`)
        }
        setSuggestions([])  // 设置为空数组，避免显示错误
      }

      if (predictionRes.status === 'fulfilled' && predictionRes.value?.success && predictionRes.value.data) {
        setPrediction(predictionRes.value.data)
      } else if (predictionRes.status === 'rejected') {
        console.error("获取成本预测失败:", predictionRes.reason)
        // 成本预测失败不影响主要功能，只记录日志
        setPrediction(null)  // 设置为null，避免显示错误
      }
    } catch (e: any) {
      console.error("Failed to fetch AI optimizer data:", e)
      const errorMsg = e?.message || String(e)
      if (!errorMsg.includes('timeout') && !errorMsg.includes('abort')) {
        setError(`加载失败: ${errorMsg}`)
      }
      // 即使失败也设置空数据，避免一直loading
      setSuggestions([])
      setPrediction(null)
    } finally {
      setLoading(false)
      setError(null)  // 清除之前的错误
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      // 强制刷新，不使用缓存
      const [suggestionsRes, predictionRes] = await Promise.allSettled([
        apiGet("/ai-optimizer/suggestions", { account: currentAccount, limit: 20, force_refresh: true }, { timeout: 60000, retries: 1 } as any),
        apiGet("/ai-optimizer/predict", { account: currentAccount, days: 30, force_refresh: true }, { timeout: 60000, retries: 1 } as any)
      ])
      
      if (suggestionsRes.status === 'fulfilled' && suggestionsRes.value?.success) {
        setSuggestions(suggestionsRes.value.data || [])
      }
      if (predictionRes.status === 'fulfilled' && predictionRes.value?.success && predictionRes.value.data) {
        setPrediction(predictionRes.value.data)
      }
    } catch (e: any) {
      console.error("刷新失败:", e)
      setError(`刷新失败: ${e?.message || String(e)}`)
    } finally {
      setRefreshing(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    const colors = {
      critical: "bg-red-500",
      high: "bg-orange-500",
      medium: "bg-yellow-500",
      low: "bg-blue-500"
    }
    return colors[priority as keyof typeof colors] || "bg-gray-500"
  }

  const getPriorityLabel = (priority: string) => {
    const labels = {
      critical: "严重",
      high: "高",
      medium: "中",
      low: "低"
    }
    return labels[priority as keyof typeof labels] || priority
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "resource_downsize":
        return <TrendingUp className="h-4 w-4" />
      case "resource_cleanup":
        return <AlertTriangle className="h-4 w-4" />
      case "cost_anomaly":
        return <AlertTriangle className="h-4 w-4" />
      default:
        return <Lightbulb className="h-4 w-4" />
    }
  }

  const totalPotentialSavings = suggestions.reduce(
    (sum, s) => sum + (s.potential_savings || 0),
    0
  )

  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-96 w-full" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">AI成本优化</h2>
            <p className="text-muted-foreground mt-1">智能分析和优化建议</p>
            {error && (
              <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-sm text-yellow-800 dark:text-yellow-200">
                ⚠️ {error}
              </div>
            )}
          </div>
          <Button onClick={handleRefresh} disabled={refreshing || loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "刷新中..." : "刷新"}
          </Button>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">优化建议</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{suggestions.length}</div>
              <div className="text-sm text-muted-foreground mt-1">条建议</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">潜在节省</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-500">
                ¥{totalPotentialSavings.toLocaleString()}
              </div>
              <div className="text-sm text-muted-foreground mt-1">预计节省金额</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">30天预测成本</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {prediction ? `¥${prediction.predicted_cost.toLocaleString()}` : "N/A"}
              </div>
              <div className="text-sm text-muted-foreground mt-1">
                {prediction ? `日均: ¥${prediction.avg_daily_cost.toFixed(2)}` : "数据不足"}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 优化建议列表 */}
        <Card>
          <CardHeader>
            <CardTitle>优化建议</CardTitle>
            <CardDescription>基于AI分析的智能优化建议</CardDescription>
          </CardHeader>
          <CardContent>
            {suggestions.length === 0 ? (
              <EmptyState
                icon={<Sparkles className="w-16 h-16" />}
                title="暂无优化建议"
                description="系统正在分析您的成本数据，稍后将提供优化建议"
              />
            ) : (
              <div className="space-y-4">
                {suggestions.map((suggestion) => (
                  <div
                    key={suggestion.id}
                    className="flex items-start gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="mt-1">
                      {getTypeIcon(suggestion.type)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-medium">{suggestion.title}</h3>
                        <Badge className={getPriorityColor(suggestion.priority)}>
                          {getPriorityLabel(suggestion.priority)}
                        </Badge>
                        {suggestion.confidence && (
                          <Badge variant="default">
                            置信度: {(suggestion.confidence * 100).toFixed(0)}%
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{suggestion.description}</p>
                      <div className="flex items-center gap-4 text-sm">
                        {suggestion.current_cost !== undefined && (
                          <span className="text-muted-foreground">
                            当前成本: ¥{suggestion.current_cost.toLocaleString()}
                          </span>
                        )}
                        {suggestion.potential_savings !== undefined && suggestion.potential_savings > 0 && (
                          <span className="text-green-500 font-medium">
                            潜在节省: ¥{suggestion.potential_savings.toLocaleString()}
                          </span>
                        )}
                        {suggestion.resource_id && (
                          <span className="text-muted-foreground">
                            资源: {suggestion.resource_type} / {suggestion.resource_id}
                          </span>
                        )}
                      </div>
                      {suggestion.action && (
                        <div className="mt-2 p-2 bg-blue-500/10 border border-blue-500/20 rounded text-sm">
                          <span className="font-medium">建议操作: </span>
                          {suggestion.action}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}






