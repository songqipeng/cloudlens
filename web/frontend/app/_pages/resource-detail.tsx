"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/badge"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
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
  public_ips: string[]
  private_ips: string[]
}

interface Metrics {
  metrics: Record<string, number>
  chart_data: {
    cpu: number[]
    memory: number[]
    dates: string[]
  }
}

export default function ResourceDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const [resource, setResource] = useState<Resource | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!params?.id) return
    fetchResource()
    fetchMetrics()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params?.id])

  const fetchResource = async () => {
    try {
      const data = await apiGet(`/resources/${params.id}`)
      if (data.success) {
        setResource(data.data)
      }
    } catch (e) {
      console.error("Failed to fetch resource:", e)
    } finally {
      setLoading(false)
    }
  }

  const fetchMetrics = async () => {
    try {
      const data = await apiGet(`/resources/${params.id}/metrics`, { days: 7 })
      if (data.success) {
        setMetrics(data.data)
      }
    } catch (e) {
      console.error("Failed to fetch metrics:", e)
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-pulse">加载中...</div>
        </div>
      </DashboardLayout>
    )
  }

  if (!resource) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div>资源不存在</div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div>
          <button onClick={() => router.back()} className="mb-4 text-sm text-muted-foreground hover:text-foreground">
            ← 返回
          </button>
          <h1 className="text-3xl font-bold">{resource.name || resource.id}</h1>
          <p className="text-muted-foreground mt-1 font-mono text-sm">{resource.id}</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>基本信息</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">类型</dt>
                  <dd className="font-medium">{resource.type.toUpperCase()}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">状态</dt>
                  <dd>
                    <StatusBadge status={resource.status} />
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">区域</dt>
                  <dd className="font-medium">{resource.region}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">规格</dt>
                  <dd className="font-medium">{resource.spec}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">月度成本</dt>
                  <dd className="font-medium text-primary">¥{resource.cost.toLocaleString()}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">创建时间</dt>
                  <dd className="font-medium">{resource.created_time ? new Date(resource.created_time).toLocaleString() : "-"}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>网络信息</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">公网IP</dt>
                  <dd className="font-medium font-mono">{resource.public_ips.length > 0 ? resource.public_ips.join(", ") : "无"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">内网IP</dt>
                  <dd className="font-medium font-mono">{resource.private_ips.length > 0 ? resource.private_ips.join(", ") : "无"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground mb-1">标签</dt>
                  <dd>
                    {Object.keys(resource.tags).length > 0 ? (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {Object.entries(resource.tags).map(([key, value]) => (
                          <span key={key} className="px-2 py-1 bg-muted rounded text-xs">
                            {key}: {value}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground">无标签</span>
                    )}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>

        {metrics && metrics.chart_data && (
          <Card>
            <CardHeader>
              <CardTitle>监控数据</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={[]}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}










