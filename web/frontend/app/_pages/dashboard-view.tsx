"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiGet, apiPut } from "@/lib/api"
import { ArrowLeft, Edit, Save, X } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { MetricWidget, ChartWidget, TableWidget } from "@/components/widgets"
import { toastError, toastSuccess } from "@/components/ui/toast"

// 动态导入react-grid-layout（客户端组件）
let GridLayout: any = null
if (typeof window !== "undefined") {
  try {
    GridLayout = require("react-grid-layout").default
    require("react-grid-layout/css/styles.css")
    require("react-resizable/css/styles.css")
  } catch (e) {
    console.warn("react-grid-layout not available")
  }
}

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
  created_at?: string
  updated_at?: string
}

export default function DashboardViewPage() {
  const params = useParams()
  const router = useRouter()
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const dashboardId = params?.id as string
  
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [layout, setLayout] = useState<any[]>([])
  const [widgetData, setWidgetData] = useState<Record<string, any>>({})

  useEffect(() => {
    if (dashboardId) {
      fetchDashboard()
    }
  }, [dashboardId])

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      const response = await apiGet(`/dashboards/${dashboardId}`)
      if (response.success) {
        const dash = response.data
        setDashboard(dash)
        
        // 转换为react-grid-layout格式
        const gridLayout = dash.widgets.map((widget: WidgetConfig) => ({
          i: widget.id,
          x: widget.position.x,
          y: widget.position.y,
          w: widget.position.w,
          h: widget.position.h,
          minW: 2,
          minH: 2
        }))
        setLayout(gridLayout)
        
        // 获取widget数据
        await fetchWidgetData(dash.widgets)
      }
    } catch (e) {
      console.error("Failed to fetch dashboard:", e)
    } finally {
      setLoading(false)
    }
  }

  const fetchWidgetData = async (widgets: WidgetConfig[]) => {
    if (!currentAccount) return
    
    const data: Record<string, any> = {}
    
    for (const widget of widgets) {
      try {
        if (widget.type === "metric") {
          // 获取指标数据
          const response = await apiGet("/dashboard/summary", { account: currentAccount })
          if (response.success) {
            const metric = widget.config.metric || "total_cost"
            const value = response[metric] || response.total_cost || 0
            
            // 计算趋势（如果有历史数据）
            let trend = undefined
            if (widget.config.showTrend) {
              // TODO: 获取历史数据计算趋势
            }
            
            data[widget.id] = {
              value,
              format: widget.config.format || "currency",
              trend
            }
          }
        } else if (widget.type === "chart") {
          // 获取图表数据
          const dataSource = widget.data_source || "cost_trend"
          
          if (dataSource === "cost_trend") {
            const response = await apiGet("/dashboard/trend", { account: currentAccount, days: 30 })
            if (response.success && response.chart_data) {
              data[widget.id] = response.chart_data
            }
          } else if (dataSource === "cost_breakdown") {
            const response = await apiGet("/cost/breakdown", { account: currentAccount })
            if (response.success && response.data) {
              // 转换为图表数据格式
              data[widget.id] = Object.entries(response.data).map(([name, value]) => ({
                name,
                value: Number(value)
              }))
            }
          }
        } else if (widget.type === "table") {
          // 获取表格数据
          const dataSource = widget.data_source || "resources"
          
          if (dataSource === "idle_resources") {
            const response = await apiGet("/dashboard/idle", { account: currentAccount })
            if (response.success) {
              data[widget.id] = response.data || response || []
            }
          }
        }
      } catch (e) {
        console.error(`Failed to fetch data for widget ${widget.id}:`, e)
      }
    }
    
    setWidgetData(data)
  }

  const handleLayoutChange = (newLayout: any[]) => {
    if (editing) {
      setLayout(newLayout)
    }
  }

  const handleSave = async () => {
    if (!dashboard) return

    try {
      // 更新widget位置
      const updatedWidgets = dashboard.widgets.map(widget => {
        const layoutItem = layout.find(l => l.i === widget.id)
        if (layoutItem) {
          return {
            ...widget,
            position: {
              x: layoutItem.x,
              y: layoutItem.y,
              w: layoutItem.w,
              h: layoutItem.h
            }
          }
        }
        return widget
      })

      const response = await apiPut(`/dashboards/${dashboard.id}`, {
        name: dashboard.name,
        description: dashboard.description,
        layout: dashboard.layout,
        widgets: updatedWidgets,
        is_shared: dashboard.is_shared
      })

      if (response.success) {
        setEditing(false)
        await fetchDashboard()
      }
    } catch (e) {
      toastError(t.dashboardView.saveFailed)
      console.error("Failed to save dashboard:", e)
    }
  }


  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-96 w-full" />
        </div>
      </DashboardLayout>
    )
  }

  if (!dashboard) {
    return (
      <DashboardLayout>
        <div className="p-6 md:p-8 max-w-[1600px] mx-auto">
          <Card>
            <CardContent className="p-12 text-center">
              <p className="text-muted-foreground">{t.dashboardView.dashboardNotFound}</p>
              <Button onClick={() => router.push("/custom-dashboards")} className="mt-4">
                {t.dashboardView.backToList}
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-6">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/custom-dashboards")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回
            </Button>
            <div>
              <h2 className="text-3xl font-bold tracking-tight">{dashboard.name}</h2>
              {dashboard.description && (
                <p className="text-muted-foreground mt-1">{dashboard.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <Button variant="outline" onClick={() => setEditing(false)}>
                  <X className="h-4 w-4 mr-2" />
                  取消
                </Button>
                <Button onClick={handleSave}>
                  <Save className="h-4 w-4 mr-2" />
                  保存
                </Button>
              </>
            ) : (
              <Button variant="outline" onClick={() => setEditing(true)}>
                <Edit className="h-4 w-4 mr-2" />
                编辑布局
              </Button>
            )}
          </div>
        </div>

        {/* 仪表盘内容 */}
        <div className="relative">
          {editing && (
            <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-500">
              {t.dashboardView.editModeHint}
            </div>
          )}
          
          {GridLayout ? (
            <GridLayout
              className="layout"
              layout={layout}
              cols={12}
              rowHeight={60}
              width={1200}
              onLayoutChange={handleLayoutChange}
              isDraggable={editing}
              isResizable={editing}
              draggableHandle={editing ? undefined : ".no-drag"}
            >
              {dashboard.widgets.map((widget) => (
                <div key={widget.id} className={editing ? "" : "no-drag"}>
                  <WidgetCard
                    widget={widget}
                    widgetData={widgetData}
                  />
                </div>
              ))}
            </GridLayout>
          ) : (
            // 简化版本：使用CSS Grid（当GridLayout未加载时）
            <div className="grid grid-cols-12 gap-4 auto-rows-fr">
              {dashboard.widgets.map((widget) => (
                <div
                  key={widget.id}
                  style={{
                    gridColumn: `span ${widget.position.w}`,
                    gridRow: `span ${widget.position.h}`
                  }}
                >
                  <WidgetCard
                    widget={widget}
                    widgetData={widgetData}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}

// Widget卡片组件
function WidgetCard({
  widget,
  widgetData
}: {
  widget: WidgetConfig
  widgetData: Record<string, any>
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-lg">{widget.title}</CardTitle>
      </CardHeader>
                  <CardContent>
                    {widget.type === "metric" && (
                      <MetricWidget
                        title={widget.title}
                        value={widgetData[widget.id]?.value || 0}
                        format={widget.config.format || "number"}
                        trend={widgetData[widget.id]?.trend}
                        subtitle={widget.config.subtitle}
                      />
                    )}
                    {widget.type === "chart" && (
                      <ChartWidget
                        title={widget.title}
                        type={widget.config.chart_type || "area"}
                        data={widgetData[widget.id]}
                        config={widget.config}
                      />
                    )}
                    {widget.type === "table" && (
                      <TableWidget
                        title={widget.title}
                        data={widgetData[widget.id] || []}
                        columns={widget.config.columns}
                        pageSize={widget.config.pageSize || 10}
                      />
                    )}
                  </CardContent>
    </Card>
  )
}







