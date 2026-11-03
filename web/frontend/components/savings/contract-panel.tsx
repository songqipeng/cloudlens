"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { apiDelete, apiGet, apiPost, apiPut, apiUploadForm, ApiError } from "@/lib/api"
import type { FrameworkContract } from "@/types/savings"
import {
  FileUp,
  CheckCircle2,
  Archive,
  RefreshCw,
  AlertTriangle,
  Plus,
  Trash2,
  Download,
  ChevronDown,
  ChevronRight,
  FileText,
} from "lucide-react"

const EMPTY_RULES = {
  framework_discount: 0.5,
  products: [
    {
      label: "ECS 包年包月",
      product_keys: ["云服务器 ECS", "ECS", "云服务器"],
      subscription_required: true,
      allowed_months: [3, 6, 12],
      regions: ["中国香港", "cn-hongkong"],
      instance_families: ["ecs.r8i", "ecs.u1", "ecs.e", "ecs.g7", "ecs.g6e", "ecs.t5", "ecs.hfr9i"],
      exclude_gpu: true,
    },
    {
      label: "RDS 包月",
      product_keys: ["云数据库 RDS", "RDS", "关系型数据库"],
      subscription_required: true,
      allowed_months: [3, 6, 12],
      regions: ["*"],
      instance_families: [],
      exclude_gpu: false,
    },
  ],
}

interface ContractPanelProps {
  account: string
  billingCycle?: string | null
  onChanged?: () => void
  /** 紧凑模式：仅摘要，适合嵌在总览页 */
  compact?: boolean
  onOpenFull?: () => void
}

function statusBadge(status: string) {
  if (status === "active") return <Badge variant="success" size="sm">生效中</Badge>
  if (status === "draft") return <Badge variant="warning" size="sm">草稿</Badge>
  if (status === "archived") return <Badge variant="default" size="sm">已归档</Badge>
  return <Badge size="sm">{status}</Badge>
}

function rulesSummary(rules: FrameworkContract["rules"] | undefined) {
  const products = rules?.products || []
  const discount = rules?.framework_discount
  const labels = products.map((p) => p.label || (p.product_keys || [])[0] || "产品").slice(0, 4)
  const months = Array.from(
    new Set(products.flatMap((p) => p.allowed_months || []))
  ).sort((a, b) => a - b)
  return {
    discountPct: discount != null ? Math.round(Number(discount) * 100) : null,
    productLabels: labels,
    productCount: products.length,
    months,
  }
}

