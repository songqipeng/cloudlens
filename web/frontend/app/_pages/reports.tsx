"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { FileText, Download, FileSpreadsheet, FileCode, FileType, Sparkles, CheckCircle2, Clock, AlertCircle } from "lucide-react"
import { useAccount } from "@/contexts/account-context"
import { apiPost } from "@/lib/api"

interface ReportType {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  color: string
}

interface ReportFormat {
  id: string
  name: string
  description: string
  icon: React.ReactNode
}

const reportTypes: ReportType[] = [
  {
    id: "comprehensive",
    name: "综合报告",
    description: "包含资源清单、成本分析、安全检查和优化建议的完整报告",
    icon: <FileText className="w-6 h-6" />,
    color: "from-blue-500 to-cyan-500",
  },
  {
    id: "resources",
    name: "资源清单",
    description: "详细的资源列表，包括所有云资源的配置和状态信息",
    icon: <FileSpreadsheet className="w-6 h-6" />,
    color: "from-green-500 to-emerald-500",
  },
  {
    id: "cost",
    name: "成本分析",
    description: "详细的成本分析报告，包括成本趋势、构成和优化建议",
    icon: <FileType className="w-6 h-6" />,
    color: "from-yellow-500 to-orange-500",
  },
  {
    id: "security",
    name: "安全报告",
    description: "安全合规检查报告，包括风险评估和合规性分析",
    icon: <FileCode className="w-6 h-6" />,
    color: "from-red-500 to-pink-500",
  },
]

const reportFormats: ReportFormat[] = [
  {
    id: "excel",
    name: "Excel",
    description: "适合数据分析和进一步处理",
    icon: <FileSpreadsheet className="w-5 h-5" />,
  },
  {
    id: "html",
    name: "HTML",
    description: "精美的网页格式，适合在线查看和分享",
    icon: <FileCode className="w-5 h-5" />,
  },
  {
    id: "pdf",
    name: "PDF",
    description: "专业的文档格式，适合打印和归档",
    icon: <FileText className="w-5 h-5" />,
  },
]

