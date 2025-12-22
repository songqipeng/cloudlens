"use client"

import { useEffect, useMemo, useState } from "react"
import { Table, TableColumn } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/badge"
import { useRouter } from "next/navigation"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet } from "@/lib/api"

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
        setResources(data.data)
        setTotal(data.pagination.total)
        setTotalPages(data.pagination.totalPages)
      }
    } catch (e) {
      console.error("Failed to fetch resources:", e)
    } finally {
      setLoading(false)
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
      render: (value) => `¥${value.toLocaleString()}`,
    },
    {
      key: "created_time",
      label: t.resources.createdTime,
      render: (value) => (value ? new Date(value).toLocaleDateString() : "-"),
    },
  ]

  const filteredResources = search
    ? resources.filter((r) => r.name.toLowerCase().includes(search.toLowerCase()) || r.id.toLowerCase().includes(search.toLowerCase()))
    : resources

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{t.resources.title}</h2>
            <p className="text-muted-foreground mt-1">{t.resources.description}</p>
          </div>
        </div>

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
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => {
                      setResourceType(t.key)
                      setPage(1)
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      resourceType === t.key
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
            <div className="mb-4">
              <input
                type="text"
                placeholder={t.resources.searchPlaceholder}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-input/50 bg-background/60 backdrop-blur-sm text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-sm"
              />
            </div>

            {loading ? (
              <div className="flex items-center justify-center h-40">
                <div className="animate-pulse">{t.common.loading}</div>
              </div>
            ) : (
              <>
                <Table
                  data={filteredResources}
                  columns={columns}
                  onRowClick={(row) => {
                    if (!base) return
                    router.push(`${base}/resources/${row.id}`)
                  }}
                />

                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    {t.resources.totalResources.replace('{total}', String(total)).replace('{page}', String(page)).replace('{totalPages}', String(totalPages))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-4 py-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {t.resources.previousPage}
                    </button>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="px-4 py-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {t.resources.nextPage}
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







