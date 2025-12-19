"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useLocale } from "@/contexts/locale-context"
import { LanguageSwitcher } from "@/components/language-switcher"
import { apiGet, apiPost } from "@/lib/api"

export default function SettingsPage() {
  const { t } = useLocale()
  const [rules, setRules] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    apiGet("/config/rules")
      .then((data) => {
        setRules(data)
        setLoading(false)
      })
      .catch((e) => {
        console.error("Failed to fetch rules:", e)
        setLoading(false)
      })
  }, [])

  async function handleSave() {
    setSaving(true)
    try {
      await apiPost("/config/rules", rules)
      alert(t.settings.saveSuccess)
    } catch (e) {
      alert(t.settings.saveFailed + ": " + String(e))
    }
    setSaving(false)
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






