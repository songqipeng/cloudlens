"use client"

import { useEffect, useMemo, useState, useRef } from "react"
import { Table, TableColumn } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/badge"
import { useRouter } from "next/navigation"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"
import { RabbitLoading } from "@/components/loading"
import { SmartLoadingProgress } from "@/components/loading-progress"
import { Download, Filter, X } from "lucide-react"

interface Resource {
  id: string
  name: string
  type: string
  status: string
  region: string
  spec: string
  cost: number
  tags: Record<string, string>
  created_time: string | null
  vpc_id?: string | null
}

export default function ResourcesPage() {
  const router = useRouter()
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [resources, setResources] = useState<Resource[]>([])
  const [loading, setLoading] = useState(true)
  const [resourceType, setResourceType] = useState("ecs")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [regionFilter, setRegionFilter] = useState<string>("all")
  const [showFilters, setShowFilters] = useState(false)
  const [exporting, setExporting] = useState(false)
  const loadingStartTime = useRef<number | null>(null)

  const base = useMemo(() => {
    return currentAccount ? `/a/${encodeURIComponent(currentAccount)}` : ""
  }, [currentAccount])

  useEffect(() => {
    if (!currentAccount) {
      setLoading(false)
      return
    }
    fetchResources()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resourceType, page, pageSize, currentAccount])

  const fetchResources = async (forceRefresh = false) => {
    if (!currentAccount) return

    setLoading(true)
    loadingStartTime.current = Date.now()
    try {
      const params: Record<string, string> = {
        type: resourceType,
        page: page.toString(),
        pageSize: pageSize.toString(),
      }

      // 对于VPC资源类型，或者强制刷新时，传递force_refresh参数
      if (forceRefresh || resourceType === "vpc") {
        params.force_refresh = "true"
      }

      const data = await apiGet("/resources", params)

      if (data.success) {
        setResources(data.data || [])
        // 安全地访问分页信息，提供默认值
        if (data.pagination) {
          setTotal(data.pagination.total ?? 0)
          setTotalPages(data.pagination.totalPages ?? 0)
        } else {
          // 如果没有分页信息，使用数据长度作为总数
          const resourceCount = data.data?.length ?? 0
          setTotal(resourceCount)
          setTotalPages(Math.ceil(resourceCount / pageSize) || 1)
        }
      } else {
        // 如果请求失败，设置默认值
        setResources([])
        setTotal(0)
        setTotalPages(0)
      }
    } catch (e) {
      console.error("Failed to fetch resources:", e)
    } finally {
      setLoading(false)
      // 延迟清除开始时间，让进度动画完成
      setTimeout(() => {
        loadingStartTime.current = null
      }, 500)
    }
  }

  const columns: TableColumn<Resource>[] = [
    {
      key: "name",
      label: t.resources.nameId,
      sortable: true,
      render: (value, row) => {
        const displayName = row.name && row.name !== "-" ? row.name : (row.id || "-")
        const displayId = row.id || "-"
        return (
          <div>
            <div className="font-medium">{displayName}</div>
            {displayId !== displayName && (
              <div className="text-xs text-muted-foreground font-mono">{displayId}</div>
            )}
          </div>
        )
      },
    },
    {
      key: "type",
      label: t.resources.type,
      render: (value) => {
        const m: Record<string, string> = {
          ecs: "ECS",
          rds: "RDS",
          redis: "Redis",
          vpc: "VPC",
          slb: "SLB",
          nat: "NAT",
          eip: "EIP",
          oss: "OSS",
          disk: "Disk",
          snapshot: "Snapshot",
        }
        return (m[String(value)] || String(value).toUpperCase())
      },
    },
    {
      key: "status",
      label: t.resources.status,
      sortable: true,
      render: (value) => <StatusBadge status={value} />,
    },
    {
      key: "region",
      label: t.resources.region,
      sortable: true,
    },
    {
      key: "vpc_id",
      label: t.resources.vpc,
      render: (value) => (value ? <span className="font-mono text-xs">{value}</span> : "-"),
    },
    {
      key: "spec",
      label: t.resources.spec,
    },
    {
      key: "cost",
      label: t.resources.monthlyCost,
      sortable: true,
      render: (value) => {
        const numValue = typeof value === 'number' ? value : (Number(value) || 0)
        return `¥${numValue.toLocaleString()}`
      },
    },
    {
      key: "created_time",
      label: t.resources.createdTime,
      render: (value) => (value ? new Date(value).toLocaleDateString() : "-"),
    },
  ]

  // 获取所有唯一的区域和状态
  const uniqueRegions = useMemo(() => {
    if (!resources || !Array.isArray(resources)) return []
    const regions = new Set<string>()
    resources.forEach((r) => {
      if (r.region) regions.add(r.region)
    })
    return Array.from(regions).sort()
  }, [resources])

  const uniqueStatuses = useMemo(() => {
    if (!resources || !Array.isArray(resources)) return []
    const statuses = new Set<string>()
    resources.forEach((r) => {
      if (r.status) statuses.add(r.status)
    })
    return Array.from(statuses).sort()
  }, [resources])

  const filteredResources = useMemo(() => {
    if (!resources || !Array.isArray(resources)) return []
    
    let filtered = resources

    // 文本搜索
    if (search) {
      const s = search.toLowerCase()
      filtered = filtered.filter((r) =>
        (r.name?.toLowerCase().includes(s)) || 
        (r.id?.toLowerCase().includes(s)) ||
        (r.region?.toLowerCase().includes(s))
      )
    }

    // 状态筛选
    if (statusFilter !== "all") {
      filtered = filtered.filter((r) => r.status === statusFilter)
    }

    // 区域筛选
    if (regionFilter !== "all") {
      filtered = filtered.filter((r) => r.region === regionFilter)
    }

    return filtered
  }, [resources, search, statusFilter, regionFilter])

  const handleExport = async (format: "csv" | "excel") => {
    if (!currentAccount) return

    setExporting(true)
    try {
      const params = new URLSearchParams({
        type: resourceType,
        format: format,
        account: currentAccount,
      })

      if (search) params.append("filter", search)
      if (statusFilter !== "all") params.append("status", statusFilter)
      if (regionFilter !== "all") params.append("region", regionFilter)

      const url = `/api/resources/export?${params.toString()}`
      window.open(url, "_blank")
    } catch (e) {
      console.error("导出失败:", e)
      alert("导出失败，请稍后重试")
    } finally {
      setExporting(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{t.resources.title}</h2>
            <p className="text-muted-foreground mt-1">{t.resources.description}</p>
          </div>
        </div>

        {loading && loadingStartTime.current && (
          <SmartLoadingProgress
            message={t.common.loading || "正在加载资源列表..."}
            loading={loading}
            startTime={loadingStartTime.current}
          />
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{t.resources.resourceList}</CardTitle>
              <div className="flex gap-2">
                {[
                  { key: "ecs", label: "ECS" },
                  { key: "rds", label: "RDS" },
                  { key: "redis", label: "Redis" },
                  { key: "slb", label: "SLB" },
                  { key: "nat", label: "NAT" },
                  { key: "eip", label: "EIP" },
                  { key: "oss", label: "OSS" },
                  { key: "disk", label: "Disk" },
                  { key: "snapshot", label: "Snapshot" },
                  { key: "vpc", label: "VPC" },
                  { key: "mongodb", label: "MongoDB" },
                  { key: "ack", label: "ACK" },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => {
                      setResourceType(t.key)
                      setPage(1)
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${resourceType === t.key
                      ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                      : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                      }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4 space-y-3">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    placeholder={t.resources.searchPlaceholder || "搜索资源名称、ID 或区域..."}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-input/50 bg-background/60 backdrop-blur-sm text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-sm"
                  />
                  {search && (
                    <button
                      onClick={() => setSearch("")}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-muted rounded"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`px-4 py-2.5 rounded-xl border transition-all ${
                    showFilters || statusFilter !== "all" || regionFilter !== "all"
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background border-input/50 hover:bg-muted"
                  }`}
                >
                  <Filter className="h-4 w-4 inline mr-2" />
                  筛选
                </button>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExport("csv")}
                    disabled={exporting || filteredResources.length === 0}
                    className="px-4 py-2.5 rounded-xl border border-input/50 bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    title="导出为 CSV"
                  >
                    <Download className="h-4 w-4 inline mr-2" />
                    CSV
                  </button>
                  <button
                    onClick={() => handleExport("excel")}
                    disabled={exporting || filteredResources.length === 0}
                    className="px-4 py-2.5 rounded-xl border border-input/50 bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    title="导出为 Excel"
                  >
                    <Download className="h-4 w-4 inline mr-2" />
                    Excel
                  </button>
                </div>
              </div>

              {showFilters && (
                <div className="flex gap-4 p-4 bg-muted/30 rounded-xl border border-input/50">
                  <div className="flex-1">
                    <label className="text-sm font-medium mb-2 block">状态</label>
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-input/50 bg-background text-sm"
                    >
                      <option value="all">全部状态</option>
                      {uniqueStatuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="text-sm font-medium mb-2 block">区域</label>
                    <select
                      value={regionFilter}
                      onChange={(e) => setRegionFilter(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-input/50 bg-background text-sm"
                    >
                      <option value="all">全部区域</option>
                      {uniqueRegions.map((region) => (
                        <option key={region} value={region}>
                          {region}
                        </option>
                      ))}
                    </select>
                  </div>
                  {(statusFilter !== "all" || regionFilter !== "all") && (
                    <div className="flex items-end">
                      <button
                        onClick={() => {
                          setStatusFilter("all")
                          setRegionFilter("all")
                        }}
                        className="px-4 py-2 rounded-lg border border-input/50 bg-background hover:bg-muted text-sm"
                      >
                        清除筛选
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {loading ? (
              <div className="flex items-center justify-center h-64">
                <RabbitLoading delay={3000} />
              </div>
            ) : (
              <>
                <Table
                  data={filteredResources}
                  columns={columns}
                  onRowClick={(row) => {
                    if (!base) return
                    // 保存当前资源类型，以便详情页使用
                    localStorage.setItem('lastResourceType', resourceType)
                    router.push(`${base}/resources/${row.id}?type=${resourceType}`)
                  }}
                />

                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    {filteredResources.length !== total && (
                      <span className="mr-2">
                        显示 {filteredResources.length} / {total} 条
                      </span>
                    )}
                    {t.resources.totalResources
                      ?.replace('{total}', String(total))
                      ?.replace('{page}', String(page))
                      ?.replace('{totalPages}', String(totalPages)) ||
                      `共 ${total} 条，第 ${page}/${totalPages} 页`}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1 || totalPages === 0}
                      className="px-4 py-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {t.resources.previousPage || "上一页"}
                    </button>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages || 1, p + 1))}
                      disabled={page >= (totalPages || 1) || totalPages === 0}
                      className="px-4 py-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {t.resources.nextPage || "下一页"}
                    </button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}











