"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"
import { Plus, Edit, Trash2, Layout, Share2, Search, Settings } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/empty-state"
import { toastError, toastSuccess } from "@/components/ui/toast"

interface WidgetConfig {
  id: string
  type: string
  title: string
  position: { x: number; y: number; w: number; h: number }
  config: Record<string, any>
  data_source?: string | null
}

interface Dashboard {
  id: string
  name: string
  description?: string | null
  widgets: WidgetConfig[]
  layout: string
  account_id?: string | null
  is_shared: boolean
  created_by?: string | null
  created_at?: string
  updated_at?: string
}

export default function CustomDashboardsPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [editingDashboard, setEditingDashboard] = useState<Dashboard | null>(null)
  const [showEditor, setShowEditor] = useState(false)

  useEffect(() => {
    fetchDashboards()
  }, [currentAccount])

  const fetchDashboards = async () => {
    try {
      setLoading(true)
      const response = await apiGet("/dashboards", { account: currentAccount || undefined })
      if (response.success) {
        setDashboards(response.data || [])
      }
    } catch (e) {
      console.error("Failed to fetch dashboards:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (dashboardId: string) => {
    if (!confirm("确定要删除这个仪表盘吗？")) return

    try {
      const response = await apiDelete(`/dashboards/${dashboardId}`)
      if (response.success) {
        setDashboards(dashboards.filter(d => d.id !== dashboardId))
      }
    } catch (e) {
      toastError(t.customDashboards.deleteFailed)
      console.error("Failed to delete dashboard:", e)
    }
  }

  const handleSave = async (dashboardData: any) => {
    try {
      if (editingDashboard) {
        const response = await apiPut(`/dashboards/${editingDashboard.id}`, dashboardData)
        if (response.success) {
          await fetchDashboards()
          setShowEditor(false)
          setEditingDashboard(null)
        }
      } else {
        const response = await apiPost("/dashboards", dashboardData)
        if (response.success) {
          await fetchDashboards()
          setShowEditor(false)
        }
      }
    } catch (e) {
      toastError(t.customDashboards.saveFailed)
      console.error("Failed to save dashboard:", e)
    }
  }

  const filteredDashboards = dashboards.filter(dashboard =>
    dashboard.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-64 w-full" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{t.customDashboards.title}</h2>
            <p className="text-muted-foreground mt-1">{t.customDashboards.description}</p>
          </div>
          <Button
            onClick={() => {
              setEditingDashboard(null)
              setShowEditor(true)
            }}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            {t.customDashboards.createDashboard}
          </Button>
        </div>

        {/* 搜索栏 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t.customDashboards.searchPlaceholder}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
          />
        </div>

        {filteredDashboards.length === 0 ? (
          <EmptyState
            icon={<Layout className="w-16 h-16" />}
            title={searchTerm ? t.customDashboards.noMatchDashboards : t.customDashboards.noDashboards}
            description={searchTerm ? t.customDashboards.tryOtherKeywords : t.customDashboards.noDashboardsDesc}
          />
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredDashboards.map((dashboard) => (
              <Card key={dashboard.id} className="hover:shadow-lg transition-all cursor-pointer group">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-xl group-hover:text-primary transition-colors">
                        {dashboard.name}
                      </CardTitle>
                      {dashboard.description && (
                        <CardDescription className="mt-2">{dashboard.description}</CardDescription>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {dashboard.is_shared && (
                        <Share2 className="h-4 w-4 text-muted-foreground" title="已共享" />
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingDashboard(dashboard)
                          setShowEditor(true)
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(dashboard.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Layout className="h-4 w-4" />
                        {dashboard.layout === "grid" ? "网格布局" : "自由布局"}
                      </span>
                      <span>{dashboard.widgets.length} 个组件</span>
                    </div>
                    
                    {/* Widget预览 */}
                    <div className="grid grid-cols-4 gap-2 p-3 bg-muted/30 rounded-lg">
                      {dashboard.widgets.slice(0, 8).map((widget) => (
                        <div
                          key={widget.id}
                          className="aspect-square bg-primary/10 rounded border border-primary/20 flex items-center justify-center text-xs text-muted-foreground"
                          title={widget.title}
                        >
                          {widget.type === "metric" && "📊"}
                          {widget.type === "chart" && "📈"}
                          {widget.type === "table" && "📋"}
                        </div>
                      ))}
                      {dashboard.widgets.length > 8 && (
                        <div className="aspect-square bg-muted rounded border border-border flex items-center justify-center text-xs text-muted-foreground">
                          +{dashboard.widgets.length - 8}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
                      <span>
                        {dashboard.updated_at
                          ? `更新于 ${new Date(dashboard.updated_at).toLocaleDateString()}`
                          : dashboard.created_at
                          ? `创建于 ${new Date(dashboard.created_at).toLocaleDateString()}`
                          : ""}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          window.location.href = `/custom-dashboards/${dashboard.id}`
                        }}
                      >
                        查看
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* 仪表盘编辑器 */}
        {showEditor && (
          <DashboardEditor
            dashboard={editingDashboard}
            onSave={handleSave}
            onCancel={() => {
              setShowEditor(false)
              setEditingDashboard(null)
            }}
          />
        )}
      </div>
    </DashboardLayout>
  )
}

