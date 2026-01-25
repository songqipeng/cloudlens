"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { BarChart3, Eye, EyeOff, Loader2, Lock, User } from 'lucide-react'
import { login } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    // 简单验证
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码')
      setLoading(false)
      return
    }

    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 500))

    const success = login(username, password)
    
    if (success) {
      // 登录成功，跳转到首页
      router.push('/')
      router.refresh()
    } else {
      setError('用户名或密码错误')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[128px]" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[128px]" />
      </div>

      {/* 登录卡片 */}
      <div className="relative w-full max-w-md">
        {/* 卡片光晕 */}
        <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 via-blue-500/20 to-primary/20 rounded-2xl blur-xl opacity-50" />
        
        <div className="relative bg-[rgba(15,15,20,0.95)] backdrop-blur-[20px] border border-[rgba(255,255,255,0.08)] rounded-2xl p-8 shadow-2xl">
          {/* Logo和标题 */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-blue-600 mb-4 shadow-lg shadow-primary/30">
              <BarChart3 className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">CloudLens</h1>
            <p className="text-sm text-muted-foreground">多云资源治理平台</p>
          </div>

          {/* 登录表单 */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* 用户名 */}
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-muted-foreground">
                用户名
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="请输入用户名"
                  className="w-full h-12 pl-11 pr-4 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] rounded-xl text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all"
                  disabled={loading}
                  autoComplete="username"
                />
              </div>
            </div>

            {/* 密码 */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-muted-foreground">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="请输入密码"
                  className="w-full h-12 pl-11 pr-12 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] rounded-xl text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all"
                  disabled={loading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-white transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {/* 登录按钮 */}
            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-gradient-to-r from-primary to-blue-600 hover:from-primary/90 hover:to-blue-600/90 text-white font-medium rounded-xl transition-all duration-200 shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  登录中...
                </>
              ) : (
                '登录'
              )}
            </button>
          </form>

          {/* 底部信息 */}
          <div className="mt-8 pt-6 border-t border-[rgba(255,255,255,0.08)]">
            <p className="text-xs text-center text-muted-foreground">
              CloudLens - 企业级多云资源治理与分析工具
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
