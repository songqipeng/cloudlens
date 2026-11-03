"use client"

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { Badge } from "@/components/ui/badge"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import {
  TrendingDown,
  DollarSign,
  AlertCircle,
  FileText,
  Server,
  ShoppingCart,
  Layers,
  Download,
  ChevronDown,
  ChevronRight,
  RefreshCw,
} from "lucide-react"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"
import { SmartLoadingProgress } from "@/components/loading-progress"
import { ContractPanel } from "@/components/savings/contract-panel"
import type { SavingsOpportunitiesData, SavingsOpportunity } from "@/types/savings"

type MainTab = "overview" | "contract"
type CategoryKey = "framework" | "idle" | "weak" | "other"

const TYPE_META: Record<
  string,
  { label: string; icon: ReactNode; group: CategoryKey }
> = {
  framework_out_of_scope: {
    label: "框外产品",
    icon: <Layers className="w-4 h-4" />,
    group: "framework",
  },
  framework_wrong_purchase: {
    label: "未按约采购",
    icon: <ShoppingCart className="w-4 h-4" />,
    group: "framework",
  },
  idle_low_util: {
    label: "低利用率",
    icon: <Server className="w-4 h-4" />,
    group: "idle",
  },
  weak_subscription: {
    label: "弱建议·转包年",
    icon: <TrendingDown className="w-4 h-4" />,
    group: "weak",
  },
}

const CATEGORY_META: Record<
  CategoryKey,
  { title: string; titleEn: string; desc: string; descEn: string }
> = {
  framework: {
    title: "框架合规",
    titleEn: "Framework",
    desc: "框外产品与未按约采购",
    descEn: "Out of scope & wrong purchase",
  },
  idle: {
    title: "利用率",
    titleEn: "Utilization",
    desc: "低负载与闲置浪费",
    descEn: "Low utilization waste",
  },
  weak: {
    title: "弱建议",
    titleEn: "Weak tips",
    desc: "无合同时的保守转包年建议",
    descEn: "Conservative tips without contract",
  },
  other: {
    title: "其它优化",
    titleEn: "Other",
    desc: "来自旧优化缓存等",
    descEn: "Legacy optimization cache",
  },
}

function formatYen(n?: number) {
  return `¥${Math.round(n || 0).toLocaleString("zh-CN")}`
}

function recentCycles(n = 12): string[] {
  const out: string[] = []
  const d = new Date()
  for (let i = 0; i < n; i++) {
    const x = new Date(d.getFullYear(), d.getMonth() - i, 1)
    out.push(`${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}`)
  }
  return out
}

function groupOf(o: SavingsOpportunity): CategoryKey {
  return TYPE_META[o.type]?.group || "other"
}

function cleanTitle(title: string, typeLabel?: string): string {
  let t = title || ""
  // 去掉「未按约采购：」「框外产品：」等与分组重复的前缀
  t = t.replace(/^(未按约采购|框外产品|低利用率|弱建议[·・]?转包年|长期按量)[:：]\s*/u, "")
  if (typeLabel) {
    const esc = typeLabel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    t = t.replace(new RegExp(`^${esc}[:：]\\s*`, "u"), "")
  }
  return t || title
}

