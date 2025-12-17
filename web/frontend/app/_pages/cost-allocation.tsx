"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useAccount } from "@/contexts/account-context"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"
import { Plus, Edit, Trash2, Play, TrendingUp, DollarSign, PieChart } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/empty-state"
import { PieChart as RechartsPieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts"

interface AllocationRule {
  id: string
  name: string
  description?: string
  method: string
  account_id?: string
  enabled: boolean
  created_at?: string
  updated_at?: string
}

interface AllocationResult {
  id: string
  rule_id: string
  rule_name: string
  period: string
  total_cost: number
  allocated_cost: number
  unallocated_cost: number
  allocations: Array<{
    target: string
    amount: number
    percentage: number
  }>
  created_at?: string
}

export default function CostAllocationPage() {
  const { currentAccount } = useAccount()
  const [rules, setRules] = useState<AllocationRule[]>([])
  const [results, setResults] = useState<AllocationResult[]>([])
  const [loading, setLoading] = useState(true)
  const [editingRule, setEditingRule] = useState<AllocationRule | null>(null)
  const [activeTab, setActiveTab] = useState<"rules" | "results">("rules")

  useEffect(() => {
    fetchData()
  }, [currentAccount])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [rulesRes, resultsRes] = await Promise.all([
        apiGet("/cost-allocation/rules", { account: currentAccount }),
        apiGet("/cost-allocation/results", { limit: 50 })
      ])

      if (rulesRes.success) {
        setRules(rulesRes.data || [])
      }

      if (resultsRes.success) {
        setResults(resultsRes.data || [])
      }
    } catch (e) {
      console.error("Failed to fetch cost allocation data:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm("确定要删除此成本分配规则吗？")) {
      return
    }

    try {
      const response = await apiDelete(`/cost-allocation/rules/${ruleId}`)
      if (response.success) {
        await fetchData()
      }
    } catch (e) {
      alert("删除失败")
      console.error("Failed to delete rule:", e)
    }
  }

  const handleExecuteRule = async (ruleId: string) => {
    try {
      const response = await apiPost(`/cost-allocation/rules/${ruleId}/execute`, {}, { account: currentAccount })
      if (response.success) {
        alert("成本分配执行成功")
        await fetchData()
      }
    } catch (e) {
      alert("执行失败")
      console.error("Failed to execute rule:", e)
    }
  }

  const getMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      equal: "平均分配",
      proportional: "按比例分配",
      usage_based: "按使用量分配",
      tag_based: "按标签分配",
      custom: "自定义规则"
    }
    return labels[method] || method
  }

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
            <h2 className="text-3xl font-bold tracking-tight">成本分配</h2>
            <p className="text-muted-foreground mt-1">管理成本分配规则和查看分配结果</p>
          </div>
          <Button onClick={() => setEditingRule({} as AllocationRule)}>
            <Plus className="h-4 w-4 mr-2" />
            新建分配规则
          </Button>
        </div>

        {/* 标签页 */}
        <div className="flex items-center gap-2 border-b">
          <button
            onClick={() => setActiveTab("rules")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "rules"
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            分配规则 ({rules.length})
          </button>
          <button
            onClick={() => setActiveTab("results")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "results"
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            分配结果 ({results.length})
          </button>
        </div>

        {/* 分配规则列表 */}
        {activeTab === "rules" && (
          <Card>
            <CardHeader>
              <CardTitle>成本分配规则</CardTitle>
              <CardDescription>配置和管理成本分配规则</CardDescription>
            </CardHeader>
            <CardContent>
              {rules.length === 0 ? (
                <EmptyState
                  icon={PieChart}
                  title="暂无成本分配规则"
                  description="创建第一个成本分配规则来分配共享成本"
                  action={
                    <Button onClick={() => setEditingRule({} as AllocationRule)}>
                      <Plus className="h-4 w-4 mr-2" />
                      新建分配规则
                    </Button>
                  }
                />
              ) : (
                <div className="space-y-4">
                  {rules.map((rule) => (
                    <div
                      key={rule.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="font-medium">{rule.name}</h3>
                          <Badge>{getMethodLabel(rule.method)}</Badge>
                          {rule.enabled ? (
                            <Badge className="bg-green-500">已启用</Badge>
                          ) : (
                            <Badge className="bg-gray-500">已禁用</Badge>
                          )}
                        </div>
                        {rule.description && (
                          <p className="text-sm text-muted-foreground mt-1">{rule.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleExecuteRule(rule.id)}
                          disabled={!rule.enabled}
                        >
                          <Play className="h-4 w-4 mr-2" />
                          执行
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setEditingRule(rule)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteRule(rule.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* 分配结果列表 */}
        {activeTab === "results" && (
          <div className="space-y-6">
            {results.length === 0 ? (
              <Card>
                <CardContent className="p-12">
                  <EmptyState
                    icon={TrendingUp}
                    title="暂无分配结果"
                    description="执行成本分配规则后，结果将显示在这里"
                  />
                </CardContent>
              </Card>
            ) : (
              results.map((result) => (
                <Card key={result.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>{result.rule_name}</CardTitle>
                        <CardDescription>周期: {result.period}</CardDescription>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold">¥{result.total_cost.toLocaleString()}</div>
                        <div className="text-sm text-muted-foreground">总成本</div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div>
                        <div className="text-sm text-muted-foreground">已分配</div>
                        <div className="text-xl font-bold text-green-500">
                          ¥{result.allocated_cost.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">未分配</div>
                        <div className="text-xl font-bold text-gray-500">
                          ¥{result.unallocated_cost.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">分配率</div>
                        <div className="text-xl font-bold">
                          {((result.allocated_cost / result.total_cost) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>

                    {result.allocations && result.allocations.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-4">分配明细</h4>
                        <div className="grid grid-cols-2 gap-6">
                          <div>
                            <div className="space-y-2">
                              {result.allocations.map((alloc, index) => (
                                <div key={index} className="flex items-center justify-between p-2 border rounded">
                                  <span className="text-sm">{alloc.target}</span>
                                  <div className="text-right">
                                    <div className="font-medium">¥{alloc.amount.toFixed(2)}</div>
                                    <div className="text-xs text-muted-foreground">{alloc.percentage.toFixed(1)}%</div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                          <div>
                            <ResponsiveContainer width="100%" height={200}>
                              <RechartsPieChart>
                                <Pie
                                  data={result.allocations}
                                  dataKey="amount"
                                  nameKey="target"
                                  cx="50%"
                                  cy="50%"
                                  outerRadius={80}
                                  label={(entry: any) => `${entry.target}: ${entry.percentage.toFixed(1)}%`}
                                >
                                  {result.allocations.map((_, index) => (
                                    <Cell
                                      key={`cell-${index}`}
                                      fill={["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"][index % 5]}
                                    />
                                  ))}
                                </Pie>
                                <Tooltip formatter={(value: any) => `¥${Number(value).toFixed(2)}`} />
                                <Legend />
                              </RechartsPieChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}

        {/* 分配规则编辑器 */}
        {editingRule !== null && (
          <AllocationRuleEditor
            rule={editingRule}
            onSave={async () => {
              setEditingRule(null)
              await fetchData()
            }}
            onCancel={() => setEditingRule(null)}
          />
        )}
      </div>
    </DashboardLayout>
  )
}

// 分配规则编辑器组件
function AllocationRuleEditor({
  rule,
  onSave,
  onCancel
}: {
  rule: AllocationRule | null
  onSave: () => void
  onCancel: () => void
}) {
  const { currentAccount } = useAccount()
  const [name, setName] = useState(rule?.name || "")
  const [description, setDescription] = useState(rule?.description || "")
  const [method, setMethod] = useState(rule?.method || "equal")
  const [enabled, setEnabled] = useState(rule?.enabled !== false)
  const [allocationTargets, setAllocationTargets] = useState<string[]>([])
  const [allocationWeights, setAllocationWeights] = useState<Record<string, number>>({})
  const [newTarget, setNewTarget] = useState("")
  const [newWeight, setNewWeight] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const data: any = {
        name,
        description,
        method,
        enabled,
        allocation_targets: JSON.stringify(allocationTargets),
      }

      if (method === "proportional" && Object.keys(allocationWeights).length > 0) {
        data.allocation_weights = JSON.stringify(allocationWeights)
      }

      if (rule?.id) {
        await apiPut(`/cost-allocation/rules/${rule.id}`, data)
      } else {
        await apiPost("/cost-allocation/rules", data, { account: currentAccount })
      }

      onSave()
    } catch (e) {
      alert("保存失败")
      console.error("Failed to save rule:", e)
    }
  }

  const addTarget = () => {
    if (newTarget && !allocationTargets.includes(newTarget)) {
      setAllocationTargets([...allocationTargets, newTarget])
      if (method === "proportional") {
        setAllocationWeights({ ...allocationWeights, [newTarget]: 0 })
      }
      setNewTarget("")
    }
  }

  const removeTarget = (target: string) => {
    setAllocationTargets(allocationTargets.filter(t => t !== target))
    const newWeights = { ...allocationWeights }
    delete newWeights[target]
    setAllocationWeights(newWeights)
  }

  const updateWeight = (target: string, weight: number) => {
    setAllocationWeights({ ...allocationWeights, [target]: weight })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>{rule?.id ? "编辑分配规则" : "新建分配规则"}</CardTitle>
          <CardDescription>配置成本分配规则</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">规则名称</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">描述</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">分配方法</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              >
                <option value="equal">平均分配</option>
                <option value="proportional">按比例分配</option>
                <option value="usage_based">按使用量分配</option>
                <option value="tag_based">按标签分配</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">分配目标</label>
              <div className="flex items-center gap-2 mb-2">
                <input
                  type="text"
                  value={newTarget}
                  onChange={(e) => setNewTarget(e.target.value)}
                  placeholder="输入目标名称（如：部门、项目等）"
                  className="flex-1 px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                  onKeyPress={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      addTarget()
                    }
                  }}
                />
                <Button type="button" onClick={addTarget}>
                  添加
                </Button>
              </div>
              <div className="space-y-2">
                {allocationTargets.map((target) => (
                  <div key={target} className="flex items-center gap-2 p-2 border rounded">
                    <span className="flex-1">{target}</span>
                    {method === "proportional" && (
                      <input
                        type="number"
                        value={allocationWeights[target] || 0}
                        onChange={(e) => updateWeight(target, Number(e.target.value))}
                        placeholder="权重"
                        step="0.1"
                        min="0"
                        className="w-24 px-2 py-1 rounded border text-sm"
                      />
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeTarget(target)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              <label htmlFor="enabled" className="text-sm font-medium">
                启用此规则
              </label>
            </div>

            <div className="flex items-center justify-end gap-3">
              <Button type="button" variant="outline" onClick={onCancel}>
                取消
              </Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