export function ContractPanel({
  account,
  billingCycle,
  onChanged,
  compact = false,
  onOpenFull,
}: ContractPanelProps) {
  const [contracts, setContracts] = useState<FrameworkContract[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [selected, setSelected] = useState<FrameworkContract | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState("")
  const [warnings, setWarnings] = useState<string[]>([])
  const [rulesText, setRulesText] = useState("")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showArchived, setShowArchived] = useState(false)

  const load = useCallback(async () => {
    if (!account) return
    setLoading(true)
    try {
      const res = await apiGet<{
        success: boolean
        data: { contracts: FrameworkContract[]; active_contract_id?: string | null }
      }>("/contracts", { account, billing_cycle: billingCycle || undefined })
      const list = res?.data?.contracts || []
      setContracts(list)
      setActiveId(res?.data?.active_contract_id || null)
      const pick =
        list.find((c) => c.id === res?.data?.active_contract_id) ||
        list.find((c) => c.status === "draft") ||
        list[0] ||
        null
      setSelected(pick)
      setRulesText(pick ? JSON.stringify(pick.rules || {}, null, 2) : "")
      setWarnings(pick?.parse_meta?.warnings || [])
    } catch (e) {
      console.error(e)
      setMessage(e instanceof ApiError ? e.message : "加载合同失败")
    } finally {
      setLoading(false)
    }
  }, [account, billingCycle])

  useEffect(() => {
    load()
  }, [load])

  const active = useMemo(
    () => contracts.find((c) => c.id === activeId) || null,
    [contracts, activeId]
  )
  const drafts = useMemo(() => contracts.filter((c) => c.status === "draft"), [contracts])
  const archived = useMemo(
    () => contracts.filter((c) => c.status === "archived"),
    [contracts]
  )
  const editableList = useMemo(
    () => contracts.filter((c) => c.status !== "archived" || showArchived),
    [contracts, showArchived]
  )

  const onUpload = async (file: File | null) => {
    if (!file || !account) return
    setUploading(true)
    setMessage("")
    try {
      const fd = new FormData()
      fd.append("account", account)
      fd.append("file", file)
      const res = await apiUploadForm<{
        success: boolean
        data: { contract: FrameworkContract; warnings?: string[]; message?: string }
      }>("/contracts/parse-pdf", fd)
      setMessage(res?.data?.message || "已解析为草稿，请确认后发布")
      setWarnings(res?.data?.warnings || [])
      await load()
      if (res?.data?.contract) {
        setSelected(res.data.contract)
        setRulesText(JSON.stringify(res.data.contract.rules || {}, null, 2))
        setShowAdvanced(true)
      }
      onChanged?.()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "PDF 解析失败")
    } finally {
      setUploading(false)
    }
  }

  const createManual = async () => {
    try {
      const res = await apiPost<{ success: boolean; data: FrameworkContract }>(
        "/contracts",
        {
          title: "手工框架规则",
          status: "draft",
          priority: 0,
          rules: EMPTY_RULES,
          notes: "手工创建，请按合同附件一补全",
        },
        { account }
      )
      setMessage("已创建手工草稿")
      await load()
      if (res?.data) {
        setSelected(res.data)
        setRulesText(JSON.stringify(res.data.rules || EMPTY_RULES, null, 2))
        setShowAdvanced(true)
      }
      onChanged?.()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "创建失败")
    }
  }

  const saveRules = async () => {
    if (!selected) return
    try {
      const rules = JSON.parse(rulesText)
      await apiPut(`/contracts/${selected.id}`, {
        rules,
        title: selected.title,
        contract_no: selected.contract_no,
        cloud_uid: selected.cloud_uid,
        effective_from: selected.effective_from,
        effective_to: selected.effective_to,
        priority: selected.priority,
        notes: selected.notes,
      })
      setMessage("规则已保存")
      await load()
      onChanged?.()
    } catch (e) {
      setMessage(e instanceof Error ? `保存失败: ${e.message}` : "保存失败")
    }
  }

  const publish = async () => {
    if (!selected) return
    try {
      try {
        const rules = JSON.parse(rulesText)
        await apiPut(`/contracts/${selected.id}`, {
          rules,
          title: selected.title,
          contract_no: selected.contract_no,
          cloud_uid: selected.cloud_uid,
          effective_from: selected.effective_from,
          effective_to: selected.effective_to,
          priority: selected.priority,
          notes: selected.notes,
        })
      } catch {
        /* publish 会再校验 */
      }
      await apiPost(`/contracts/${selected.id}/publish`, {})
      setMessage("已发布；同账号其它生效合同已归档")
      await load()
      onChanged?.()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "发布失败")
    }
  }

  const archive = async () => {
    if (!selected) return
    try {
      await apiPost(`/contracts/${selected.id}/archive`, {})
      setMessage("已归档")
      await load()
      onChanged?.()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "归档失败")
    }
  }

  const remove = async () => {
    if (!selected) return
    if (!window.confirm(`确认删除合同「${selected.title || selected.id}」？`)) return
    try {
      await apiDelete(`/contracts/${selected.id}`)
      setMessage("已删除")
      setSelected(null)
      await load()
      onChanged?.()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "删除失败")
    }
  }

  const downloadPdf = () => {
    if (!selected?.id || !selected.source_pdf_name) return
    const host = typeof window !== "undefined" ? window.location.hostname : "localhost"
    const base =
      host === "localhost" || host === "127.0.0.1"
        ? "http://localhost:8000/api"
        : `${window.location.origin}/api`
    window.open(`${base}/contracts/${selected.id}/pdf`, "_blank")
  }

  const summaryFor = (c: FrameworkContract | null) => rulesSummary(c?.rules)
  // compact 条用生效合同；详情区必须用当前选中合同，避免草稿摘要绑错
  const activeSummary = summaryFor(active)
  const selectedSummary = summaryFor(selected)

  if (compact) {
    return (
      <div className="rounded-xl border border-border/60 bg-card/40 px-4 py-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0 flex items-start gap-3">
            <div className="mt-0.5 rounded-lg bg-emerald-500/10 p-2 text-emerald-600">
              <FileText className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold">框架合同</span>
                {loading ? (
                  <Badge variant="default" size="sm">加载中</Badge>
                ) : active ? (
                  statusBadge("active")
                ) : (
                  <Badge variant="warning" size="sm">未配置</Badge>
                )}
              </div>
              {loading ? (
                <p className="text-sm text-muted-foreground mt-0.5">正在加载合同状态…</p>
              ) : active ? (
                <>
                  <p className="text-sm mt-0.5 truncate">
                    {active.title || "框架服务协议"}
                    {active.contract_no ? (
                      <span className="text-muted-foreground"> · {active.contract_no}</span>
                    ) : null}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {(active.effective_from || "?").toString().slice(0, 10)} ~{" "}
                    {(active.effective_to || "?").toString().slice(0, 10)}
                    {activeSummary.discountPct != null ? ` · 约 ${activeSummary.discountPct}% 优惠` : ""}
                    {activeSummary.productCount
                      ? ` · ${activeSummary.productCount} 类产品`
                      : ""}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground mt-0.5">
                  导入 PDF 并发布后，可识别框外产品与未按约采购
                  {drafts.length ? `（有 ${drafts.length} 份草稿待确认）` : ""}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground cursor-pointer hover:bg-primary/90">
              <FileUp className="w-3.5 h-3.5" />
              {uploading ? "解析中…" : "导入 PDF"}
              <input
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                disabled={uploading || !account}
                onChange={(e) => onUpload(e.target.files?.[0] || null)}
              />
            </label>
            <button
              type="button"
              onClick={onOpenFull}
              className="text-xs px-3 py-1.5 rounded-md border hover:bg-muted"
            >
              管理合同
            </button>
          </div>
        </div>
        {message && (
          <p className="text-xs text-muted-foreground mt-2 border-t border-border/40 pt-2">{message}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-base font-semibold">框架合同管理</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            优先导入 PDF 预填 → 核对后发布。账期 {billingCycle || "最新"} 用于匹配生效合同。
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => load()}
            className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border hover:bg-muted"
          >
            <RefreshCw className="w-3.5 h-3.5" /> 刷新
          </button>
          <button
            type="button"
            onClick={createManual}
            className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border hover:bg-muted"
          >
            <Plus className="w-3.5 h-3.5" /> 手工新建
          </button>
          <label className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground cursor-pointer hover:bg-primary/90">
            <FileUp className="w-3.5 h-3.5" />
            {uploading ? "解析中…" : "导入 PDF"}
            <input
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              disabled={uploading || !account}
              onChange={(e) => onUpload(e.target.files?.[0] || null)}
            />
          </label>
        </div>
      </div>

      {message && (
        <div className="text-xs rounded-lg border border-border/60 bg-muted/30 px-3 py-2">{message}</div>
      )}
      {warnings.length > 0 && (
        <div className="text-xs rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-amber-800 space-y-1">
          <div className="flex items-center gap-1 font-medium">
            <AlertTriangle className="w-3.5 h-3.5" /> 解析提示（请人工确认）
          </div>
          {warnings.map((w) => (
            <div key={w}>· {w}</div>
          ))}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground py-8 text-center">加载合同…</p>
      ) : contracts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/70 px-6 py-10 text-center">
          <FileText className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="font-medium text-sm">尚未导入合同</p>
          <p className="text-xs text-muted-foreground mt-1">
            导入框架合同 PDF，或手工新建规则后再发布
          </p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-[240px_1fr] gap-4">
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground px-1">
              版本列表
            </div>
            <div className="space-y-1.5 max-h-[420px] overflow-auto pr-1">
              {editableList.map((c) => {
                const sum = rulesSummary(c.rules)
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => {
                      setSelected(c)
                      setRulesText(JSON.stringify(c.rules || {}, null, 2))
                      setWarnings(c.parse_meta?.warnings || [])
                      setShowAdvanced(false)
                    }}
                    className={`w-full text-left rounded-lg px-3 py-2.5 text-xs transition border ${
                      selected?.id === c.id
                        ? "border-primary bg-primary/5"
                        : "border-transparent hover:bg-muted/50"
                    }`}
                  >
                    <div className="font-medium truncate">{c.title || c.contract_no || c.id}</div>
                    <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                      {statusBadge(c.status)}
                      {activeId === c.id && (
                        <span className="text-emerald-600 text-[10px]">扫描用</span>
                      )}
                    </div>
                    <div className="text-muted-foreground mt-1">
                      {(c.effective_from || "?").toString().slice(0, 10)} ~{" "}
                      {(c.effective_to || "?").toString().slice(0, 10)}
                    </div>
                    {sum.productCount > 0 && (
                      <div className="text-muted-foreground mt-0.5 truncate">
                        {sum.productLabels.join("、")}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
            {archived.length > 0 && (
              <button
                type="button"
                onClick={() => setShowArchived((v) => !v)}
                className="text-[11px] text-muted-foreground hover:text-foreground px-1"
              >
                {showArchived ? "隐藏" : "显示"}已归档（{archived.length}）
              </button>
            )}
          </div>

          {selected && (
            <div className="rounded-xl border border-border/60 bg-card/30 p-4 space-y-4">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-semibold">{selected.title || "未命名合同"}</h4>
                    {statusBadge(selected.status)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {selected.contract_no || "无合同号"}
                    {selected.cloud_uid ? ` · UID ${selected.cloud_uid}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selected.status !== "active" && (
                    <button
                      type="button"
                      onClick={publish}
                      className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> 确认发布
                    </button>
                  )}
                  {selected.status === "active" && (
                    <button
                      type="button"
                      onClick={archive}
                      className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border hover:bg-muted"
                    >
                      <Archive className="w-3.5 h-3.5" /> 归档
                    </button>
                  )}
                  {selected.source_pdf_name && (
                    <button
                      type="button"
                      onClick={downloadPdf}
                      className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border hover:bg-muted"
                    >
                      <Download className="w-3.5 h-3.5" /> PDF
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={remove}
                    className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border border-red-500/30 text-red-600 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> 删除
                  </button>
                </div>
              </div>

              {/* 结构化摘要：跟随当前选中合同 */}
              <div className="grid sm:grid-cols-3 gap-3">
                <div className="rounded-lg bg-muted/30 px-3 py-2">
                  <div className="text-[11px] text-muted-foreground">框架优惠</div>
                  <div className="text-lg font-semibold mt-0.5">
                    {selectedSummary.discountPct != null
                      ? `${selectedSummary.discountPct}%`
                      : "—"}
                  </div>
                </div>
                <div className="rounded-lg bg-muted/30 px-3 py-2">
                  <div className="text-[11px] text-muted-foreground">覆盖产品</div>
                  <div className="text-sm font-medium mt-0.5 line-clamp-2">
                    {selectedSummary.productLabels.join("、") || "未配置"}
                  </div>
                </div>
                <div className="rounded-lg bg-muted/30 px-3 py-2">
                  <div className="text-[11px] text-muted-foreground">允许时长</div>
                  <div className="text-sm font-medium mt-0.5">
                    {selectedSummary.months.length
                      ? selectedSummary.months.map((m) => `${m}月`).join(" / ")
                      : "—"}
                  </div>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-2 text-xs">
                <label className="space-y-1">
                  <span className="text-muted-foreground">标题</span>
                  <input
                    className="w-full rounded-md border px-2 py-1.5 bg-background"
                    value={selected.title || ""}
                    onChange={(e) => setSelected({ ...selected, title: e.target.value })}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-muted-foreground">合同号</span>
                  <input
                    className="w-full rounded-md border px-2 py-1.5 bg-background"
                    value={selected.contract_no || ""}
                    onChange={(e) => setSelected({ ...selected, contract_no: e.target.value })}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-muted-foreground">生效起</span>
                  <input
                    className="w-full rounded-md border px-2 py-1.5 bg-background"
                    value={(selected.effective_from || "").toString().slice(0, 10)}
                    onChange={(e) => setSelected({ ...selected, effective_from: e.target.value })}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-muted-foreground">生效止</span>
                  <input
                    className="w-full rounded-md border px-2 py-1.5 bg-background"
                    value={(selected.effective_to || "").toString().slice(0, 10)}
                    onChange={(e) => setSelected({ ...selected, effective_to: e.target.value })}
                  />
                </label>
              </div>

              <button
                type="button"
                onClick={saveRules}
                className="text-xs px-3 py-1.5 rounded-md border hover:bg-muted"
              >
                保存元数据 / 规则
              </button>

              <button
                type="button"
                onClick={() => setShowAdvanced((v) => !v)}
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {showAdvanced ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
                高级：编辑规则 JSON / UID / 优先级
              </button>

              {showAdvanced && (
                <div className="space-y-3 border-t border-border/40 pt-3">
                  <div className="grid sm:grid-cols-2 gap-2 text-xs">
                    <label className="space-y-1">
                      <span className="text-muted-foreground">云账号 UID</span>
                      <input
                        className="w-full rounded-md border px-2 py-1.5 bg-background"
                        value={selected.cloud_uid || ""}
                        onChange={(e) => setSelected({ ...selected, cloud_uid: e.target.value })}
                      />
                    </label>
                    <label className="space-y-1">
                      <span className="text-muted-foreground">优先级</span>
                      <input
                        type="number"
                        className="w-full rounded-md border px-2 py-1.5 bg-background"
                        value={selected.priority ?? 0}
                        onChange={(e) =>
                          setSelected({ ...selected, priority: Number(e.target.value) || 0 })
                        }
                      />
                    </label>
                  </div>
                  <textarea
                    className="w-full h-44 font-mono text-[11px] rounded-md border px-2 py-2 bg-background"
                    value={rulesText}
                    onChange={(e) => setRulesText(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={saveRules}
                    className="text-xs px-3 py-1.5 rounded-md border hover:bg-muted"
                  >
                    保存规则
                  </button>
                  <p className="text-[11px] text-muted-foreground">
                    regions 支持 *；exclude_gpu 排除 GPU；allowed_months / instance_families
                    决定未按约判定。
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