function OpportunityRow({
  o,
  open,
  onToggle,
  zh,
  highLabel,
  mediumLabel,
  lowLabel,
  hideTypeBadge = false,
}: {
  o: SavingsOpportunity
  open: boolean
  onToggle: () => void
  zh: boolean
  highLabel: string
  mediumLabel: string
  lowLabel: string
  hideTypeBadge?: boolean
}) {
  const meta = TYPE_META[o.type] || {
    label: o.category || o.type,
    icon: <AlertCircle className="w-4 h-4" />,
    group: "other" as const,
  }
  const annual = o.annual_savings ?? o.savings_potential ?? 0
  const priorityVariant =
    o.priority === "high" ? "danger" : o.priority === "medium" ? "warning" : "info"
  const priorityLabel =
    o.priority === "high" ? highLabel : o.priority === "medium" ? mediumLabel : lowLabel
  const title = cleanTitle(o.title, meta.label)

  return (
    <div className="border-b border-border/30 last:border-0">
      <button
        type="button"
        className="w-full text-left px-4 py-2.5 hover:bg-muted/30 transition"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="text-muted-foreground shrink-0 opacity-70">{meta.icon}</div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 min-w-0">
                <h4 className="text-sm font-medium truncate">{title}</h4>
                <Badge variant={priorityVariant} size="sm" className="shrink-0">
                  {priorityLabel}
                </Badge>
                {!hideTypeBadge && (
                  <Badge variant="default" size="sm" className="shrink-0 opacity-80">
                    {meta.label}
                  </Badge>
                )}
              </div>
              {!open && (
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{o.description}</p>
              )}
            </div>
          </div>
          <div className="text-right shrink-0 pl-2">
            <div className="text-sm font-semibold text-emerald-600 tabular-nums">
              {formatYen(annual)}
            </div>
          </div>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-3 pl-11 grid md:grid-cols-2 gap-3 text-sm">
          <div>
            <div className="text-[11px] text-muted-foreground mb-1">{zh ? "原因" : "Why"}</div>
            <p className="text-sm text-foreground/90">{o.description || "—"}</p>
            <div className="text-[11px] text-muted-foreground mt-3 mb-1">
              {zh ? "建议动作" : "Recommendation"}
            </div>
            <p>{o.recommendation || o.action || "—"}</p>
          </div>
          <div>
            <div className="text-[11px] text-muted-foreground mb-1">{zh ? "证据" : "Evidence"}</div>
            <pre className="text-[11px] bg-muted/40 rounded-md p-2 overflow-auto max-h-36 whitespace-pre-wrap">
              {JSON.stringify(o.evidence || o.resources?.[0] || {}, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

function ItemList({
  items,
  zh,
  expanded,
  setExpanded,
  highLabel,
  mediumLabel,
  lowLabel,
  preview = 5,
  hideTypeBadge = false,
}: {
  items: SavingsOpportunity[]
  zh: boolean
  expanded: string | null
  setExpanded: (id: string | null) => void
  highLabel: string
  mediumLabel: string
  lowLabel: string
  preview?: number
  hideTypeBadge?: boolean
}) {
  const [showAll, setShowAll] = useState(false)
  const visible = showAll ? items : items.slice(0, preview)
  return (
    <div>
      {visible.map((o) => {
        const id = o.id || `${o.type}-${o.title}`
        return (
          <OpportunityRow
            key={id}
            o={o}
            open={expanded === id}
            onToggle={() => setExpanded(expanded === id ? null : id)}
            zh={zh}
            highLabel={highLabel}
            mediumLabel={mediumLabel}
            lowLabel={lowLabel}
            hideTypeBadge={hideTypeBadge}
          />
        )
      })}
      {items.length > preview && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="w-full text-center text-xs text-muted-foreground hover:text-foreground py-2 border-t border-border/30"
        >
          {showAll
            ? zh
              ? "收起"
              : "Collapse"
            : zh
              ? `还有 ${items.length - preview} 条，点击展开`
              : `Show ${items.length - preview} more`}
        </button>
      )}
    </div>
  )
}

function CategorySection({
  category,
  items,
  defaultOpen,
  zh,
  expanded,
  setExpanded,
  highLabel,
  mediumLabel,
  lowLabel,
}: {
  category: CategoryKey
  items: SavingsOpportunity[]
  defaultOpen: boolean
  zh: boolean
  expanded: string | null
  setExpanded: (id: string | null) => void
  highLabel: string
  mediumLabel: string
  lowLabel: string
}) {
  const [open, setOpen] = useState(defaultOpen)
  const meta = CATEGORY_META[category]
  const total = items.reduce(
    (s, o) => s + (Number(o.annual_savings ?? o.savings_potential) || 0),
    0
  )

  const subgroups = useMemo(() => {
    if (category !== "framework") return null
    const oos = items.filter((o) => o.type === "framework_out_of_scope")
    const wrong = items.filter((o) => o.type === "framework_wrong_purchase")
    return [
      { key: "wrong", title: zh ? "未按约采购" : "Wrong purchase", items: wrong },
      { key: "oos", title: zh ? "框外产品" : "Out of scope", items: oos },
    ].filter((g) => g.items.length > 0)
  }, [category, items, zh])

  if (items.length === 0) return null

  return (
    <section className="rounded-xl border border-border/60 overflow-hidden bg-card/20">
      <button
        type="button"
        className="w-full flex items-center justify-between gap-3 px-4 py-3.5 hover:bg-muted/20 transition text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-3 min-w-0">
          {open ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-sm">{zh ? meta.title : meta.titleEn}</h3>
              <Badge size="sm" variant="default">
                {items.length}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {zh ? meta.desc : meta.descEn}
            </p>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-lg font-bold text-emerald-600 tabular-nums">{formatYen(total)}</div>
          <div className="text-[10px] text-muted-foreground">{zh ? "本组年化" : "group annual"}</div>
        </div>
      </button>
      {open && (
        <div className="border-t border-border/50">
          {subgroups && subgroups.length > 0 ? (
            <div className="divide-y divide-border/40">
              {subgroups.map((g, idx) => (
                <SubGroup
                  key={g.key}
                  title={g.title}
                  items={g.items}
                  defaultOpen={idx === 0}
                  zh={zh}
                  expanded={expanded}
                  setExpanded={setExpanded}
                  highLabel={highLabel}
                  mediumLabel={mediumLabel}
                  lowLabel={lowLabel}
                />
              ))}
            </div>
          ) : (
            <ItemList
              items={items}
              zh={zh}
              expanded={expanded}
              setExpanded={setExpanded}
              highLabel={highLabel}
              mediumLabel={mediumLabel}
              lowLabel={lowLabel}
            />
          )}
        </div>
      )}
    </section>
  )
}

function SubGroup({
  title,
  items,
  defaultOpen,
  zh,
  expanded,
  setExpanded,
  highLabel,
  mediumLabel,
  lowLabel,
}: {
  title: string
  items: SavingsOpportunity[]
  defaultOpen: boolean
  zh: boolean
  expanded: string | null
  setExpanded: (id: string | null) => void
  highLabel: string
  mediumLabel: string
  lowLabel: string
}) {
  const [open, setOpen] = useState(defaultOpen)
  const subTotal = items.reduce(
    (s, o) => s + (Number(o.annual_savings ?? o.savings_potential) || 0),
    0
  )
  return (
    <div>
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-2.5 bg-muted/15 hover:bg-muted/30 transition text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2 text-xs font-medium">
          {open ? (
            <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
          )}
          <span>{title}</span>
          <Badge size="sm" variant="default">
            {items.length}
          </Badge>
        </div>
        <span className="text-xs font-semibold text-emerald-600 tabular-nums">
          {formatYen(subTotal)}
        </span>
      </button>
      {open && (
        <ItemList
          items={items}
          zh={zh}
          expanded={expanded}
          setExpanded={setExpanded}
          highLabel={highLabel}
          mediumLabel={mediumLabel}
          lowLabel={lowLabel}
          hideTypeBadge
          preview={5}
        />
      )}
    </div>
  )
}

export default function OptimizationPage() {
  const { currentAccount, loading: accountLoading } = useAccount()
  const { t, locale } = useLocale()
  const [data, setData] = useState<SavingsOpportunitiesData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingProgress, setLoadingProgress] = useState("")
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [mainTab, setMainTab] = useState<MainTab>("overview")
  const [focusCategory, setFocusCategory] = useState<CategoryKey | "all">("all")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [billingCycle, setBillingCycle] = useState<string>("")
  const [includeLegacy, setIncludeLegacy] = useState(true)
  const loadingStartTime = useRef<number | null>(null)
  const zh = locale === "zh"
  const cycles = useMemo(() => recentCycles(18), [])

  const fetchData = useCallback(
    async (opts?: { force?: boolean }) => {
      if (accountLoading) {
        setLoading(true)
        return
      }
      if (!currentAccount) {
        setLoading(false)
        setData(null)
        setFetchError(null)
        return
      }
      const force = Boolean(opts?.force)
      try {
        setLoading(true)
        setFetchError(null)
        loadingStartTime.current = Date.now()
        setLoadingProgress(zh ? "正在扫描省钱机会…" : "Scanning…")
        const result = await apiGet<{ success: boolean; data: SavingsOpportunitiesData }>(
          "/optimization/savings-opportunities",
          {
            account: currentAccount,
            force_refresh: force,
            include_legacy: includeLegacy,
            ...(billingCycle ? { billing_cycle: billingCycle } : {}),
          },
          { timeout: 180000, retries: 1 } as any
        )
        setData(result?.data || null)
        setLoadingProgress("")
      } catch (e: any) {
        console.error(e)
        const msg = e?.message || (zh ? "加载失败" : "Failed")
        setLoadingProgress(msg)
        setFetchError(msg)
        setData(null)
      } finally {
        setLoading(false)
        setTimeout(() => {
          loadingStartTime.current = null
        }, 400)
      }
    },
    [currentAccount, accountLoading, zh, billingCycle, includeLegacy]
  )

  useEffect(() => {
    fetchData({ force: false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount, accountLoading, billingCycle, includeLegacy])

  const opportunities: SavingsOpportunity[] = useMemo(() => {
    if (!data) return []
    return data.opportunities || data.suggestions || []
  }, [data])

  const grouped = useMemo(() => {
    const buckets: Record<CategoryKey, SavingsOpportunity[]> = {
      framework: [],
      idle: [],
      weak: [],
      other: [],
    }
    for (const o of opportunities) {
      buckets[groupOf(o)].push(o)
    }
    return buckets
  }, [opportunities])

  const summary = data?.summary
  const annualTotal = summary?.annual_savings_total ?? summary?.total_savings_potential ?? 0
  const byType = summary?.by_type_annual_savings || {}
  const frameworkTotal =
    (byType.framework_out_of_scope || 0) + (byType.framework_wrong_purchase || 0)
  const idleTotal = byType.idle_low_util || 0
  const weakTotal = byType.weak_subscription || 0
  const otherTotal = Math.max(0, annualTotal - frameworkTotal - idleTotal - weakTotal)
  const contractConfigured = Boolean(data?.contract?.configured)

  const exportReport = async () => {
    if (!currentAccount) return
    const q = new URLSearchParams({
      account: currentAccount,
      include_legacy: String(includeLegacy),
      force_refresh: "false",
    })
    if (billingCycle) q.set("billing_cycle", billingCycle)
    const host = typeof window !== "undefined" ? window.location.hostname : "localhost"
    const base =
      host === "localhost" || host === "127.0.0.1"
        ? "http://localhost:8000/api"
        : `${window.location.origin}/api`
    try {
      const res = await fetch(`${base}/optimization/savings-report?${q.toString()}`, {
        credentials: "include",
      })
      if (!res.ok) throw new Error(`export ${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `savings-${currentAccount}.html`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error(e)
      window.open(`${base}/optimization/savings-report?${q.toString()}`, "_blank")
    }
  }

  const visibleCategories = (
    ["framework", "idle", "weak", "other"] as CategoryKey[]
  ).filter((k) => {
    if (focusCategory === "all") return true
    if (focusCategory === "weak") return k === "weak" || k === "other"
    return focusCategory === k
  })

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1400px] mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
              {zh ? "省钱机会" : t.optimization.title}
            </h2>
            <p className="text-muted-foreground mt-1 text-sm max-w-2xl">
              {zh
                ? "按类别查看框架合规、利用率与弱建议。金额为年化可省估算。"
                : t.optimization.description}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              className="text-sm rounded-md border px-2.5 py-2 bg-background"
              value={billingCycle}
              onChange={(e) => setBillingCycle(e.target.value)}
              title="选择账期以匹配生效合同"
            >
              <option value="">{zh ? "账期：最新" : "Cycle: latest"}</option>
              {cycles.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <label className="inline-flex items-center gap-1.5 text-xs border rounded-md px-2.5 py-2">
              <input
                type="checkbox"
                checked={includeLegacy}
                onChange={(e) => setIncludeLegacy(e.target.checked)}
              />
              {zh ? "含其它缓存" : "Legacy"}
            </label>
            <button
              type="button"
              onClick={exportReport}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border text-sm hover:bg-muted"
            >
              <Download className="w-4 h-4" />
              {zh ? "导出" : "Export"}
            </button>
            {!loading && (
              <button
                type="button"
                onClick={() => fetchData({ force: true })}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                {t.optimization.refresh}
              </button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border/60">
          {(
            [
              ["overview", zh ? "机会总览" : "Overview", <DollarSign key="i" className="w-3.5 h-3.5" />],
              ["contract", zh ? "框架合同" : "Contracts", <FileText key="i" className="w-3.5 h-3.5" />],
            ] as [MainTab, string, ReactNode][]
          ).map(([key, label, icon]) => (
            <button
              key={key}
              type="button"
              onClick={() => setMainTab(key)}
              className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 -mb-px transition ${
                mainTab === key
                  ? "border-primary text-foreground font-medium"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>

        {!currentAccount && !accountLoading && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900">
            {zh ? "请先在左上角选择云账号。" : "Please select an account."}
          </div>
        )}

        {mainTab === "contract" && currentAccount && (
          <ContractPanel
            account={currentAccount}
            billingCycle={billingCycle || null}
            onChanged={() => fetchData({ force: true })}
          />
        )}

        {mainTab === "overview" && (
          <>
            {currentAccount && (
              <ContractPanel
                account={currentAccount}
                billingCycle={billingCycle || null}
                compact
                onOpenFull={() => setMainTab("contract")}
                onChanged={() => fetchData({ force: true })}
              />
            )}

            {loading || accountLoading ? (
              <SmartLoadingProgress
                message={loadingProgress || (zh ? "正在扫描省钱机会…" : "Scanning…")}
                subMessage={
                  zh ? "首次扫描可能需要较长时间，请稍候" : t.optimization.loadingProgressDesc
                }
                loading={loading || accountLoading}
                startTime={loadingStartTime.current || undefined}
                estimatedDuration={45}
              />
            ) : (
              <>
                {/* KPI — clickable as category focus */}
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {(
                    [
                      {
                        key: "all" as const,
                        label: zh ? "年化可省合计" : "Annual total",
                        value: annualTotal,
                        hint: zh
                          ? `${opportunities.length} 条 · 高 ${summary?.high_priority_count || 0} / 中 ${summary?.medium_priority_count || 0} / 低 ${summary?.low_priority_count || 0}`
                          : `${opportunities.length} opportunities`,
                        accent: "text-emerald-600",
                        show: true,
                      },
                      {
                        key: "framework" as const,
                        label: zh ? "框架合规" : "Framework",
                        value: frameworkTotal,
                        hint: contractConfigured
                          ? `${grouped.framework.length} 条`
                          : zh
                            ? "未配置合同"
                            : "No contract",
                        accent: "text-foreground",
                        show: true,
                      },
                      {
                        key: "idle" as const,
                        label: zh ? "利用率" : "Utilization",
                        value: idleTotal,
                        hint: zh
                          ? `${grouped.idle.length} 条 · 规格粗估`
                          : `${grouped.idle.length} items`,
                        accent: "text-foreground",
                        show: grouped.idle.length > 0 || idleTotal > 0,
                      },
                      {
                        key: "weak" as const,
                        label: zh ? "弱建议 / 其它" : "Weak / Other",
                        value: weakTotal + otherTotal,
                        hint: zh
                          ? `${grouped.weak.length + grouped.other.length} 条`
                          : `${grouped.weak.length + grouped.other.length} items`,
                        accent: "text-foreground",
                        show: grouped.weak.length + grouped.other.length > 0,
                      },
                    ] as const
                  )
                    .filter((kpi) => kpi.show)
                    .map((kpi) => (
                      <button
                        key={kpi.key}
                        type="button"
                        onClick={() =>
                          setFocusCategory((prev) => (prev === kpi.key ? "all" : kpi.key))
                        }
                        className={`text-left rounded-xl border px-4 py-3 transition ${
                          focusCategory === kpi.key
                            ? "border-primary bg-primary/5"
                            : "border-border/60 hover:bg-muted/30"
                        }`}
                      >
                        <div className="text-xs text-muted-foreground">{kpi.label}</div>
                        <div className={`text-2xl font-bold mt-1 tabular-nums ${kpi.accent}`}>
                          {formatYen(kpi.value)}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-1 truncate">
                          {kpi.hint}
                        </div>
                      </button>
                    ))}
                </div>

                {!contractConfigured && !data?.contract?.period_miss && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
                    {zh
                      ? "尚未发布生效的框架合同。当前主要展示利用率与弱建议；在「框架合同」页导入并发布后，可识别框外与未按约。"
                      : "No active framework contract yet."}
                  </div>
                )}
                {data?.contract?.period_miss && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
                    {zh
                      ? `账期 ${billingCycle || data.contract.billing_cycle || ""} 无匹配生效合同。当前仅展示弱建议与利用率。`
                      : `No contract covers billing cycle ${billingCycle || ""}.`}
                  </div>
                )}

                {focusCategory !== "all" && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground">
                      {zh ? "已筛选：" : "Filter: "}
                      {zh
                        ? CATEGORY_META[focusCategory].title
                        : CATEGORY_META[focusCategory].titleEn}
                    </span>
                    <button
                      type="button"
                      className="underline text-muted-foreground hover:text-foreground"
                      onClick={() => setFocusCategory("all")}
                    >
                      {zh ? "清除" : "Clear"}
                    </button>
                  </div>
                )}

                {fetchError ? (
                  <div className="rounded-xl border border-red-500/30 bg-red-500/5 py-14 text-center px-4">
                    <TrendingDown className="w-12 h-12 mx-auto mb-3 opacity-40 text-red-500" />
                    <p className="font-medium">{zh ? "扫描失败" : "Scan failed"}</p>
                    <p className="text-sm text-muted-foreground mt-1">{fetchError}</p>
                    <button
                      type="button"
                      onClick={() => fetchData({ force: true })}
                      className="mt-4 text-sm px-3 py-1.5 rounded-md border hover:bg-muted"
                    >
                      {zh ? "重试" : "Retry"}
                    </button>
                  </div>
                ) : opportunities.length === 0 ? (
                  <div className="rounded-xl border border-border/50 py-14 text-center">
                    <TrendingDown className="w-12 h-12 mx-auto mb-3 opacity-40" />
                    <p className="font-medium">{t.optimization.noSuggestions}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {t.optimization.noSuggestionsDesc}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {visibleCategories.map((cat) => (
                      <CategorySection
                        key={`${cat}-${focusCategory}`}
                        category={cat}
                        items={grouped[cat]}
                        defaultOpen={
                          focusCategory === cat ||
                          (focusCategory === "weak" && (cat === "weak" || cat === "other")) ||
                          (focusCategory === "all" && cat === "framework" && grouped[cat].length > 0)
                        }
                        zh={zh}
                        expanded={expanded}
                        setExpanded={setExpanded}
                        highLabel={t.optimization.highPriority}
                        mediumLabel={t.optimization.mediumPriority}
                        lowLabel={t.optimization.lowPriority}
                      />
                    ))}
                  </div>
                )}

                {summary?.note && (
                  <p className="text-xs text-muted-foreground text-center pt-2">{summary.note}</p>
                )}
              </>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