// 仪表盘编辑器组件
function DashboardEditor({
  dashboard,
  onSave,
  onCancel
}: {
  dashboard: Dashboard | null
  onSave: (data: any) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(dashboard?.name || "")
  const [description, setDescription] = useState(dashboard?.description || "")
  const [layout, setLayout] = useState(dashboard?.layout || "grid")
  const [isShared, setIsShared] = useState(dashboard?.is_shared || false)
  const [widgets, setWidgets] = useState<WidgetConfig[]>(dashboard?.widgets || [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      name,
      description,
      layout,
      widgets,
      is_shared: isShared
    })
  }

  const addWidget = (type: string) => {
    const newWidget: WidgetConfig = {
      id: `widget-${Date.now()}`,
      type,
      title: type === "metric" ? "指标" : type === "chart" ? "图表" : "表格",
      position: { x: 0, y: 0, w: 4, h: 2 },
      config: {}
    }
    setWidgets([...widgets, newWidget])
  }

  const removeWidget = (widgetId: string) => {
    setWidgets(widgets.filter(w => w.id !== widgetId))
  }

  const updateWidget = (widgetId: string, field: keyof WidgetConfig, value: any) => {
    setWidgets(widgets.map(w => 
      w.id === widgetId ? { ...w, [field]: value } : w
    ))
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>{dashboard ? t.customDashboards.editDashboard : t.customDashboards.createDashboard}</CardTitle>
          <CardDescription>配置仪表盘信息和组件</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">仪表盘名称</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">描述</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">布局类型</label>
              <select
                value={layout}
                onChange={(e) => setLayout(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-input/50 bg-background/60 backdrop-blur-sm focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              >
                <option value="grid">网格布局</option>
                <option value="freeform">自由布局</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="isShared"
                checked={isShared}
                onChange={(e) => setIsShared(e.target.checked)}
              />
              <label htmlFor="isShared" className="text-sm font-medium">
                共享仪表盘
              </label>
            </div>

            {/* Widget管理 */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <label className="text-sm font-medium">组件列表</label>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => addWidget("metric")}>
                    + 指标
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={() => addWidget("chart")}>
                    + 图表
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={() => addWidget("table")}>
                    + 表格
                  </Button>
                </div>
              </div>
              <div className="space-y-3">
                {widgets.map((widget) => (
                  <div key={widget.id} className="flex items-center gap-3 p-3 border rounded-lg">
                    <div className="flex-1">
                      <input
                        type="text"
                        value={widget.title}
                        onChange={(e) => updateWidget(widget.id, "title", e.target.value)}
                        className="w-full px-2 py-1 rounded border text-sm"
                        placeholder="组件标题"
                      />
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {widget.type === "metric" && "📊 指标"}
                      {widget.type === "chart" && "📈 图表"}
                      {widget.type === "table" && "📋 表格"}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeWidget(widget.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {widgets.length === 0 && (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    {t.customDashboards.noWidgets}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3">
              <Button type="button" variant="outline" onClick={onCancel}>
                取消
              </Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}


