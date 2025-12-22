"use client"

import { Button } from "@/components/ui/button"
import { FileImage, FileText } from "lucide-react"
import { useState } from "react"

interface ChartExportProps {
  chartId: string
  title?: string
  onExport?: (format: "png" | "pdf") => void
}

export function ChartExport({ chartId, title, onExport }: ChartExportProps) {
  const [exporting, setExporting] = useState(false)

  const handleExport = async (format: "png" | "pdf") => {
    if (onExport) {
      onExport(format)
      return
    }

    const element = document.getElementById(chartId)
    if (!element) {
      console.error("Chart element not found")
      alert("未找到图表元素")
      return
    }

    setExporting(true)

    try {
      if (format === "png") {
        // 动态导入html2canvas
        const html2canvas = (await import("html2canvas")).default
        
        const canvas = await html2canvas(element, {
          backgroundColor: "#ffffff",
          scale: 2,
          logging: false,
          useCORS: true
        })
        
        const url = canvas.toDataURL("image/png")
        const link = document.createElement("a")
        link.download = `${title || "chart"}-${new Date().toISOString().split("T")[0]}.png`
        link.href = url
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } else if (format === "pdf") {
        // 动态导入html2canvas和jsPDF
        const html2canvas = (await import("html2canvas")).default
        const { jsPDF } = await import("jspdf")
        
        const canvas = await html2canvas(element, {
          backgroundColor: "#ffffff",
          scale: 2,
          logging: false,
          useCORS: true
        })
        
        const imgData = canvas.toDataURL("image/png")
        const pdf = new jsPDF({
          orientation: canvas.width > canvas.height ? "landscape" : "portrait",
          unit: "px",
          format: [canvas.width, canvas.height]
        })
        
        pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height)
        pdf.save(`${title || "chart"}-${new Date().toISOString().split("T")[0]}.pdf`)
      }
    } catch (e) {
      console.error(`Failed to export ${format.toUpperCase()}:`, e)
      alert(`导出${format.toUpperCase()}失败: ${e instanceof Error ? e.message : "未知错误"}`)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => handleExport("png")}
        disabled={exporting}
        className="gap-2"
        title="导出为PNG图片"
      >
        <FileImage className="h-4 w-4" />
        {exporting ? "导出中..." : "PNG"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => handleExport("pdf")}
        disabled={exporting}
        className="gap-2"
        title="导出为PDF文档"
      >
        <FileText className="h-4 w-4" />
        {exporting ? "导出中..." : "PDF"}
      </Button>
    </div>
  )
}




