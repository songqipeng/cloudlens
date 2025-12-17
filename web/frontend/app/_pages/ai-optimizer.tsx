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

  useEffect(() => {
    fetchData()
  }, [currentAccount])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [suggestionsRes, predictionRes] = await Promise.all([
        apiGet("/ai-optimizer/suggestions", { account: currentAccount, limit: 20 }),
        apiGet("/ai-optimizer/predict", { account: currentAccount, days: 30 })
      ])

      if (suggestionsRes.success) {
        setSuggestions(suggestionsRes.data || [])
      }

      if (predictionRes.success && predictionRes.data) {
        setPrediction(predictionRes.data)
      }
    } catch (e) {
      console.error("Failed to fetch AI optimizer data:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchData()
    setRefreshing(false)
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
          </div>
          <Button onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            刷新
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
                icon={Sparkles}
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
                          <Badge variant="outline">
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

