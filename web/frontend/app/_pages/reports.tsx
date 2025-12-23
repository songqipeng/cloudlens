"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { FileText, Download, FileSpreadsheet, FileCode, FileType, Sparkles, CheckCircle2, Clock, AlertCircle } from "lucide-react"
import { useAccount } from "@/contexts/account-context"
import { useLocale } from "@/contexts/locale-context"
import { apiPost } from "@/lib/api"
import { toastError, toastSuccess } from "@/components/ui/toast"

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

export default function ReportsPage() {
  const { currentAccount } = useAccount()
  const { t } = useLocale()
  const [reportType, setReportType] = useState("comprehensive")
  const [format, setFormat] = useState("excel")
  const [generating, setGenerating] = useState(false)
  const [recentReports, setRecentReports] = useState<any[]>([])
  
  const reportTypes: ReportType[] = [
    {
      id: "comprehensive",
      name: t.reports.types.comprehensive.name,
      description: t.reports.types.comprehensive.description,
      icon: <FileText className="w-6 h-6" />,
      color: "from-blue-500 to-cyan-500",
    },
    {
      id: "resources",
      name: t.reports.types.resource.name,
      description: t.reports.types.resource.description,
      icon: <FileSpreadsheet className="w-6 h-6" />,
      color: "from-green-500 to-emerald-500",
    },
    {
      id: "cost",
      name: t.reports.types.cost.name,
      description: t.reports.types.cost.description,
      icon: <FileType className="w-6 h-6" />,
      color: "from-yellow-500 to-orange-500",
    },
    {
      id: "security",
      name: t.reports.types.security.name,
      description: t.reports.types.security.description,
      icon: <FileCode className="w-6 h-6" />,
      color: "from-red-500 to-pink-500",
    },
  ]

  const reportFormats: ReportFormat[] = [
    {
      id: "excel",
      name: t.reports.formats.excel.name,
      description: t.reports.formats.excel.description,
      icon: <FileSpreadsheet className="w-5 h-5" />,
    },
    {
      id: "html",
      name: t.reports.formats.html.name,
      description: t.reports.formats.html.description,
      icon: <FileCode className="w-5 h-5" />,
    },
    {
      id: "pdf",
      name: t.reports.formats.pdf.name,
      description: t.reports.formats.pdf.description,
      icon: <FileText className="w-5 h-5" />,
    },
  ]

  useEffect(() => {
    // TODO: fetchRecentReports()
  }, [])

  const handleGenerate = async () => {
    if (!currentAccount) {
      toastError(t.reports.selectAccountFirst)
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
          toastSuccess(t.reports.generateSuccess)
        }, 500)
        return
      }
      throw new Error(t.reports.generateFailed)
    } catch (e) {
      console.error("Failed to generate report:", e)
      toastError(t.reports.generateFailed + ": " + String(e))
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
          <h2 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-primary to-cyan-500 bg-clip-text text-transparent">{t.reports.title}</h2>
          <p className="text-lg text-muted-foreground">{t.reports.description}</p>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-semibold">{t.reports.selectReportType}</h3>
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
            <h3 className="text-xl font-semibold">{t.reports.selectFormat}</h3>
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
                    <CardTitle className="text-2xl mb-2">{t.reports.generateReport}</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {t.reports.selected}: <span className="font-semibold text-foreground">{selectedType.name}</span> · {t.reports.format}:{" "}
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
                      <div className="text-xs text-muted-foreground mb-1">{t.reports.reportType}</div>
                      <div className="font-semibold flex items-center gap-2">
                        {selectedType.icon}
                        {selectedType.name}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">{t.reports.outputFormat}</div>
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
                        <span>{t.reports.generating}</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center gap-3">
                        <Download className="w-5 h-5" />
                        <span>{t.reports.generateAndDownload}</span>
                      </div>
                    )}
                  </button>

                  <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                    <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-muted-foreground">
                      <div className="font-medium text-blue-400 mb-1">💡 {t.reports.tip}</div>
                      <div>
                        {t.reports.tipContent}
                        {format === "excel" && t.reports.excelTip}
                        {format === "html" && t.reports.htmlTip}
                        {format === "pdf" && t.reports.pdfTip}
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
                {t.reports.recentReports}
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
                      <button className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">{t.reports.download}</button>
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









