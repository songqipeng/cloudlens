"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableColumn } from "@/components/ui/table"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"
import { RabbitLoading } from "@/components/loading"
import { SmartLoadingProgress } from "@/components/loading-progress"

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
    const zhe = Number(z)
    // 处理边界情况：0折或负数折显示为"免费"
    if (zhe <= 0) return t.discounts.free
    return `${zhe.toFixed(1)}${t.discounts.discountUnit}`
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
  const loadingStartTime = useRef<number | null>(null)

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
    loadingStartTime.current = Date.now()
    setElapsedSec(0)
    setError(null)
    setStatusText(force ? t.discounts.forceRefreshing || "正在强制刷新..." : t.common.loading || "正在加载...")
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
      setTimeout(() => {
        loadingStartTime.current = null
      }, 500)
    }
  }

  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")

  const rows = useMemo(() => {
    const all = data?.rows || []
    let filtered = all
      .filter((r) => (mode === "all" ? true : String(r.subscription_type) === mode))
      .filter((r) => {
        const q = search.trim().toLowerCase()
        if (!q) return true
        return (
          String(r.product_code || "").toLowerCase().includes(q) ||
          String(r.product_name || "").toLowerCase().includes(q)
        )
      })
    
    // 实现排序
    if (sortKey) {
      filtered = [...filtered].sort((a, b) => {
        const aVal = a[sortKey]
        const bVal = b[sortKey]
        
        // 处理null/undefined
        if (aVal == null && bVal == null) return 0
        if (aVal == null) return 1
        if (bVal == null) return -1
        
        // 数值比较
        const aNum = Number(aVal)
        const bNum = Number(bVal)
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return sortOrder === "asc" ? aNum - bNum : bNum - aNum
        }
        
        // 字符串比较
        const aStr = String(aVal).toLowerCase()
        const bStr = String(bVal).toLowerCase()
        if (sortOrder === "asc") {
          return aStr.localeCompare(bStr)
        } else {
          return bStr.localeCompare(aStr)
        }
      })
    }
    
    return filtered
  }, [data, mode, search, sortKey, sortOrder])
  
  const handleSort = (key: string, order: "asc" | "desc") => {
    setSortKey(key)
    setSortOrder(order)
  }

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
      render: (v, row) => {
        const amount = Number(v || 0)
        // 数据验证：确保折后价不超过原价
        const gross = Number(row.pretax_gross_amount || 0)
        const isValid = amount <= gross
        return (
          <span className={`font-mono ${!isValid ? 'text-destructive' : ''}`} title={!isValid ? '数据异常：折后价超过原价' : ''}>
            {fmtCny(amount)}
          </span>
        )
      },
    },
    {
      key: "discount_amount",
      label: t.discounts.savings,
      sortable: true,
      render: (v, row) => {
        const amount = Number(v || 0)
        // 数据验证：重新计算折扣金额确保准确性
        const gross = Number(row.pretax_gross_amount || 0)
        const pretax = Number(row.pretax_amount || 0)
        const calculatedDiscount = Math.max(0, gross - pretax)
        const isValid = Math.abs(amount - calculatedDiscount) < 0.01 // 允许0.01的误差
        
        return (
          <span 
            className={`font-mono text-primary ${!isValid ? 'opacity-70' : ''}`}
            title={!isValid ? `计算值: ${fmtCny(calculatedDiscount)}` : ''}
          >
            {fmtCny(amount)}
          </span>
        )
      },
    },
    {
      key: "discount_pct",
      label: t.discounts.overallDiscount,
      sortable: true,
      render: (v, row) => {
        // 数据验证：确保折扣金额计算正确
        const gross = Number(row.pretax_gross_amount || 0)
        const pretax = Number(row.pretax_amount || 0)
        const calculatedDiscount = gross > 0 ? gross - pretax : 0
        const calculatedRate = gross > 0 ? (pretax / gross) : null
        
        return (
          <div className="font-mono">
            <div className="font-semibold">{fmtZhe(row.discount_zhe, row.free)}</div>
            <div className="text-[11px] text-muted-foreground">
              {calculatedRate === null ? "-" : `${t.discounts.actualPaymentRate} ${calculatedRate.toFixed(4)}`}
            </div>
            {row.discount_pct !== null && (
              <div className="text-[10px] text-muted-foreground/70 mt-0.5">
                {Number(row.discount_pct).toFixed(2)}% {t.discounts.discountOff || "折扣"}
              </div>
            )}
          </div>
        )
      },
    },
    {
      key: "outstanding_amount",
      label: t.discounts.unpaid,
      sortable: true,
      render: (v) => <span className="font-mono">{fmtCny(Number(v || 0))}</span>,
    },
  ]

  const summary = data?.summary
  
  // 计算筛选后的汇总数据（用于验证）
  const filteredSummary = useMemo(() => {
    if (!rows.length) return null
    const totalGross = rows.reduce((sum, r) => sum + Number(r.pretax_gross_amount || 0), 0)
    const totalPretax = rows.reduce((sum, r) => sum + Number(r.pretax_amount || 0), 0)
    const totalDiscount = rows.reduce((sum, r) => sum + Number(r.discount_amount || 0), 0)
    const rate = totalGross > 0 ? totalPretax / totalGross : null
    return {
      totalGross,
      totalPretax,
      totalDiscount,
      rate,
      zhe: rate !== null && totalPretax > 0 ? rate * 10 : null,
      free: totalGross > 0 && totalPretax === 0
    }
  }, [rows])

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex flex-col gap-2">
          <h2 className="text-3xl font-bold tracking-tight">{t.discounts.title}</h2>
          <p className="text-muted-foreground">{t.discounts.description}</p>
        </div>

        {loading && loadingStartTime.current && (
          <SmartLoadingProgress
            message={statusText || t.common.loading || "正在加载折扣数据..."}
            loading={loading}
            startTime={loadingStartTime.current}
          />
        )}

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
              <div className="text-2xl font-bold text-primary">
                {fmtCny(Number(
                  filteredSummary?.totalDiscount ?? summary?.total_discount_amount ?? 0
                ))}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {t.discounts.overallDiscount}：{fmtZhe(
                  filteredSummary?.zhe ?? summary?.discount_zhe, 
                  filteredSummary?.free ?? summary?.free
                )}
              </div>
              {filteredSummary && mode !== "all" && (
                <div className="text-[10px] text-muted-foreground/70 mt-1">
                  （仅当前筛选）
                </div>
              )}
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
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${mode === t.k
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
              <div className="flex flex-col items-center justify-center h-64 space-y-4">
                <RabbitLoading delay={3000} showText={false} />
                <div className="text-center space-y-2">
                  <div className="animate-pulse text-sm text-muted-foreground">{statusText || t.common.loading}</div>
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
            ) : rows.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <div className="space-y-2">
                  <p className="text-sm font-medium">暂无数据</p>
                  <p className="text-xs">请检查：</p>
                  <ul className="text-xs space-y-1 mt-2 text-left max-w-md mx-auto">
                    <li>• 账期是否正确（格式：YYYY-MM）</li>
                    <li>• 筛选条件是否过于严格</li>
                    <li>• 该账期是否有账单数据</li>
                    <li>• 可以尝试点击"强制刷新"重新获取数据</li>
                  </ul>
                </div>
              </div>
            ) : (
              <Table data={rows} columns={columns} onSort={handleSort} />
            )}
            {rows.length > 0 && (
              <div className="mt-4 pt-4 border-t border-[rgba(255,255,255,0.08)]">
                <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                  <span>共 {rows.length} 条记录</span>
                  {mode !== "all" && (
                    <span>（已筛选：{mode === "Subscription" ? t.discounts.subscription : t.discounts.payAsYouGo}）</span>
                  )}
                  {search && (
                    <span>（搜索："{search}"）</span>
                  )}
                </div>
              </div>
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