export default function ReportsPage() {
  const { currentAccount } = useAccount()
  const [reportType, setReportType] = useState("comprehensive")
  const [format, setFormat] = useState("excel")
  const [generating, setGenerating] = useState(false)
  const [recentReports, setRecentReports] = useState<any[]>([])

  useEffect(() => {
    // TODO: fetchRecentReports()
  }, [])

  const handleGenerate = async () => {
    if (!currentAccount) {
      alert("请先选择账号")
      return
    }

    setGenerating(true)
    try {
      const data = await apiPost("/reports/generate", {
        type: reportType,
        format: format,
      })

      if (data.success) {
        if (data.data.format === "html") {
          const blob = new Blob([data.data.content], { type: "text/html" })
          const url = URL.createObjectURL(blob)
          const a = document.createElement("a")
          a.href = url
          a.download = `report-${Date.now()}.html`
          a.click()
          URL.revokeObjectURL(url)
        } else if (data.data.download_url) {
          window.open(data.data.download_url, "_blank")
        }

        setTimeout(() => {
          setGenerating(false)
          alert("报告生成成功！")
        }, 500)
        return
      }
      throw new Error("生成失败")
    } catch (e) {
      console.error("Failed to generate report:", e)
      alert("报告生成失败: " + String(e))
    } finally {
      setGenerating(false)
    }
  }

  const selectedType = reportTypes.find((t) => t.id === reportType) || reportTypes[0]
  const selectedFormat = reportFormats.find((f) => f.id === format) || reportFormats[0]

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-8">
        <div className="space-y-2">
          <h2 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-primary to-cyan-500 bg-clip-text text-transparent">报告生成</h2>
          <p className="text-lg text-muted-foreground">生成专业的资源分析报告，支持多种格式和类型</p>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-semibold">选择报告类型</h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {reportTypes.map((type) => (
              <div
                key={type.id}
                onClick={() => setReportType(type.id)}
                className={`relative p-6 rounded-2xl border-2 cursor-pointer transition-all duration-300 group ${
                  reportType === type.id
                    ? `border-primary bg-gradient-to-br ${type.color} text-white shadow-2xl shadow-primary/30 scale-105`
                    : "border-border/50 bg-background/60 backdrop-blur-sm hover:border-primary/50 hover:shadow-xl hover:scale-102"
                }`}
              >
                <div className={`flex items-center gap-3 mb-3 ${reportType === type.id ? "text-white" : "text-foreground"}`}>
                  <div className={`p-2.5 rounded-xl ${reportType === type.id ? "bg-white/20 backdrop-blur-sm" : "bg-primary/10"}`}>{type.icon}</div>
                  <h4 className="text-lg font-bold">{type.name}</h4>
                </div>
                <p className={`text-sm ${reportType === type.id ? "text-white/90" : "text-muted-foreground"}`}>{type.description}</p>
                {reportType === type.id && (
                  <div className="absolute top-3 right-3">
                    <CheckCircle2 className="w-6 h-6 text-white" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <FileType className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-semibold">选择输出格式</h3>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {reportFormats.map((fmt) => (
              <div
                key={fmt.id}
                onClick={() => setFormat(fmt.id)}
                className={`p-5 rounded-xl border-2 cursor-pointer transition-all duration-300 ${
                  format === fmt.id
                    ? "border-primary bg-primary/10 shadow-lg shadow-primary/20 scale-105"
                    : "border-border/50 bg-background/60 backdrop-blur-sm hover:border-primary/50 hover:shadow-md hover:scale-102"
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className={`p-2 rounded-lg ${format === fmt.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{fmt.icon}</div>
                  <h4 className="font-semibold text-lg">{fmt.name}</h4>
                  {format === fmt.id && <CheckCircle2 className="w-5 h-5 text-primary ml-auto" />}
                </div>
                <p className="text-sm text-muted-foreground">{fmt.description}</p>
              </div>
            ))}
          </div>
        </div>

        <Card className="glass border border-border/50 shadow-2xl overflow-hidden">
          <div className="bg-gradient-to-r from-primary/20 via-cyan-500/20 to-primary/20 p-1">
            <div className="bg-background/95 backdrop-blur-sm rounded-lg">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-2xl mb-2">生成报告</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      已选择: <span className="font-semibold text-foreground">{selectedType.name}</span> · 格式:{" "}
                      <span className="font-semibold text-foreground">{selectedFormat.name}</span>
                    </p>
                  </div>
                  <div className={`p-4 rounded-xl bg-gradient-to-br ${selectedType.color} text-white shadow-lg`}>{selectedType.icon}</div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-2 p-4 bg-muted/30 rounded-xl">
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">报告类型</div>
                      <div className="font-semibold flex items-center gap-2">
                        {selectedType.icon}
                        {selectedType.name}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">输出格式</div>
                      <div className="font-semibold flex items-center gap-2">
                        {selectedFormat.icon}
                        {selectedFormat.name}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className={`w-full py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 shadow-lg ${
                      generating
                        ? "bg-muted text-muted-foreground cursor-not-allowed"
                        : `bg-gradient-to-r ${selectedType.color} text-white hover:shadow-2xl hover:scale-[1.02] active:scale-[0.98]`
                    }`}
                  >
                    {generating ? (
                      <div className="flex items-center justify-center gap-3">
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        <span>正在生成报告...</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center gap-3">
                        <Download className="w-5 h-5" />
                        <span>生成并下载报告</span>
                      </div>
                    )}
                  </button>

                  <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                    <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-muted-foreground">
                      <div className="font-medium text-blue-400 mb-1">💡 提示</div>
                      <div>
                        报告生成可能需要几分钟时间，请耐心等待。生成完成后将自动下载。
                        {format === "excel" && " Excel 格式适合数据分析和进一步处理。"}
                        {format === "html" && " HTML 格式包含精美的样式，适合在线查看和分享。"}
                        {format === "pdf" && " PDF 格式适合打印和归档保存。"}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </div>
          </div>
        </Card>

        {recentReports.length > 0 && (
          <Card className="glass border border-border/50 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                最近生成的报告
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {recentReports.map((report, idx) => (
                  <div key={idx} className="p-3 border border-border/50 rounded-lg hover:bg-muted/30 transition-colors">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{report.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {report.type} · {report.format} · {report.created_at}
                        </div>
                      </div>
                      <button className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">下载</button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}




