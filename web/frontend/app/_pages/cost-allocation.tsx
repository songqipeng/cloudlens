"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"
import { Plus, Edit, Trash2, Play, TrendingUp, DollarSign, PieChart } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/empty-state"
import { PieChart as RechartsPieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts"
import { toastError, toastSuccess } from "@/components/ui/toast"

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
  const { t } = useLocale()
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
    if (!confirm(t.costAllocation.deleteConfirm)) {
      return
    }

    try {
      const response = await apiDelete(`/cost-allocation/rules/${ruleId}`)
      if (response.success) {
        await fetchData()
      }
    } catch (e) {
      toastError(t.costAllocation.deleteFailed)
      console.error("Failed to delete rule:", e)
    }
  }

  const handleExecuteRule = async (ruleId: string) => {
    try {
      const response = await apiPost(`/cost-allocation/rules/${ruleId}/execute`, {}, { account: currentAccount })
      if (response.success) {
        toastSuccess(t.costAllocation.executeSuccess)
        await fetchData()
      }
    } catch (e) {
      toastError(t.costAllocation.executeFailed)
      console.error("Failed to execute rule:", e)
    }
  }

  const getMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      equal: t.costAllocation.methods.equal,
      proportional: t.costAllocation.methods.proportional,
      usage_based: t.costAllocation.methods.usage_based,
      tag_based: t.costAllocation.methods.tag_based,
      custom: t.costAllocation.methods.custom
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
            <h2 className="text-3xl font-bold tracking-tight">{t.costAllocation.title}</h2>
            <p className="text-muted-foreground mt-1">{t.costAllocation.description}</p>
          </div>
          <Button onClick={() => setEditingRule({} as AllocationRule)}>
            <Plus className="h-4 w-4 mr-2" />
            {t.costAllocation.createRule}
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
            {t.costAllocation.rules} ({rules.length})
          </button>
          <button
            onClick={() => setActiveTab("results")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "results"
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.costAllocation.results} ({results.length})
          </button>
        </div>

        {/* 分配规则列表 */}
        {activeTab === "rules" && (
          <Card>
            <CardHeader>
              <CardTitle>{t.costAllocation.rulesTitle}</CardTitle>
              <CardDescription>{t.costAllocation.rulesDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              {rules.length === 0 ? (
                <EmptyState
                  icon={<PieChart className="w-16 h-16" />}
                  title={t.costAllocation.noRules}
                  description={t.costAllocation.noRulesDesc}
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
                            <Badge className="bg-green-500">{t.costAllocation.enabled}</Badge>
                          ) : (
                            <Badge className="bg-gray-500">{t.costAllocation.disabled}</Badge>
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
                          {t.costAllocation.execute}
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
                    icon={<TrendingUp className="w-16 h-16" />}
                    title="暂无分配结果"
                    description={t.costAllocation.noResultsDesc}
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
                        <CardDescription>{t.costAllocation.period}: {result.period}</CardDescription>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold">¥{result.total_cost.toLocaleString()}</div>
                        <div className="text-sm text-muted-foreground">{t.costAllocation.totalCost}</div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div>
                        <div className="text-sm text-muted-foreground">{t.costAllocation.allocated}</div>
                        <div className="text-xl font-bold text-green-500">
                          ¥{result.allocated_cost.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">{t.costAllocation.unallocated}</div>
                        <div className="text-xl font-bold text-gray-500">
                          ¥{result.unallocated_cost.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">{t.costAllocation.allocationRate}</div>
                        <div className="text-xl font-bold">
                          {((result.allocated_cost / result.total_cost) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>

                    {result.allocations && result.allocations.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-4">{t.costAllocation.allocationDetails}</h4>
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
  const { t } = useLocale()
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
      toastError(t.costAllocation.saveFailed)
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
          <CardTitle>{rule?.id ? t.costAllocation.editRule : t.costAllocation.createRule}</CardTitle>
          <CardDescription>{t.costAllocation.configureRule}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">{t.costAllocation.ruleName}</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.costAllocation.ruleDescription}</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.costAllocation.allocationMethod}</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              >
                <option value="equal">{t.costAllocation.methods.equal}</option>
                <option value="proportional">{t.costAllocation.methods.proportional}</option>
                <option value="usage_based">{t.costAllocation.methods.usage_based}</option>
                <option value="tag_based">{t.costAllocation.methods.tag_based}</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.costAllocation.allocationTarget}</label>
              <div className="flex items-center gap-2 mb-2">
                <input
                  type="text"
                  value={newTarget}
                  onChange={(e) => setNewTarget(e.target.value)}
                  placeholder={t.costAllocation.allocationTargetPlaceholder}
                  className="flex-1 px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                  onKeyPress={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      addTarget()
                    }
                  }}
                />
                <Button type="button" onClick={addTarget}>
                  {t.costAllocation.add}
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
                        placeholder={t.costAllocation.weight}
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
                {t.costAllocation.enableRule}
              </label>
            </div>

            <div className="flex items-center justify-end gap-3">
              <Button type="button" variant="outline" onClick={onCancel}>
                {t.common.cancel}
              </Button>
              <Button type="submit">{t.common.save}</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}






