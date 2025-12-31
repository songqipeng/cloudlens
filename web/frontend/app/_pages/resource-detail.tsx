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
  vpc_id?: string | null
  ack_details?: {
    cluster_id: string
    cluster_type: string
    cluster_spec: string
    kubernetes_version: string
    init_version: string
    node_count: number
    created: string
    updated: string
    cluster_domain: string
    timezone: string
    deletion_protection: boolean
    network_mode: string
    proxy_mode: string
    vpc_id: string
    vswitch_id: string
    vswitch_ids: string[]
    security_group_id: string
    external_loadbalancer_id: string
    service_domain_name: string
    service_cidr: string
    master_url: {
      api_server_endpoint?: string
      intranet_api_server_endpoint?: string
      dashboard_endpoint?: string
    }
    resource_group_id: string
    profile: string
    addons: Array<{
      name: string
      version?: string
      config?: string
      disabled?: boolean
    }>
    network_info: {
      network: string
      proxy_mode: string
      node_cidr_mask: string
    }
  }
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
      // 从 URL 参数获取资源类型
      const urlParams = new URLSearchParams(window.location.search)
      const resourceType = urlParams.get('type') || localStorage.getItem('lastResourceType') || 'ecs'
      
      const data = await apiGet(`/resources/${params.id}`, { type: resourceType })
      if (data.success && data.data) {
        // 确保所有必需字段都有默认值
        setResource({
          id: data.data.id || params.id || "",
          name: data.data.name || data.data.id || params.id || "",
          type: data.data.type || resourceType || "unknown",
          status: data.data.status || "Unknown",
          region: data.data.region || "",
          spec: data.data.spec || "-",
          cost: data.data.cost || 0,
          tags: data.data.tags || {},
          created_time: data.data.created_time || null,
          public_ips: data.data.public_ips || [],
          private_ips: data.data.private_ips || [],
          vpc_id: data.data.vpc_id || null,
          ack_details: data.data.ack_details || undefined,
        })
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
                  <dd className="font-medium">
                    {resource.type ? resource.type.toUpperCase() : "未知"}
                  </dd>
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

        {/* ACK 集群详细信息 */}
        {resource.type === "ack" && resource.ack_details && (
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Kubernetes 信息</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3">
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">Kubernetes 版本</dt>
                    <dd className="font-medium">{resource.ack_details.kubernetes_version || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">初始版本</dt>
                    <dd className="font-medium">{resource.ack_details.init_version || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">集群类型</dt>
                    <dd className="font-medium">{resource.ack_details.cluster_type || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">集群规格</dt>
                    <dd className="font-medium">{resource.ack_details.cluster_spec || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">节点数量</dt>
                    <dd className="font-medium">{resource.ack_details.node_count || 0}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">集群域名</dt>
                    <dd className="font-medium font-mono text-xs">{resource.ack_details.cluster_domain || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">时区</dt>
                    <dd className="font-medium">{resource.ack_details.timezone || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">删除保护</dt>
                    <dd className="font-medium">{resource.ack_details.deletion_protection ? "已启用" : "未启用"}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>网络配置</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3">
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">网络模式</dt>
                    <dd className="font-medium">{resource.ack_details.network_mode || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">网络插件</dt>
                    <dd className="font-medium">{resource.ack_details.network_info?.network || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">代理模式</dt>
                    <dd className="font-medium">{resource.ack_details.proxy_mode || resource.ack_details.network_info?.proxy_mode || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">VPC ID</dt>
                    <dd className="font-medium font-mono text-xs">{resource.ack_details.vpc_id || resource.vpc_id || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">主 VSwitch</dt>
                    <dd className="font-medium font-mono text-xs">{resource.ack_details.vswitch_id || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">所有 VSwitch</dt>
                    <dd>
                      {resource.ack_details.vswitch_ids && resource.ack_details.vswitch_ids.length > 0 ? (
                        <div className="space-y-1">
                          {resource.ack_details.vswitch_ids.map((vsw, idx) => (
                            <div key={idx} className="font-mono text-xs">{vsw}</div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">安全组</dt>
                    <dd className="font-medium font-mono text-xs">{resource.ack_details.security_group_id || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">Service CIDR</dt>
                    <dd className="font-medium font-mono text-xs">{resource.ack_details.service_cidr || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">外部负载均衡器</dt>
                    <dd className="font-medium font-mono text-xs">{resource.ack_details.external_loadbalancer_id || "-"}</dd>
                  </div>
                  {resource.ack_details.master_url?.intranet_api_server_endpoint && (
                    <div>
                      <dt className="text-sm text-muted-foreground mb-1">API Server 内网地址</dt>
                      <dd className="font-medium font-mono text-xs">{resource.ack_details.master_url.intranet_api_server_endpoint}</dd>
                    </div>
                  )}
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>插件信息</CardTitle>
              </CardHeader>
              <CardContent>
                {resource.ack_details.addons && resource.ack_details.addons.length > 0 ? (
                  <div className="space-y-2">
                    {resource.ack_details.addons.map((addon, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 bg-muted/30 rounded">
                        <div>
                          <div className="font-medium text-sm">{addon.name}</div>
                          {addon.version && (
                            <div className="text-xs text-muted-foreground">版本: {addon.version}</div>
                          )}
                        </div>
                        {addon.disabled && (
                          <span className="text-xs text-muted-foreground">已禁用</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted-foreground">无插件信息</span>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>其他信息</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3">
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">资源组 ID</dt>
                    <dd className="font-medium font-mono text-xs">{resource.ack_details.resource_group_id || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">Profile</dt>
                    <dd className="font-medium">{resource.ack_details.profile || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">创建时间</dt>
                    <dd className="font-medium">
                      {resource.ack_details.created ? new Date(resource.ack_details.created).toLocaleString() : "-"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground mb-1">更新时间</dt>
                    <dd className="font-medium">
                      {resource.ack_details.updated ? new Date(resource.ack_details.updated).toLocaleString() : "-"}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </div>
        )}

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










