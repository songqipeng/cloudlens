/**
 * CloudLens 设计系统
 * 基于Finout风格，打造现代化、专业的UI设计
 */

// 色彩系统
export const colors = {
  // 主色调（专业蓝色系）
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',  // 主色
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },
  
  // 语义化颜色
  semantic: {
    success: '#10b981',  // 节省、正常
    warning: '#f59e0b',  // 警告、闲置
    error: '#ef4444',    // 超支、异常
    info: '#6366f1',     // 信息
  },
  
  // 数据可视化配色
  chart: {
    series1: '#3b82f6',  // 主系列（蓝色）
    series2: '#10b981',  // 对比系列（绿色）
    series3: '#f59e0b',  // 第三系列（橙色）
    series4: '#ef4444',  // 第四系列（红色）
    series5: '#8b5cf6',  // 第五系列（紫色）
    series6: '#ec4899',  // 第六系列（粉色）
    series7: '#06b6d4',  // 第七系列（青色）
    series8: '#84cc16',  // 第八系列（黄绿色）
  },
  
  // 灰度系统
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
}

// 排版系统
export const typography = {
  fontSize: {
    xs: '12px',      // 辅助信息
    sm: '14px',      // 次要信息
    base: '16px',    // 正文
    lg: '18px',      // 小标题
    xl: '20px',      // 标题
    '2xl': '24px',   // 大标题
    '3xl': '30px',   // 超大标题
    '4xl': '36px',   // 数字显示
    '5xl': '48px',   // 超大数字
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.6,
  },
}

// 间距系统（4px基础单位）
export const spacing = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
}

// 圆角系统
export const borderRadius = {
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '20px',
  full: '9999px',
}

// 阴影系统
export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px rgba(0, 0, 0, 0.15)',
  '2xl': '0 25px 50px rgba(0, 0, 0, 0.25)',
  // 彩色阴影（用于强调）
  primary: '0 4px 12px rgba(59, 130, 246, 0.2)',
  success: '0 4px 12px rgba(16, 185, 129, 0.2)',
  warning: '0 4px 12px rgba(245, 158, 11, 0.2)',
  error: '0 4px 12px rgba(239, 68, 68, 0.2)',
}

// 动画系统
export const animations = {
  duration: {
    fast: '150ms',
    normal: '200ms',
    slow: '300ms',
  },
  easing: {
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
}

// 组件设计规范
export const componentStyles = {
  card: {
    borderRadius: borderRadius.lg,
    padding: spacing[6],
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(9, 9, 11, 0.75)',
    backdropFilter: 'blur(20px)',
    boxShadow: shadows.md,
    hover: {
      boxShadow: shadows.lg,
      transform: 'translateY(-2px)',
    },
  },
  button: {
    borderRadius: borderRadius.md,
    height: '40px',
    padding: `${spacing[3]} ${spacing[6]}`,
    fontWeight: typography.fontWeight.medium,
  },
}

