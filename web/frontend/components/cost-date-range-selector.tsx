"use client"

import { useState, useEffect } from "react"
import { Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useLocale } from "@/contexts/locale-context"

export interface CostDateRange {
  startDate: string | null  // YYYY-MM-DD格式
  endDate: string | null    // YYYY-MM-DD格式
}

interface CostDateRangeSelectorProps {
  onChange: (range: CostDateRange) => void
  className?: string
}

/**
 * 成本趋势日期范围选择器
 * 
 * 提供快捷选项：7天、30天、90天、全部，以及自定义日期范围
 */
export function CostDateRangeSelector({ onChange, className = "" }: CostDateRangeSelectorProps) {
  const [selectedPreset, setSelectedPreset] = useState<string | null>("30")  // 默认30天
  const [customStart, setCustomStart] = useState<string>("")
  const [customEnd, setCustomEnd] = useState<string>("")
  const [showCustom, setShowCustom] = useState(false)

  // 计算预设日期范围
  const getPresetRange = (preset: string): CostDateRange => {
    const now = new Date()
    const today = now.toISOString().split('T')[0]  // YYYY-MM-DD
    
    switch (preset) {
      case "7":
        {
          const date = new Date(now)
          date.setDate(date.getDate() - 7)
          return { startDate: date.toISOString().split('T')[0], endDate: today }
        }
      
      case "30":
        {
          const date = new Date(now)
          date.setDate(date.getDate() - 30)
          return { startDate: date.toISOString().split('T')[0], endDate: today }
        }
      
      case "90":
        {
          const date = new Date(now)
          date.setDate(date.getDate() - 90)
          return { startDate: date.toISOString().split('T')[0], endDate: today }
        }
      
      case "all":
        return { startDate: null, endDate: null }
      
      case "custom":
        return {
          startDate: customStart || null,
          endDate: customEnd || null
        }
      
      default:
        return { startDate: null, endDate: null }
    }
  }

  // 初始化：默认选择30天
  useEffect(() => {
    if (selectedPreset === "30") {
      const range = getPresetRange("30")
      onChange(range)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])  // 只在组件挂载时执行一次

  // 初始化：默认选择30天
  useEffect(() => {
    const range = getPresetRange("30")
    onChange(range)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])  // 只在组件挂载时执行一次

  // 处理预设按钮点击
  const handlePresetClick = (preset: string) => {
    setSelectedPreset(preset)
    setShowCustom(preset === "custom")
    
    if (preset !== "custom") {
      const range = getPresetRange(preset)
      onChange(range)
      // 清除自定义日期输入
      setCustomStart("")
      setCustomEnd("")
    }
  }

  // 处理自定义日期变化
  const handleCustomChange = () => {
    if (customStart && customEnd) {
      if (customStart > customEnd) {
        alert(t.locale === 'zh' ? "开始日期不能晚于结束日期" : "Start date cannot be later than end date")
        return
      }
      onChange({
        startDate: customStart,
        endDate: customEnd
      })
      setSelectedPreset("custom")
    }
  }

  const { t } = useLocale()
  
  // 预设选项
  const presets = [
    { id: "7", label: t.dateRange.last7Days },
    { id: "30", label: t.dateRange.last30Days },
    { id: "90", label: t.dateRange.last90Days },
    { id: "all", label: t.dateRange.all },
    { id: "custom", label: t.dateRange.custom }
  ]

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {/* 快捷按钮 */}
      <div className="flex items-center gap-2 flex-wrap">
        {presets.map((preset) => (
          <button
            key={preset.id}
            onClick={() => handlePresetClick(preset.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              selectedPreset === preset.id
                ? 'bg-primary text-primary-foreground shadow-[0_2px_8px_rgba(59,130,246,0.2)]' 
                : 'bg-[rgba(255,255,255,0.05)] text-muted-foreground hover:bg-[rgba(255,255,255,0.08)] hover:text-foreground'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* 自定义日期输入 */}
      {showCustom && (
        <div className="flex items-center gap-3 pt-2 border-t border-[rgba(255,255,255,0.08)]">
          <Calendar className="w-4 h-4 text-muted-foreground" />
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground whitespace-nowrap">{t.dateRange.startDate}:</label>
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              max={customEnd || new Date().toISOString().split('T')[0]}  // 不能晚于结束日期或今天
              className="px-3 py-1.5 text-sm rounded-lg border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.05)] text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
            />
          </div>
          <span className="text-muted-foreground">{t.common.to || 'to'}</span>
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground whitespace-nowrap">{t.dateRange.endDate}:</label>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              min={customStart}  // 不能早于开始日期
              max={new Date().toISOString().split('T')[0]}  // 不能选择未来日期
              className="px-3 py-1.5 text-sm rounded-lg border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.05)] text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
            />
          </div>
          <Button
            size="sm"
            onClick={handleCustomChange}
            disabled={!customStart || !customEnd || customStart > customEnd}
            className="h-8"
          >
            {t.dateRange.apply}
          </Button>
        </div>
      )}
    </div>
  )
}
