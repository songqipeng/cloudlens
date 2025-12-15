"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useRouter } from "next/navigation"
import { TrendingDown, DollarSign, AlertCircle, Tag, Server, Globe, Lock, Network, ArrowRight } from "lucide-react"
import { useAccount } from "@/contexts/account-context"
import { apiGet } from "@/lib/api"

interface Suggestion {
  type: string
  category: string
  priority: string
  title: string
  description: string
  savings_potential: number
  resource_count: number
  resources?: any[]
  action?: string
  recommendation?: string
}

interface OptimizationData {
  suggestions: Suggestion[]
  summary: {
    total_suggestions: number
    total_savings_potential: number
    high_priority_count: number
    medium_priority_count: number
    low_priority_count: number
  }
}

export default function OptimizationPage() {
  const router = useRouter()
  const { currentAccount } = useAccount()
  const [data, setData] = useState<OptimizationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedSuggestions, setExpandedSuggestions] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<string>("all")

  const base = useMemo(() => {
    return currentAccount ? `/a/${encodeURIComponent(currentAccount)}` : ""
  }, [currentAccount])

  useEffect(() => {
    if (!currentAccount) {
      setLoading(false)
      return
    }
    fetchSuggestions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount])

  const fetchSuggestions = async () => {
    if (!currentAccount) return

    try {
      const result = await apiGet("/optimization/suggestions")
      setData(result.data || { suggestions: [], summary: {} })
    } catch (e) {
      console.error("Failed to fetch suggestions:", e)
    } finally {
      setLoading(false)
    }
  }

  const toggleSuggestion = (type: string) => {
    const newExpanded = new Set(expandedSuggestions)
    if (newExpanded.has(type)) {
      newExpanded.delete(type)
    } else {
      newExpanded.add(type)
    }
    setExpandedSuggestions(newExpanded)
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-red-500/10 text-red-500 border-red-500/20"
      case "medium":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
      case "low":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20"
      default:
        return "bg-muted text-muted-foreground"
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "成本优化":
        return <DollarSign className="w-4 h-4" />
      case "安全优化":
        return <Lock className="w-4 h-4" />
      case "资源管理":
        return <Tag className="w-4 h-4" />
      default:
        return <TrendingDown className="w-4 h-4" />
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "idle_resources":
        return <Server className="w-5 h-5" />
      case "stopped_instances":
        return <Server className="w-5 h-5" />
      case "unbound_eips":
        return <Network className="w-5 h-5" />
      case "missing_tags":
        return <Tag className="w-5 h-5" />
      case "spec_downgrade":
        return <TrendingDown className="w-5 h-5" />
      case "public_exposure":
        return <Globe className="w-5 h-5" />
      case "disk_encryption":
        return <Lock className="w-5 h-5" />
      default:
        return <AlertCircle className="w-5 h-5" />
    }
  }

  const filteredSuggestions = data?.suggestions.filter((s) => {
    if (filter === "all") return true
    return s.priority === filter
  }) || []

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">优化建议</h2>
          <p className="text-muted-foreground mt-1">基于资源分析提供的详细优化建议</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-pulse">加载中...</div>
          </div>
        ) : !data || data.suggestions.length === 0 ? (
          <Card className="glass border border-border/50">
            <CardContent className="py-12 text-center">
              <TrendingDown className="w-16 h-16 mx-auto mb-4 opacity-50 text-muted-foreground" />
              <p className="text-lg font-medium text-foreground mb-2">暂无优化建议</p>
              <p className="text-sm text-muted-foreground">当前资源使用情况良好，未发现明显的优化机会</p>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-4">
              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                    <TrendingDown className="w-4 h-4" />
                    总节省潜力
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-500">¥{data.summary.total_savings_potential?.toLocaleString() || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">月度节省潜力</p>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">优化建议数</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.summary.total_suggestions || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">条优化建议</p>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">高优先级</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-red-500">{data.summary.high_priority_count || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">需要立即关注</p>
                </CardContent>
              </Card>

              <Card className="glass border border-border/50 hover:shadow-xl transition-all">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">中优先级</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-yellow-500">{data.summary.medium_priority_count || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">建议尽快处理</p>
                </CardContent>
              </Card>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setFilter("all")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filter === "all" ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" : "bg-muted/50 text-muted-foreground hover:bg-muted"
                }`}
              >
                全部 ({data.summary.total_suggestions || 0})
              </button>
              <button
                onClick={() => setFilter("high")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filter === "high" ? "bg-red-500 text-white shadow-md shadow-red-500/20" : "bg-muted/50 text-muted-foreground hover:bg-muted"
                }`}
              >
                高优先级 ({data.summary.high_priority_count || 0})
              </button>
              <button
                onClick={() => setFilter("medium")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filter === "medium" ? "bg-yellow-500 text-white shadow-md shadow-yellow-500/20" : "bg-muted/50 text-muted-foreground hover:bg-muted"
                }`}
              >
                中优先级 ({data.summary.medium_priority_count || 0})
              </button>
              <button
                onClick={() => setFilter("low")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filter === "low" ? "bg-blue-500 text-white shadow-md shadow-blue-500/20" : "bg-muted/50 text-muted-foreground hover:bg-muted"
                }`}
              >
                低优先级 ({data.summary.low_priority_count || 0})
              </button>
            </div>

            <div className="space-y-4">
              {filteredSuggestions.map((suggestion, idx) => (
                <Card
                  key={idx}
                  className={`glass border border-border/50 hover:shadow-xl transition-all ${
                    suggestion.priority === "high"
                      ? "border-l-4 border-l-red-500"
                      : suggestion.priority === "medium"
                        ? "border-l-4 border-l-yellow-500"
                        : "border-l-4 border-l-blue-500"
                  }`}
                >
                  <div className="cursor-pointer" onClick={() => toggleSuggestion(suggestion.type)}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4 flex-1">
                          <div className={`p-2.5 rounded-xl ${getPriorityColor(suggestion.priority)}`}>{getTypeIcon(suggestion.type)}</div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <CardTitle className="text-lg">{suggestion.title}</CardTitle>
                              <Badge className={getPriorityColor(suggestion.priority)}>
                                {suggestion.priority === "high" ? "高优先级" : suggestion.priority === "medium" ? "中优先级" : "低优先级"}
                              </Badge>
                              <Badge variant="info" className="flex items-center gap-1">
                                {getCategoryIcon(suggestion.category)}
                                {suggestion.category}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground mb-3">{suggestion.description}</p>
                            <div className="flex items-center gap-6 text-sm">
                              <div>
                                <span className="text-muted-foreground">涉及资源: </span>
                                <span className="font-semibold text-foreground">{suggestion.resource_count} 个</span>
                              </div>
                              {suggestion.savings_potential > 0 && (
                                <div>
                                  <span className="text-muted-foreground">节省潜力: </span>
                                  <span className="font-semibold text-green-500">¥{suggestion.savings_potential.toLocaleString()}/月</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                        <svg
                          className={`w-5 h-5 text-muted-foreground transition-transform flex-shrink-0 ${expandedSuggestions.has(suggestion.type) ? "rotate-180" : ""}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </CardHeader>
                  </div>

                  {expandedSuggestions.has(suggestion.type) && (
                    <CardContent className="border-t border-border/50 pt-4">
                      {suggestion.recommendation && (
                        <div className="mb-4 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                          <div className="flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                            <div>
                              <div className="text-sm font-medium text-blue-400 mb-1">💡 优化建议</div>
                              <div className="text-sm text-muted-foreground">{suggestion.recommendation}</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {suggestion.resources && suggestion.resources.length > 0 && (
                        <div>
                          <div className="text-sm font-semibold mb-3">相关资源 ({suggestion.resources.length}):</div>
                          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                            {suggestion.resources.map((resource: any, rIdx: number) => (
                              <div
                                key={rIdx}
                                className="p-3 bg-muted/30 rounded-lg text-sm hover:bg-muted/50 transition-colors cursor-pointer group"
                                onClick={() => {
                                  const resourceId = resource.instance_id || resource.id || resource.resource_id
                                  if (resourceId && base) router.push(`${base}/resources/${resourceId}`)
                                }}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex-1 min-w-0">
                                    <div className="font-medium truncate">{resource.name || resource.resource_name || resource.id || "-"}</div>
                                    <div className="text-xs text-muted-foreground truncate font-mono mt-1">{resource.instance_id || resource.id || resource.resource_id}</div>
                                  </div>
                                  <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ml-2" />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  )
}




