"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Calendar } from "lucide-react"

export interface DateRange {
  startDate: string | null  // YYYY-MM格式
  endDate: string | null    // YYYY-MM格式
}

interface DateRangeSelectorProps {
  onChange: (range: DateRange) => void
  className?: string
}

/**
 * 时间范围选择器
 * 
 * 提供快捷选项：全部、最近3个月、最近6个月、最近12个月、自定义
 */
export function DateRangeSelector({ onChange, className = "" }: DateRangeSelectorProps) {
  const [selectedPreset, setSelectedPreset] = useState<string>("all")
  const [customStart, setCustomStart] = useState<string>("")
  const [customEnd, setCustomEnd] = useState<string>("")
  const [showCustom, setShowCustom] = useState(false)

  // 计算预设日期范围
  const getPresetRange = (preset: string): DateRange => {
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1 // 0-based
    
    const formatMonth = (year: number, month: number) => {
      return `${year}-${month.toString().padStart(2, '0')}`
    }
    
    const currentMonthStr = formatMonth(currentYear, currentMonth)
    
    switch (preset) {
      case "all":
        return { startDate: null, endDate: null }
      
      case "3m":
        {
          const date = new Date(now)
          date.setMonth(date.getMonth() - 3)
          const startMonth = formatMonth(date.getFullYear(), date.getMonth() + 1)
          return { startDate: startMonth, endDate: currentMonthStr }
        }
      
      case "6m":
        {
          const date = new Date(now)
          date.setMonth(date.getMonth() - 6)
          const startMonth = formatMonth(date.getFullYear(), date.getMonth() + 1)
          return { startDate: startMonth, endDate: currentMonthStr }
        }
      
      case "12m":
        {
          const date = new Date(now)
          date.setMonth(date.getMonth() - 12)
          const startMonth = formatMonth(date.getFullYear(), date.getMonth() + 1)
          return { startDate: startMonth, endDate: currentMonthStr }
        }
      
      case "custom":
        return {
          startDate: customStart || null,
          endDate: customEnd || null
        }
      
      default:
        return { startDate: null, endDate: null }
    }
  }

  // 处理预设按钮点击
  const handlePresetClick = (preset: string) => {
    setSelectedPreset(preset)
    setShowCustom(preset === "custom")
    
    if (preset !== "custom") {
      const range = getPresetRange(preset)
      onChange(range)
    }
  }

  // 处理自定义日期变化
  const handleCustomChange = () => {
    if (customStart && customEnd) {
      onChange({
        startDate: customStart,
        endDate: customEnd
      })
    }
  }

  // 预设选项
  const presets = [
    { id: "all", label: "全部时间" },
    { id: "3m", label: "最近3个月" },
    { id: "6m", label: "最近6个月" },
    { id: "12m", label: "最近12个月" },
    { id: "custom", label: "自定义" }
  ]

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {/* 快捷按钮 */}
      <div className="flex items-center gap-2 flex-wrap">
        <Calendar className="w-4 h-4 text-gray-500" />
        <span className="text-sm text-gray-600 mr-2">时间范围：</span>
        {presets.map((preset) => (
          <Button
            key={preset.id}
            variant={selectedPreset === preset.id ? "default" : "outline"}
            size="sm"
            onClick={() => handlePresetClick(preset.id)}
            className="h-8"
          >
            {preset.label}
          </Button>
        ))}
      </div>

      {/* 自定义日期输入 */}
      {showCustom && (
        <div className="flex items-center gap-3 pl-6 pb-2">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">开始月份：</label>
            <input
              type="month"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">结束月份：</label>
            <input
              type="month"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <Button
            size="sm"
            onClick={handleCustomChange}
            disabled={!customStart || !customEnd}
            className="h-8"
          >
            应用
          </Button>
        </div>
      )}
    </div>
  )
}

