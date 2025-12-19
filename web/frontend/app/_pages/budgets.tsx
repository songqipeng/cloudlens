"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"
import { Plus, Edit, Trash2, TrendingUp, AlertTriangle, Calendar, DollarSign, Search } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/empty-state"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { toastError, toastSuccess } from "@/components/ui/toast"

interface AlertThreshold {
  percentage: number
  enabled: boolean
  notification_channels: string[]
}

interface Budget {
  id: string
  name: string
  amount: number
  period: string
  type: string
  start_date: string
  end_date: string
  tag_filter?: string | null
  service_filter?: string | null
  alerts: AlertThreshold[]
  account_id?: string | null
  created_at?: string
  updated_at?: string
}

interface BudgetStatus {
  budget_id: string
  spent: number
  remaining: number
  usage_rate: number
  days_elapsed: number
  days_total: number
  predicted_spend?: number | null
  predicted_overspend?: number | null
  alerts_triggered: any[]
}

export default function BudgetsPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null)
  const [showEditor, setShowEditor] = useState(false)
  const [selectedBudget, setSelectedBudget] = useState<string | null>(null)
  const [budgetStatus, setBudgetStatus] = useState<Record<string, BudgetStatus>>({})
  const [trendData, setTrendData] = useState<Record<string, any[]>>({})

  useEffect(() => {
    fetchBudgets()
  }, [currentAccount])

  const fetchBudgets = async () => {
    try {
      setLoading(true)
      const response = await apiGet("/budgets", { account: currentAccount || undefined })
      if (response.success) {
        setBudgets(response.data || [])
        // 获取每个预算的状态
        for (const budget of response.data || []) {
          fetchBudgetStatus(budget.id)
          fetchBudgetTrend(budget.id)
        }
      }
    } catch (e) {
      console.error("Failed to fetch budgets:", e)
    } finally {
      setLoading(false)
    }
  }

  const fetchBudgetStatus = async (budgetId: string) => {
    try {
      const response = await apiGet(`/budgets/${budgetId}/status`, { account: currentAccount || undefined })
      if (response.success) {
        setBudgetStatus(prev => ({
          ...prev,
          [budgetId]: response.data
        }))
      }
    } catch (e) {
      console.error(`Failed to fetch budget status for ${budgetId}:`, e)
    }
  }

  const fetchBudgetTrend = async (budgetId: string) => {
    try {
      const response = await apiGet(`/budgets/${budgetId}/trend`, { days: 30 })
      if (response.success) {
        setTrendData(prev => ({
          ...prev,
          [budgetId]: response.data || []
        }))
      }
    } catch (e) {
      console.error(`Failed to fetch budget trend for ${budgetId}:`, e)
    }
  }

  const handleDelete = async (budgetId: string) => {
    if (!confirm(t.budget.deleteConfirm)) return

    try {
      const response = await apiDelete(`/budgets/${budgetId}`)
      if (response.success) {
        setBudgets(budgets.filter(b => b.id !== budgetId))
        const newStatus = { ...budgetStatus }
        delete newStatus[budgetId]
        setBudgetStatus(newStatus)
        const newTrend = { ...trendData }
        delete newTrend[budgetId]
        setTrendData(newTrend)
      }
    } catch (e) {
      toastError(t.budget.deleteFailed)
      console.error("Failed to delete budget:", e)
    }
  }

  const handleSave = async (budgetData: any) => {
    setSaving(true)
    try {
      console.log("保存预算数据:", budgetData)
      let response
      if (editingBudget) {
        console.log("更新预算:", editingBudget.id)
        response = await apiPut(`/budgets/${editingBudget.id}`, budgetData)
      } else {
        // 不传 account_id，让后端从 account 参数生成
        console.log("创建预算:", budgetData)
        response = await apiPost("/budgets", budgetData, { account: currentAccount || undefined })
      }
      
      console.log("API 响应:", response)
      
      // 检查响应
      if (response && response.success) {
        // 成功提示
        const successMsg = t.budget?.saveSuccess || t.budget.saveSuccess
        toastSuccess(successMsg)
        await fetchBudgets()
        setShowEditor(false)
        setEditingBudget(null)
      } else {
        // 即使没有 success 字段，如果响应存在也认为成功（兼容性处理）
        const errorMsg = response?.message || response?.detail || t.budget.saveFailed
        console.warn("预算保存响应异常:", response)
        toastError(errorMsg)
      }
    } catch (e: any) {
      const errorMsg = e?.message || e?.toString() || t.budget.saveFailed
      toastError(`${t.budget.saveFailed}: ${errorMsg}`)
      console.error("Failed to save budget:", e)
    } finally {
      setSaving(false)
    }
  }

  const filteredBudgets = budgets.filter(budget =>
    budget.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getPeriodLabel = (period: string) => {
    const labels: Record<string, string> = {
      monthly: t.budget.period.monthly,
      quarterly: t.budget.period.quarterly,
      yearly: t.budget.period.yearly
    }
    return labels[period] || period
  }

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      total: t.budget.scope.total,
      tag: t.budget.scope.tag,
      service: t.budget.scope.service
    }
    return labels[type] || type
  }

  const getUsageColor = (usageRate: number) => {
    if (usageRate >= 100) return "text-red-500"
    if (usageRate >= 80) return "text-orange-500"
    if (usageRate >= 50) return "text-yellow-500"
    return "text-green-500"
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('zh-CN')
    } catch {
      return dateString
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-64 w-full" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{t.budget.title}</h2>
            <p className="text-muted-foreground mt-1">{t.budget.description}</p>
          </div>
          <Button
            onClick={() => {
              setEditingBudget(null)
              setShowEditor(true)
            }}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            {t.budget.createBudget}
          </Button>
        </div>

        {/* 搜索栏 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t.budget.searchPlaceholder}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
          />
        </div>

        {filteredBudgets.length === 0 ? (
          <EmptyState
            icon={<DollarSign className="w-16 h-16" />}
            title={searchTerm ? t.budget.noMatchBudgets : t.budget.noBudgets}
            description={searchTerm ? t.budget.tryOtherKeywords : t.budget.noBudgetsDesc}
          />
        ) : (
          <div className="grid gap-6">
            {filteredBudgets.map((budget) => {
              const status = budgetStatus[budget.id]
              const trend = trendData[budget.id] || []
              const usageRate = status?.usage_rate || 0

              return (
                <Card key={budget.id} className="overflow-hidden">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-xl">{budget.name}</CardTitle>
                        <CardDescription className="mt-2 flex items-center gap-4">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            {getPeriodLabel(budget.period)}
                          </span>
                          <span className="flex items-center gap-1">
                            <DollarSign className="h-4 w-4" />
                            {getTypeLabel(budget.type)}
                          </span>
                          <span>
                            {formatDate(budget.start_date)} - {formatDate(budget.end_date)}
                          </span>
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingBudget(budget)
                            setShowEditor(true)
                          }}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(budget.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* 预算状态 */}
                    {status && (
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div>
                          <div className="text-sm text-muted-foreground">{t.budget.budgetAmount}</div>
                          <div className="text-2xl font-bold mt-1">¥{budget.amount.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t.budget.spent}</div>
                          <div className="text-2xl font-bold mt-1">¥{status.spent.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t.budget.remaining}</div>
                          <div className="text-2xl font-bold mt-1">¥{status.remaining.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t.budget.usageRate}</div>
                          <div className={`text-2xl font-bold mt-1 ${getUsageColor(usageRate)}`}>
                            {usageRate.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 进度条 */}
                    {status && (
                      <div>
                        <div className="flex items-center justify-between text-sm mb-2">
                          <span>{t.budget.usageProgress}</span>
                          <span className={getUsageColor(usageRate)}>
                            {status.days_elapsed} / {status.days_total} {t.budget.days}
                          </span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              usageRate >= 100
                                ? "bg-red-500"
                                : usageRate >= 80
                                ? "bg-orange-500"
                                : usageRate >= 50
                                ? "bg-yellow-500"
                                : "bg-green-500"
                            }`}
                            style={{ width: `${Math.min(usageRate, 100)}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* 预测信息 */}
                    {status && status.predicted_spend && (
                      <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                        <TrendingUp className="h-5 w-5 text-primary" />
                        <div className="flex-1">
                          <div className="text-sm font-medium">{t.budget.predictedSpend}</div>
                          <div className="text-lg font-bold">¥{status.predicted_spend.toLocaleString()}</div>
                        </div>
                        {status.predicted_overspend && status.predicted_overspend > 0 && (
                          <div className="flex items-center gap-2 text-red-500">
                            <AlertTriangle className="h-5 w-5" />
                            <div>
                              <div className="text-sm font-medium">{t.budget.predictedOverspend}</div>
                              <div className="text-lg font-bold">¥{status.predicted_overspend.toLocaleString()}</div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* 告警状态 */}
                    {status && status.alerts_triggered && status.alerts_triggered.length > 0 && (
                      <div className="flex items-center gap-2 p-4 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-orange-500" />
                        <div className="flex-1">
                          <div className="text-sm font-medium text-orange-500">{t.budget.alertTriggered}</div>
                          <div className="text-sm text-muted-foreground">
                            {status.alerts_triggered.map((alert: any, idx: number) => (
                              <span key={idx}>
                                {alert.threshold}% 阈值已触发
                                {idx < status.alerts_triggered.length - 1 && ", "}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 趋势图表 */}
                    {trend.length > 0 && (
                      <div>
                        <h3 className="text-sm font-medium mb-4">{t.budget.spendingTrend}</h3>
                        <ResponsiveContainer width="100%" height={200}>
                          <AreaChart data={trend}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
                            <XAxis
                              dataKey="date"
                              stroke="hsl(var(--muted-foreground))"
                              fontSize={12}
                            />
                            <YAxis
                              stroke="hsl(var(--muted-foreground))"
                              fontSize={12}
                              tickFormatter={(value) => `¥${(value / 1000).toFixed(0)}k`}
                            />
                            <Tooltip
                              formatter={(value: any) => [`¥${Number(value).toLocaleString()}`, t.budget.spending]}
                              labelFormatter={(label) => `${t.budget.date} ${label}`}
                              contentStyle={{
                                backgroundColor: "hsl(var(--card))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "8px"
                              }}
                            />
                            <Area
                              type="monotone"
                              dataKey="spent"
                              stroke="hsl(var(--primary))"
                              fill="hsl(var(--primary))"
                              fillOpacity={0.2}
                            />
                            {trend.some((d: any) => d.predicted) && (
                              <Area
                                type="monotone"
                                dataKey="predicted"
                                stroke="hsl(var(--muted-foreground))"
                                fill="hsl(var(--muted-foreground))"
                                fillOpacity={0.1}
                                strokeDasharray="5 5"
                              />
                            )}
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}

        {/* 预算编辑器 */}
        {showEditor && (
          <BudgetEditor
            budget={editingBudget}
            saving={saving}
            onSave={handleSave}
            onCancel={() => {
              setShowEditor(false)
              setEditingBudget(null)
            }}
          />
        )}
      </div>
    </DashboardLayout>
  )
}

// 预算编辑器组件
function BudgetEditor({
  budget,
  saving,
  onSave,
  onCancel
}: {
  budget: Budget | null
  saving?: boolean
  onSave: (data: any) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(budget?.name || "")
  const [amount, setAmount] = useState(budget?.amount || 0)
  const [period, setPeriod] = useState(budget?.period || "monthly")
  const [type, setType] = useState(budget?.type || "total")
  const [startDate, setStartDate] = useState(
    budget?.start_date ? budget.start_date.split("T")[0] : new Date().toISOString().split("T")[0]
  )
  const [alerts, setAlerts] = useState<AlertThreshold[]>(budget?.alerts || [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      name,
      amount,
      period,
      type,
      start_date: `${startDate}T00:00:00`,
      alerts
    })
  }

  const addAlert = () => {
    setAlerts([...alerts, { percentage: 80, enabled: true, notification_channels: [] }])
  }

  const removeAlert = (index: number) => {
    setAlerts(alerts.filter((_, i) => i !== index))
  }

  const updateAlert = (index: number, field: keyof AlertThreshold, value: any) => {
    const newAlerts = [...alerts]
    newAlerts[index] = { ...newAlerts[index], [field]: value }
    setAlerts(newAlerts)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>{budget ? "编辑预算" : "新建预算"}</CardTitle>
          <CardDescription>配置预算信息和告警规则</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">{t.budget.budgetName}</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">预算金额 (CNY)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
                required
                min="0"
                step="0.01"
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.budget.budgetPeriod}</label>
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              >
                <option value="monthly">{t.budget.period.monthly}</option>
                <option value="quarterly">{t.budget.period.quarterly}</option>
                <option value="yearly">{t.budget.period.yearly}</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.budget.budgetType}</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              >
                <option value="total">{t.budget.scope.total}</option>
                <option value="tag">{t.budget.scope.tag}</option>
                <option value="service">{t.budget.scope.service}</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.budget.startDate}</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            {/* 告警规则 */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <label className="text-sm font-medium">{t.budget.alertRules}</label>
                <Button type="button" variant="outline" size="sm" onClick={addAlert}>
                  <Plus className="h-4 w-4 mr-1" />
                  {t.budget.addAlert}
                </Button>
              </div>
              <div className="space-y-3">
                {alerts.map((alert, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 border rounded-lg">
                    <input
                      type="number"
                      value={alert.percentage}
                      onChange={(e) => updateAlert(index, "percentage", parseFloat(e.target.value) || 0)}
                      min="0"
                      max="100"
                      step="1"
                      className="w-20 px-2 py-1 rounded border"
                    />
                    <span>%</span>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={alert.enabled}
                        onChange={(e) => updateAlert(index, "enabled", e.target.checked)}
                      />
                      <span className="text-sm">{t.budget.enable}</span>
                    </label>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeAlert(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {alerts.length === 0 && (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    {t.budget.noAlertRulesDesc}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3">
              <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
                {t.budget.cancel}
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? t.budget.saving : t.budget.save}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}


