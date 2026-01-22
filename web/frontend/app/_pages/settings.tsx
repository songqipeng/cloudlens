"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useLocale } from "@/contexts/locale-context"
import { LanguageSwitcher } from "@/components/language-switcher"
import { apiGet, apiPost } from "@/lib/api"
import { toastSuccess, toastError } from "@/components/ui/toast"

interface LLMConfig {
  provider: string
  has_api_key: boolean
  is_active: boolean
}

export default function SettingsPage() {
  const { t, locale } = useLocale()
  const [rules, setRules] = useState<any>(null)
  const [notificationConfig, setNotificationConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingNotifications, setSavingNotifications] = useState(false)

  // LLM配置相关状态
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([])
  const [apiKeys, setApiKeys] = useState({
    claude: '',
    openai: '',
    deepseek: ''
  })
  const [savingLlm, setSavingLlm] = useState(false)

  useEffect(() => {
    Promise.all([
      apiGet("/config/rules"),
      apiGet("/config/notifications"),
      apiGet<LLMConfig[]>("/v1/chatbot/configs")
    ])
      .then(([rulesData, notificationData, llmData]) => {
        setRules(rulesData)
        setNotificationConfig(notificationData)
        setLlmConfigs(llmData)
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

  async function handleSaveLlmConfig() {
    setSavingLlm(true)
    try {
      const promises = Object.entries(apiKeys).map(([provider, api_key]) => {
        if (api_key.trim()) {
          return apiPost('/v1/chatbot/configs', {
            provider,
            api_key,
            is_active: true
          })
        }
        return Promise.resolve()
      })

      await Promise.all(promises)

      // 重新加载配置
      const llmData = await apiGet<LLMConfig[]>("/v1/chatbot/configs")
      setLlmConfigs(llmData)

      // 清空输入框
      setApiKeys({ claude: '', openai: '', deepseek: '' })

      toastSuccess('API密钥配置已保存')
    } catch (e) {
      toastError('保存失败: ' + String(e))
    } finally {
      setSavingLlm(false)
    }
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
          <h2 className="text-3xl font-bold tracking-tight text-foreground">{t.settings.title}</h2>
          <p className="text-muted-foreground mt-1">{t.settings.idleRules.description}</p>
        </div>

        <Card className="glass">
          <CardHeader>
            <CardTitle>{t.settings.idleRules.title}</CardTitle>
            <CardDescription>{t.settings.idleRules.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">{t.settings.idleRules.cpuThreshold}</label>
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
              <p className="text-xs text-muted-foreground">{t.settings.idleRules.cpuThresholdDesc}</p>
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">{t.settings.idleRules.excludeTags}</label>
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
              <p className="text-xs text-muted-foreground">{t.settings.idleRules.excludeTagsDesc}</p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition shadow-lg shadow-primary/20 disabled:opacity-50"
          >
            {saving ? t.settings.saving : t.common.save}
          </button>
        </div>

        {/* 通知配置 */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>{t.settings.notifications.title}</CardTitle>
            <CardDescription>
              {t.settings.notifications.description}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">
                {t.settings.notifications.senderEmail}
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
                {t.settings.notifications.senderEmailDesc}
              </p>
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">
                {t.settings.notifications.authCode}
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
                  {t.settings.notifications.qqMailNote}
                </p>
                <p>
                  {t.settings.notifications.gmailNote}
                </p>
                <p className="mt-2">
                  <a 
                    href="https://service.mail.qq.com/cgi-bin/help?subtype=1&&id=28&&no=1001256" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {t.settings.notifications.qqMailLink}
                  </a>
                </p>
              </div>
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium leading-none">
                {t.settings.notifications.defaultReceiverEmail}
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
                {t.settings.notifications.defaultReceiverEmailDesc}
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
                    {t.settings.notifications.smtpInfo}
                  </p>
                  <div className="text-xs space-y-1 text-muted-foreground">
                    <p>
                      {t.settings.notifications.server}
                      <span className="text-foreground font-mono">{smtpHost}</span>
                    </p>
                    <p>
                      {t.settings.notifications.port}
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
                {savingNotifications ? t.settings.saving : t.common.save}
              </button>
            </div>
          </CardContent>
        </Card>

        {/* LLM API 配置 */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>AI 模型配置</CardTitle>
            <CardDescription>
              配置大语言模型的 API 密钥，用于 AI Chatbot 功能
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4">
              {/* Claude API Key */}
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium leading-none">
                    Anthropic API Key (Claude 3.5 Sonnet)
                  </label>
                  {llmConfigs.find(c => c.provider === 'claude')?.has_api_key && (
                    <span className="text-xs text-green-600 dark:text-green-500 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-green-600 dark:bg-green-500"></span>
                      已配置
                    </span>
                  )}
                </div>
                <input
                  type="password"
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                  value={apiKeys.claude}
                  onChange={(e) => setApiKeys({ ...apiKeys, claude: e.target.value })}
                  placeholder="sk-ant-..."
                />
                <p className="text-xs text-muted-foreground">
                  强大的推理和分析能力，适合复杂问答场景
                </p>
              </div>

              {/* OpenAI API Key */}
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium leading-none">
                    OpenAI API Key (GPT-4)
                  </label>
                  {llmConfigs.find(c => c.provider === 'openai')?.has_api_key && (
                    <span className="text-xs text-green-600 dark:text-green-500 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-green-600 dark:bg-green-500"></span>
                      已配置
                    </span>
                  )}
                </div>
                <input
                  type="password"
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                  value={apiKeys.openai}
                  onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                  placeholder="sk-..."
                />
                <p className="text-xs text-muted-foreground">
                  通用对话和问答，知识面广
                </p>
              </div>

              {/* DeepSeek API Key */}
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium leading-none">
                    DeepSeek API Key
                  </label>
                  {llmConfigs.find(c => c.provider === 'deepseek')?.has_api_key && (
                    <span className="text-xs text-green-600 dark:text-green-500 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-green-600 dark:bg-green-500"></span>
                      已配置
                    </span>
                  )}
                </div>
                <input
                  type="password"
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                  value={apiKeys.deepseek}
                  onChange={(e) => setApiKeys({ ...apiKeys, deepseek: e.target.value })}
                  placeholder="sk-..."
                />
                <p className="text-xs text-muted-foreground">
                  高性价比 AI 模型，适合大量对话场景
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-border/50">
              <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/50 rounded-md">
                <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="text-xs text-blue-800 dark:text-blue-300">
                  <p className="font-medium mb-1">安全说明：</p>
                  <ul className="space-y-1 list-disc list-inside">
                    <li>API 密钥将加密存储在数据库中</li>
                    <li>可以选择配置一个或多个模型的 API 密钥</li>
                    <li>在 AI Chatbot 中可以随时切换使用不同的模型</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={handleSaveLlmConfig}
                disabled={savingLlm}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition shadow-lg shadow-primary/20 disabled:opacity-50"
              >
                {savingLlm ? '保存中...' : '保存配置'}
              </button>
            </div>
          </CardContent>
        </Card>

        {/* 语言设置 */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>{t.settings.language.title}</CardTitle>
            <CardDescription>{t.settings.language.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-2">{t.settings.language.currentLanguage}</p>
                <p className="text-base font-semibold">{locale === 'zh' ? t.settings.language.chinese : t.settings.language.english}</p>
              </div>
              <LanguageSwitcher />
            </div>
          </CardContent>
        </Card>

        {/* 关于信息 */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>{t.settings.about.title}</CardTitle>
            <CardDescription>{t.settings.about.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-sm text-muted-foreground">{t.settings.about.version}</span>
              <span className="text-sm font-semibold text-foreground">CloudLens v2.1</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-sm text-muted-foreground">{t.settings.about.desc}</span>
              <span className="text-sm text-foreground">{t.settings.about.platformName}</span>
            </div>
            <div className="pt-2">
              <p className="text-xs text-muted-foreground">
                {t.settings.about.descriptionText}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}










