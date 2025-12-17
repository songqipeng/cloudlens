"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableColumn } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"
import { Plus, Edit, Trash2, Bell, CheckCircle, XCircle, AlertTriangle, Info } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/empty-state"

interface AlertRule {
  id: string
  name: string
  description?: string
  type: string
  severity: string
  enabled: boolean
  condition: string
  threshold?: number
  metric?: string
  account_id?: string
  created_at?: string
  updated_at?: string
}

interface Alert {
  id: string
  rule_id: string
  rule_name: string
  severity: string
  status: string
  title: string
  message: string
  metric_value?: number
  threshold?: number
  account_id?: string
  triggered_at?: string
}

export default function AlertsPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [rules, setRules] = useState<AlertRule[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [activeTab, setActiveTab] = useState<"rules" | "alerts">("rules")

  useEffect(() => {
    fetchData()
  }, [currentAccount])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [rulesRes, alertsRes] = await Promise.all([
        apiGet("/alerts/rules", { account: currentAccount }),
        apiGet("/alerts", { account: currentAccount, limit: 50 })
      ])

      if (rulesRes.success) {
        setRules(rulesRes.data || [])
      }

      if (alertsRes.success) {
        setAlerts(alertsRes.data || [])
      }
    } catch (e) {
      console.error("Failed to fetch alerts data:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm(t.alerts.deleteConfirm)) {
      return
    }

    try {
      const response = await apiDelete(`/alerts/rules/${ruleId}`)
      if (response.success) {
        await fetchData()
      }
    } catch (e) {
      alert(t.alerts.deleteFailed)
      console.error("Failed to delete rule:", e)
    }
  }

  const handleToggleRule = async (rule: AlertRule) => {
    try {
      const response = await apiPut(`/alerts/rules/${rule.id}`, {
        ...rule,
        enabled: !rule.enabled
      })
      if (response.success) {
        await fetchData()
      }
    } catch (e) {
      alert(t.alerts.updateFailed)
      console.error("Failed to toggle rule:", e)
    }
  }

  const handleCheckRule = async (ruleId: string) => {
    try {
      const response = await apiPost(`/alerts/rules/${ruleId}/check`, {}, { account: currentAccount })
      if (response.success) {
        if (response.triggered) {
          alert(`${t.alerts.alertTriggered}: ${response.data.title}`)
        } else {
          alert(t.alerts.alertNotTriggered)
        }
        await fetchData()
      }
    } catch (e) {
      alert(t.alerts.checkFailed)
      console.error("Failed to check rule:", e)
    }
  }

  const handleUpdateAlertStatus = async (alertId: string, status: string) => {
    try {
      const response = await apiPut(`/alerts/${alertId}/status`, { status })
      if (response.success) {
        await fetchData()
      }
    } catch (e) {
      alert(t.alerts.updateFailed)
      console.error("Failed to update alert status:", e)
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <AlertTriangle className="h-4 w-4 text-red-500" />
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      default:
        return <Info className="h-4 w-4 text-blue-500" />
    }
  }

  const getSeverityBadge = (severity: string) => {
    const colors = {
      critical: "bg-red-500",
      error: "bg-red-500",
      warning: "bg-yellow-500",
      info: "bg-blue-500"
    }
    return (
      <Badge className={colors[severity as keyof typeof colors] || "bg-gray-500"}>
        {severity.toUpperCase()}
      </Badge>
    )
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      triggered: "bg-red-500",
      acknowledged: "bg-yellow-500",
      resolved: "bg-green-500",
      closed: "bg-gray-500"
    }
    const labels = {
      triggered: t.alerts.triggered,
      acknowledged: t.alerts.acknowledged,
      resolved: t.alerts.resolved,
      closed: t.alerts.closed
    }
    return (
      <Badge className={colors[status as keyof typeof colors] || "bg-gray-500"}>
        {labels[status as keyof typeof labels] || status}
      </Badge>
    )
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
            <h2 className="text-3xl font-bold tracking-tight">{t.alerts.title}</h2>
            <p className="text-muted-foreground mt-1">{t.alerts.description}</p>
          </div>
          <Button onClick={() => setEditingRule({} as AlertRule)}>
            <Plus className="h-4 w-4 mr-2" />
            {t.alerts.createRule}
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
            {t.alerts.rules} ({rules.length})
          </button>
          <button
            onClick={() => setActiveTab("alerts")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "alerts"
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.alerts.records} ({alerts.filter(a => a.status === "triggered" || a.status === "acknowledged").length})
          </button>
        </div>

        {/* 告警规则列表 */}
        {activeTab === "rules" && (
          <Card>
            <CardHeader>
              <CardTitle>{t.alerts.alertRules}</CardTitle>
              <CardDescription>{t.alerts.manageRules}</CardDescription>
            </CardHeader>
            <CardContent>
              {rules.length === 0 ? (
                <EmptyState
                  icon={Bell}
                  title={t.alerts.noRules}
                  description={t.alerts.noRulesDesc}
                  action={
                    <Button onClick={() => setEditingRule({} as AlertRule)}>
                      <Plus className="h-4 w-4 mr-2" />
                      {t.alerts.createRule}
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
                          {getSeverityIcon(rule.severity)}
                          <h3 className="font-medium">{rule.name}</h3>
                          {getSeverityBadge(rule.severity)}
                          {rule.enabled ? (
                            <Badge className="bg-green-500">{t.alerts.enabled}</Badge>
                          ) : (
                            <Badge className="bg-gray-500">{t.alerts.disabled}</Badge>
                          )}
                        </div>
                        {rule.description && (
                          <p className="text-sm text-muted-foreground mt-1">{rule.description}</p>
                        )}
                        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                          <span>{t.alerts.type}: {rule.type}</span>
                          {rule.metric && <span>{t.alerts.metric}: {rule.metric}</span>}
                          {rule.threshold && <span>{t.alerts.threshold}: {rule.threshold}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCheckRule(rule.id)}
                        >
                          {t.alerts.check}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleRule(rule)}
                        >
                          {rule.enabled ? (t.locale === 'zh' ? '禁用' : 'Disable') : (t.locale === 'zh' ? '启用' : 'Enable')}
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

        {/* 告警记录列表 */}
        {activeTab === "alerts" && (
          <Card>
            <CardHeader>
              <CardTitle>{t.alerts.alertRecords}</CardTitle>
              <CardDescription>{t.alerts.viewAndManageRecords}</CardDescription>
            </CardHeader>
            <CardContent>
              {alerts.length === 0 ? (
                <EmptyState
                  icon={CheckCircle}
                  title={t.alerts.noRecords}
                  description={t.alerts.noRecordsDesc}
                />
              ) : (
                <div className="space-y-4">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className="flex items-start justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          {getSeverityIcon(alert.severity)}
                          <h3 className="font-medium">{alert.title}</h3>
                          {getSeverityBadge(alert.severity)}
                          {getStatusBadge(alert.status)}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                          <span>{t.alerts.rule}: {alert.rule_name}</span>
                          {alert.metric_value !== undefined && (
                            <span>{t.alerts.metricValue}: {alert.metric_value.toFixed(2)}</span>
                          )}
                          {alert.threshold !== undefined && (
                            <span>{t.alerts.threshold}: {alert.threshold}</span>
                          )}
                          {alert.triggered_at && (
                            <span>{t.alerts.triggerTime}: {new Date(alert.triggered_at).toLocaleString()}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {alert.status === "triggered" && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleUpdateAlertStatus(alert.id, "acknowledged")}
                            >
                              {t.alerts.confirm}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleUpdateAlertStatus(alert.id, "resolved")}
                            >
                              {t.alerts.resolve}
                            </Button>
                          </>
                        )}
                        {alert.status === "acknowledged" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleUpdateAlertStatus(alert.id, "resolved")}
                          >
                            {t.alerts.resolve}
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUpdateAlertStatus(alert.id, "closed")}
                        >
                          {t.alerts.close}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* 告警规则编辑器 */}
        {editingRule !== null && (
          <AlertRuleEditor
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

// 告警规则编辑器组件
function AlertRuleEditor({
  rule,
  onSave,
  onCancel
}: {
  rule: AlertRule | null
  onSave: () => void
  onCancel: () => void
}) {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [name, setName] = useState(rule?.name || "")
  const [description, setDescription] = useState(rule?.description || "")
  const [type, setType] = useState(rule?.type || "cost_threshold")
  const [severity, setSeverity] = useState(rule?.severity || "warning")
  const [enabled, setEnabled] = useState(rule?.enabled !== false)
  const [condition, setCondition] = useState(rule?.condition || "gt")
  const [threshold, setThreshold] = useState(rule?.threshold || 0)
  const [metric, setMetric] = useState(rule?.metric || "total_cost")
  const [notifyEmail, setNotifyEmail] = useState("")
  const [notifyWebhook, setNotifyWebhook] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const data = {
        name,
        description,
        type,
        severity,
        enabled,
        condition,
        threshold: type === "cost_threshold" ? threshold : undefined,
        metric: type === "cost_threshold" ? metric : undefined,
        notify_email: notifyEmail || undefined,
        notify_webhook: notifyWebhook || undefined
      }

      if (rule?.id) {
        await apiPut(`/alerts/rules/${rule.id}`, data)
      } else {
        await apiPost("/alerts/rules", data, { account: currentAccount })
      }

      onSave()
    } catch (e) {
      alert(t.settings.saveFailed)
      console.error("Failed to save rule:", e)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>{rule?.id ? t.alerts.editRule : t.alerts.createRule}</CardTitle>
          <CardDescription>{t.alerts.configureRule}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">{t.locale === 'zh' ? '规则名称' : 'Rule Name'}</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.locale === 'zh' ? '描述' : 'Description'}</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">{t.alerts.alertType}</label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                >
                  <option value="cost_threshold">{t.alerts.costThreshold}</option>
                  <option value="budget_overspend">{t.locale === 'zh' ? '预算超支' : 'Budget Overspend'}</option>
                  <option value="resource_anomaly">{t.locale === 'zh' ? '资源异常' : 'Resource Anomaly'}</option>
                  <option value="security_compliance">{t.locale === 'zh' ? '安全合规' : 'Security Compliance'}</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">{t.locale === 'zh' ? '严重程度' : 'Severity'}</label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                >
                  <option value="info">{t.locale === 'zh' ? '信息' : 'Info'}</option>
                  <option value="warning">{t.locale === 'zh' ? '警告' : 'Warning'}</option>
                  <option value="error">{t.locale === 'zh' ? '错误' : 'Error'}</option>
                  <option value="critical">{t.locale === 'zh' ? '严重' : 'Critical'}</option>
                </select>
              </div>
            </div>

            {type === "cost_threshold" && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">{t.alerts.metric}</label>
                    <select
                      value={metric}
                      onChange={(e) => setMetric(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                    >
                      <option value="total_cost">{t.locale === 'zh' ? '总成本' : 'Total Cost'}</option>
                      <option value="daily_cost">{t.locale === 'zh' ? '日成本' : 'Daily Cost'}</option>
                      <option value="monthly_cost">{t.locale === 'zh' ? '月成本' : 'Monthly Cost'}</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">{t.locale === 'zh' ? '条件' : 'Condition'}</label>
                    <select
                      value={condition}
                      onChange={(e) => setCondition(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                    >
                      <option value="gt">{t.locale === 'zh' ? '大于' : 'Greater Than'}</option>
                      <option value="gte">{t.locale === 'zh' ? '大于等于' : 'Greater Than or Equal'}</option>
                      <option value="lt">{t.locale === 'zh' ? '小于' : 'Less Than'}</option>
                      <option value="lte">{t.locale === 'zh' ? '小于等于' : 'Less Than or Equal'}</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">{t.alerts.threshold}</label>
                  <input
                    type="number"
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    required
                    step="0.01"
                    className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                  />
                </div>
              </>
            )}

            <div>
              <label className="text-sm font-medium mb-2 block">{t.locale === 'zh' ? '邮件通知（可选）' : 'Email Notification (Optional)'}</label>
              <input
                type="email"
                value={notifyEmail}
                onChange={(e) => setNotifyEmail(e.target.value)}
                placeholder="example@example.com"
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">{t.locale === 'zh' ? 'Webhook通知（可选）' : 'Webhook Notification (Optional)'}</label>
              <input
                type="url"
                value={notifyWebhook}
                onChange={(e) => setNotifyWebhook(e.target.value)}
                placeholder="https://example.com/webhook"
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              <label htmlFor="enabled" className="text-sm font-medium">
                {t.locale === 'zh' ? '启用此规则' : 'Enable this rule'}
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

