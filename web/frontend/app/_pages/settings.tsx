"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useLocale } from "@/contexts/locale-context"
import { LanguageSwitcher } from "@/components/language-switcher"
import { apiGet, apiPost } from "@/lib/api"
import { toastSuccess, toastError } from "@/components/ui/toast"

export default function SettingsPage() {
  const { t } = useLocale()
  const [rules, setRules] = useState<any>(null)
  const [notificationConfig, setNotificationConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingNotifications, setSavingNotifications] = useState(false)

  useEffect(() => {
    Promise.all([
      apiGet("/config/rules"),
      apiGet("/config/notifications")
    ])
      .then(([rulesData, notificationData]) => {
        setRules(rulesData)
        setNotificationConfig(notificationData)
        setLoading(false)
      })
      .catch((e) => {
        console.error("Failed to fetch config:", e)
        setLoading(false)
      })
  }, [])

  async function handleSave() {
    setSaving(true)
    try {
      await apiPost("/config/rules", rules)
      toastSuccess(t.settings.saveSuccess)
    } catch (e) {
      toastError(t.settings.saveFailed + ": " + String(e))
    }
    setSaving(false)
  }

  async function handleSaveNotifications() {
    setSavingNotifications(true)
    try {
      await apiPost("/config/notifications", notificationConfig)
      toastSuccess(t.settings.saveSuccess)
    } catch (e) {
      toastError(t.settings.saveFailed + ": " + String(e))
    }
    setSavingNotifications(false)
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-pulse">{t.common.loading}</div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-8">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground">设置</h2>
          <p className="text-muted-foreground mt-1">配置优化规则和阈值</p>
        </div>

        <Card className="glass">
          <CardHeader>
            <CardTitle>闲置检测规则 (ECS)</CardTitle>
            <CardDescription>定义什么情况下判定为闲置实例</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">CPU阈值 (%)</label>
              <input
                type="number"
                className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                value={rules?.idle_rules?.ecs?.cpu_threshold_percent || 5}
                onChange={(e) => {
                  const newRules = { ...rules }
                  if (!newRules.idle_rules) newRules.idle_rules = {}
                  if (!newRules.idle_rules.ecs) newRules.idle_rules.ecs = {}
                  newRules.idle_rules.ecs.cpu_threshold_percent = parseInt(e.target.value) || 5
                  setRules(newRules)
                }}
              />
              <p className="text-xs text-muted-foreground">平均CPU使用率低于此值的实例将被标记为闲置</p>
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">排除标签 (逗号分隔)</label>
              <input
                type="text"
                className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                value={rules?.idle_rules?.ecs?.exclude_tags?.join(",") || ""}
                onChange={(e) => {
                  const newRules = { ...rules }
                  if (!newRules.idle_rules) newRules.idle_rules = {}
                  if (!newRules.idle_rules.ecs) newRules.idle_rules.ecs = {}
                  newRules.idle_rules.ecs.exclude_tags = e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                  setRules(newRules)
                }}
              />
              <p className="text-xs text-muted-foreground">带有这些标签的资源将被忽略</p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition shadow-lg shadow-primary/20 disabled:opacity-50"
          >
            {saving ? (t.locale === 'zh' ? '保存中...' : 'Saving...') : t.common.save}
          </button>
        </div>

        {/* 通知配置 */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>{t.locale === 'zh' ? '通知配置' : 'Notification Settings'}</CardTitle>
            <CardDescription>
              {t.locale === 'zh' 
                ? '配置邮件通知，用于发送告警通知。系统会根据邮箱类型自动配置SMTP服务器。'
                : 'Configure email notifications for alerts. SMTP server will be auto-configured based on email type.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">
                {t.locale === 'zh' ? '发件邮箱' : 'Sender Email Address'}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="email"
                className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                value={notificationConfig?.email || ""}
                onChange={(e) => {
                  setNotificationConfig({
                    ...notificationConfig,
                    email: e.target.value
                  })
                }}
                placeholder="your-email@qq.com 或 your-email@gmail.com"
              />
              <p className="text-xs text-muted-foreground">
                {t.locale === 'zh' 
                  ? '支持QQ邮箱、Gmail、163邮箱等。系统会自动配置对应的SMTP服务器。'
                  : 'Supports QQ Mail, Gmail, 163 Mail, etc. SMTP server will be auto-configured.'}
              </p>
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">
                {t.locale === 'zh' ? '授权码/密码' : 'Authorization Code / Password'}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="password"
                className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                value={notificationConfig?.auth_code || ""}
                onChange={(e) => {
                  setNotificationConfig({
                    ...notificationConfig,
                    auth_code: e.target.value
                  })
                }}
                placeholder="••••••••"
              />
              <div className="text-xs text-muted-foreground space-y-1">
                <p>
                  {t.locale === 'zh' ? '• QQ邮箱：需要在QQ邮箱设置中开启SMTP服务并获取授权码' : '• QQ Mail: Enable SMTP service in QQ Mail settings and get authorization code'}
                </p>
                <p>
                  {t.locale === 'zh' ? '• Gmail：需要使用应用专用密码（App Password）' : '• Gmail: Use app-specific password (App Password)'}
                </p>
                <p className="mt-2">
                  <a 
                    href="https://service.mail.qq.com/cgi-bin/help?subtype=1&&id=28&&no=1001256" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {t.locale === 'zh' ? 'QQ邮箱如何获取授权码？' : 'How to get QQ Mail authorization code?'}
                  </a>
                </p>
              </div>
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">
                {t.locale === 'zh' ? '默认接收邮箱' : 'Default Receiver Email'}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="email"
                className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                value={notificationConfig?.default_receiver_email || ""}
                onChange={(e) => {
                  setNotificationConfig({
                    ...notificationConfig,
                    default_receiver_email: e.target.value
                  })
                }}
                placeholder="receiver@example.com"
              />
              <p className="text-xs text-muted-foreground">
                {t.locale === 'zh' 
                  ? '告警通知的默认接收邮箱。在创建告警规则时，如果没有指定接收邮箱，将使用此默认邮箱。'
                  : 'Default email address to receive alert notifications. If a rule doesn\'t specify a receiver email, this default will be used.'}
              </p>
            </div>

            {/* 显示自动配置的SMTP信息（只读） */}
            {notificationConfig?.email && (() => {
              const email = notificationConfig.email.toLowerCase().trim()
              let smtpHost = 'smtp.gmail.com'
              let smtpPort = 587
              
              if (email.endsWith('@qq.com')) {
                smtpHost = 'smtp.qq.com'
                smtpPort = 587
              } else if (email.endsWith('@gmail.com')) {
                smtpHost = 'smtp.gmail.com'
                smtpPort = 587
              } else if (email.endsWith('@163.com')) {
                smtpHost = 'smtp.163.com'
                smtpPort = 465
              } else if (email.endsWith('@126.com')) {
                smtpHost = 'smtp.126.com'
                smtpPort = 465
              }
              
              return (
                <div className="p-3 bg-muted/30 rounded-md border border-border/50">
                  <p className="text-xs font-medium mb-2 text-muted-foreground">
                    {t.locale === 'zh' ? '自动配置的SMTP信息：' : 'Auto-configured SMTP settings:'}
                  </p>
                  <div className="text-xs space-y-1 text-muted-foreground">
                    <p>
                      {t.locale === 'zh' ? '服务器：' : 'Server: '}
                      <span className="text-foreground font-mono">{smtpHost}</span>
                    </p>
                    <p>
                      {t.locale === 'zh' ? '端口：' : 'Port: '}
                      <span className="text-foreground font-mono">{smtpPort}</span>
                    </p>
                  </div>
                </div>
              )
            })()}

            <div className="flex justify-end pt-2">
              <button
                onClick={handleSaveNotifications}
                disabled={savingNotifications || !notificationConfig?.email || !notificationConfig?.auth_code}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition shadow-lg shadow-primary/20 disabled:opacity-50"
              >
                {savingNotifications ? (t.locale === 'zh' ? '保存中...' : 'Saving...') : t.common.save}
              </button>
            </div>
          </CardContent>
        </Card>

        {/* 语言设置 */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>{t.locale === 'zh' ? '语言设置' : 'Language Settings'}</CardTitle>
            <CardDescription>{t.locale === 'zh' ? '选择界面显示语言' : 'Select interface display language'}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-2">{t.locale === 'zh' ? '当前语言' : 'Current Language'}</p>
                <p className="text-base font-semibold">{t.locale === 'zh' ? '中文' : 'English'}</p>
              </div>
              <LanguageSwitcher />
            </div>
          </CardContent>
        </Card>

        {/* 关于信息 */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>{t.locale === 'zh' ? '关于' : 'About'}</CardTitle>
            <CardDescription>{t.locale === 'zh' ? 'CloudLens 版本信息' : 'CloudLens Version Information'}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-sm text-muted-foreground">{t.locale === 'zh' ? '版本' : 'Version'}</span>
              <span className="text-sm font-semibold text-foreground">CloudLens v2.1</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-sm text-muted-foreground">{t.locale === 'zh' ? '描述' : 'Description'}</span>
              <span className="text-sm text-foreground">{t.locale === 'zh' ? '多云资源治理平台' : 'Multi-Cloud Resource Governance Platform'}</span>
            </div>
            <div className="pt-2">
              <p className="text-xs text-muted-foreground">
                {t.locale === 'zh' 
                  ? 'CloudLens 是一个企业级多云资源治理与分析工具，帮助您优化云资源使用，降低成本。'
                  : 'CloudLens is an enterprise-grade multi-cloud resource governance and analysis tool that helps you optimize cloud resource usage and reduce costs.'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}






