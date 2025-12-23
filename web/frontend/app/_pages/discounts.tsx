"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableColumn } from "@/components/ui/table"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"

type SubscriptionType = "Subscription" | "PayAsYouGo" | "Unknown"

interface DiscountRow {
  product_code: string
  product_name: string
  subscription_type: SubscriptionType | string
  pretax_gross_amount: number
  pretax_amount: number
  discount_amount: number
  discount_rate: number | null
  discount_pct: number | null
  discount_zhe?: number | null
  free?: boolean
  payment_amount: number
  outstanding_amount: number
  invoice_discount: number
  round_down_discount: number
  deducted_by_coupons: number
  deducted_by_cash_coupons: number
  deducted_by_prepaid_card: number
  currency: string
}

interface DiscountsResponse {
  billing_cycle: string
  summary: {
    total_pretax_gross_amount: number
    total_pretax_amount: number
    total_discount_amount: number
    discount_rate: number | null
    discount_pct: number | null
    discount_zhe?: number | null
    free?: boolean
  }
  rows: DiscountRow[]
}

const fmtCny = (n: number) => `¥${(Number.isFinite(n) ? n : 0).toLocaleString()}`

export default function DiscountsPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  
  const fmtZhe = (z: number | null | undefined, free?: boolean) => {
    if (free) return t.discounts.free
    if (z === null || z === undefined || !Number.isFinite(z)) return "-"
    return `${Number(z).toFixed(1)}${t.discounts.discountUnit}`
  }

  const typeLabel = (tType: string) => {
    if (tType === "Subscription") return t.discounts.subscription
    if (tType === "PayAsYouGo") return t.discounts.payAsYouGo
    return tType || "-"
  }
  const [billingCycle, setBillingCycle] = useState(() => new Date().toISOString().slice(0, 7))
  const [mode, setMode] = useState<"all" | "Subscription" | "PayAsYouGo">("all")
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DiscountsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [statusText, setStatusText] = useState<string>("")
  const [elapsedSec, setElapsedSec] = useState<number>(0)
  const abortRef = useRef<AbortController | null>(null)
  const reqSeqRef = useRef(0)

  useEffect(() => {
    if (!currentAccount) {
      setLoading(false)
      return
    }
    fetchData(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount, billingCycle])

  useEffect(() => {
    if (!loading) return
    const start = Date.now()
    const t = window.setInterval(() => setElapsedSec(Math.floor((Date.now() - start) / 1000)), 500)
    return () => window.clearInterval(t)
  }, [loading])

  const fetchData = async (force: boolean) => {
    // 新请求开始：递增序号，旧请求的回调/错误不再影响 UI
    const reqSeq = ++reqSeqRef.current

    // 终止上一次请求
    abortRef.current?.abort()

    // 绑定本次请求的 controller，避免 setTimeout 误杀“新请求”
    const controller = new AbortController()
    abortRef.current = controller
    const signal = controller.signal
    const startedAt = Date.now()

    setLoading(true)
    setElapsedSec(0)
    setError(null)
    setStatusText(force ? t.discounts.forceRefreshing : t.discounts.loadingCache)
    try {
      const timeoutMs = force ? 60000 : 15000
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
      const res = await apiGet(
        "/billing/discounts",
        { billing_cycle: billingCycle, force_refresh: force ? "true" : "false" },
        { signal }
      )
      window.clearTimeout(timeoutId)
      if (reqSeq === reqSeqRef.current && res?.success) setData(res.data as DiscountsResponse)
    } catch (e: any) {
      console.error("Failed to fetch billing discounts:", e)
      if (e?.name === "AbortError") {
        // 如果是被“新请求”中断（比如你快速切换账期/反复点击），不提示错误
        if (reqSeq !== reqSeqRef.current) return
        const waited = Math.floor((Date.now() - startedAt) / 1000)
        setError(t.discounts.timeoutMessage.replace('{seconds}', String(waited)))
      } else {
        if (reqSeq !== reqSeqRef.current) return
        setError(String(e))
      }
    } finally {
      if (reqSeq !== reqSeqRef.current) return
      setLoading(false)
      setStatusText("")
    }
  }

  const rows = useMemo(() => {
    const all = data?.rows || []
    const filtered = all
      .filter((r) => (mode === "all" ? true : String(r.subscription_type) === mode))
      .filter((r) => {
        const q = search.trim().toLowerCase()
        if (!q) return true
        return (
          String(r.product_code || "").toLowerCase().includes(q) ||
          String(r.product_name || "").toLowerCase().includes(q)
        )
      })
    return filtered
  }, [data, mode, search])

  const columns: TableColumn<DiscountRow>[] = [
    {
      key: "product_name",
      label: t.discounts.product,
      sortable: true,
      render: (value, row) => (
        <div>
          <div className="font-medium">{row.product_name || row.product_code}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.product_code}</div>
        </div>
      ),
    },
    {
      key: "subscription_type",
      label: t.discounts.billingType,
      sortable: true,
      render: (value) => <span className="text-sm">{typeLabel(String(value || ""))}</span>,
    },
    {
      key: "pretax_gross_amount",
      label: t.discounts.originalPrice,
      sortable: true,
      render: (v) => <span className="font-mono">{fmtCny(Number(v || 0))}</span>,
    },
    {
      key: "pretax_amount",
      label: t.discounts.discountedPrice,
      sortable: true,
      render: (v) => <span className="font-mono">{fmtCny(Number(v || 0))}</span>,
    },
    {
      key: "discount_amount",
      label: t.discounts.savings,
      sortable: true,
      render: (v) => <span className="font-mono text-primary">{fmtCny(Number(v || 0))}</span>,
    },
    {
      key: "discount_pct",
      label: t.discounts.overallDiscount,
      sortable: true,
      render: (v, row) => (
        <div className="font-mono">
          <div className="font-semibold">{fmtZhe(row.discount_zhe, row.free)}</div>
          <div className="text-[11px] text-muted-foreground">
            {row.discount_rate === null ? "-" : `${t.discounts.actualPaymentRate} ${Number(row.discount_rate).toFixed(4)}`}
          </div>
        </div>
      ),
    },
    {
      key: "outstanding_amount",
      label: t.discounts.unpaid,
      sortable: true,
      render: (v) => <span className="font-mono">{fmtCny(Number(v || 0))}</span>,
    },
  ]

  const summary = data?.summary

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex flex-col gap-2">
          <h2 className="text-3xl font-bold tracking-tight">{t.discounts.title}</h2>
          <p className="text-muted-foreground">{t.discounts.description}</p>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card className="glass border border-border/50 hover:shadow-xl transition-all">
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">{t.discounts.billingCycle}</CardTitle>
            </CardHeader>
            <CardContent>
              <input
                value={billingCycle}
                onChange={(e) => setBillingCycle(e.target.value)}
                placeholder="YYYY-MM"
                className="w-full px-3 py-2 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm font-mono"
              />
              <div className="text-xs text-muted-foreground mt-2">
                {t.discounts.current}：<span className="font-mono">{data?.billing_cycle || "-"}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="glass border border-border/50 hover:shadow-xl transition-all">
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">{t.discounts.originalPrice}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{fmtCny(Number(summary?.total_pretax_gross_amount || 0))}</div>
            </CardContent>
          </Card>

          <Card className="glass border border-border/50 hover:shadow-xl transition-all">
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">{t.discounts.discountedPrice}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{fmtCny(Number(summary?.total_pretax_amount || 0))}</div>
            </CardContent>
          </Card>

          <Card className="glass border border-border/50 hover:shadow-xl transition-all">
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">{t.discounts.savingsDiscount}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">{fmtCny(Number(summary?.total_discount_amount || 0))}</div>
              <div className="text-xs text-muted-foreground mt-1">{t.discounts.overallDiscount}：{fmtZhe(summary?.discount_zhe, summary?.free)}</div>
            </CardContent>
          </Card>
        </div>

        <Card className="glass border border-border/50 shadow-xl">
          <CardHeader>
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
              <CardTitle>{t.discounts.details}</CardTitle>
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="flex gap-2">
                  {[
                    { k: "all" as const, label: t.discounts.all },
                    { k: "Subscription" as const, label: t.discounts.subscription },
                    { k: "PayAsYouGo" as const, label: t.discounts.payAsYouGo },
                  ].map((t) => (
                    <button
                      key={t.k}
                      onClick={() => setMode(t.k)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        mode === t.k
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                          : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={t.discounts.searchPlaceholder}
                  className="px-4 py-2 rounded-lg border border-border/60 bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm"
                />
                <button
                  onClick={() => fetchData(false)}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-muted/40 transition-colors text-sm"
                >
                  {t.discounts.loadCache}
                </button>
                <button
                  onClick={() => fetchData(true)}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm"
                >
                  {t.discounts.forceRefresh}
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-40">
                <div className="text-center space-y-2">
                  <div className="animate-pulse text-sm">{statusText || t.common.loading}</div>
                  <div className="text-xs text-muted-foreground">{t.discounts.waited.replace('{seconds}', String(elapsedSec))}</div>
                  <button
                    onClick={() => abortRef.current?.abort()}
                    className="mt-2 px-3 py-1.5 rounded-lg border border-border hover:bg-muted/40 transition-colors text-xs"
                  >
                    {t.discounts.cancelRequest}
                  </button>
                </div>
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/10 text-sm">
                <div className="font-medium text-destructive mb-2">{t.discounts.loadFailed}</div>
                <div className="text-muted-foreground break-words">{error}</div>
              </div>
            ) : (
              <Table data={rows} columns={columns} />
            )}
            <div className="text-xs text-muted-foreground mt-3">
              {t.discounts.note}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}









