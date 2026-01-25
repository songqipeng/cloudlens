"use client"

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { login } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mounted, setMounted] = useState(false)

  // 粒子动画
  useEffect(() => {
    setMounted(true)
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number
    let particles: { x: number; y: number; speed: number; size: number }[] = []

    const init = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      particles = []
      for (let i = 0; i < 50; i++) {
        particles.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          speed: 0.5 + Math.random() * 2,
          size: 1 + Math.random() * 2
        })
      }
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#0ea5e9'
      particles.forEach(p => {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fill()
        p.y -= p.speed
        if (p.y < 0) p.y = canvas.height
      })
      animationId = requestAnimationFrame(draw)
    }

    init()
    draw()

    const handleResize = () => init()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationId)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    if (!username.trim() || !password.trim()) {
      setError('// ERROR: CREDENTIALS_REQUIRED')
      setLoading(false)
      return
    }

    await new Promise(resolve => setTimeout(resolve, 800))

    const success = login(username, password)
    
    if (success) {
      router.push('/')
      router.refresh()
    } else {
      setError('// ERROR: AUTH_FAILED - INVALID_CREDENTIALS')
      setLoading(false)
    }
  }

  return (
    <div 
      className="min-h-screen bg-black flex items-center justify-center p-4 relative overflow-hidden"
      style={{
        backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(255, 255, 255, 0.05) 1px, transparent 0)',
        backgroundSize: '40px 40px'
      }}
    >
      {/* 粒子背景 */}
      <canvas 
        ref={canvasRef} 
        className="fixed inset-0 pointer-events-none opacity-40"
        style={{ zIndex: 0 }}
      />

      {/* 扫描线效果 */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-30"
        style={{
          background: 'linear-gradient(to bottom, transparent 50%, rgba(14, 165, 233, 0.03) 50%)',
          backgroundSize: '100% 4px',
          zIndex: 1
        }}
      />

      {/* HUD 角标 */}
      <div className="fixed top-6 left-6 font-mono text-xs text-cyan-500/60 tracking-widest z-10">
        // SYS.AUTH_GATEWAY
      </div>
      <div className="fixed top-6 right-6 font-mono text-xs text-cyan-500/60 tracking-widest z-10">
        PROTOCOL: SECURE_v2.1
      </div>
      <div className="fixed bottom-6 left-6 font-mono text-xs text-cyan-500/60 tracking-widest z-10">
        {mounted && new Date().toLocaleTimeString('en-US', { hour12: false })}
      </div>
      <div className="fixed bottom-6 right-6 font-mono text-xs text-cyan-500/60 tracking-widest z-10">
        CLOUDLENS_CORE
      </div>

      {/* 登录卡片 */}
      <div className={`relative w-full max-w-md z-10 transition-all duration-1000 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
        {/* 卡片光晕 */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500/20 via-purple-500/20 to-cyan-500/20 rounded-lg blur-xl opacity-50" />
        
        <div className="relative bg-black/80 backdrop-blur-xl border border-white/10 rounded-lg overflow-hidden">
          {/* 顶部装饰线 */}
          <div className="h-px bg-gradient-to-r from-transparent via-cyan-500 to-transparent" />
          
          <div className="p-8 sm:p-10">
            {/* 标题区域 */}
            <div className="text-center mb-10">
              <div className="font-mono text-xs text-cyan-500 tracking-[0.5em] mb-4 uppercase">
                Intelligence Access Gateway
              </div>
              <h1 
                className="text-4xl sm:text-5xl font-black tracking-tight mb-2"
                style={{ 
                  fontFamily: "'Orbitron', sans-serif",
                  background: 'linear-gradient(to bottom, #fff, rgba(255,255,255,0.4))',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}
              >
                CLOUDLENS
              </h1>
              <div 
                className="text-sm tracking-[0.3em] text-white/30"
                style={{ fontFamily: "'Orbitron', sans-serif" }}
              >
                PRISM PROTOCOL
              </div>
              
              {/* 装饰线 */}
              <div className="w-px h-12 bg-gradient-to-b from-cyan-500 to-transparent mx-auto mt-6" />
            </div>

            {/* 登录表单 */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 用户名 */}
              <div className="space-y-2">
                <label className="font-mono text-xs text-cyan-500 tracking-widest uppercase">
                  // USER_ID
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="ENTER_USERNAME"
                  className="w-full h-12 px-4 bg-white/5 border border-white/10 rounded text-white font-mono placeholder:text-white/20 focus:outline-none focus:border-cyan-500/50 focus:bg-white/10 transition-all"
                  disabled={loading}
                  autoComplete="username"
                />
              </div>

              {/* 密码 */}
              <div className="space-y-2">
                <label className="font-mono text-xs text-cyan-500 tracking-widest uppercase">
                  // ACCESS_KEY
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full h-12 px-4 pr-12 bg-white/5 border border-white/10 rounded text-white font-mono placeholder:text-white/20 focus:outline-none focus:border-cyan-500/50 focus:bg-white/10 transition-all"
                    disabled={loading}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-white/30 hover:text-cyan-500 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {/* 错误提示 */}
              {error && (
                <div className="p-3 border border-red-500/30 rounded bg-red-500/5">
                  <p className="font-mono text-xs text-red-400">{error}</p>
                </div>
              )}

              {/* 登录按钮 */}
              <button
                type="submit"
                disabled={loading}
                className="w-full h-12 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-black font-bold tracking-wider rounded transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40"
                style={{ fontFamily: "'Orbitron', sans-serif" }}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    AUTHENTICATING...
                  </>
                ) : (
                  'INITIALIZE ACCESS'
                )}
              </button>
            </form>

            {/* 底部信息 */}
            <div className="mt-8 pt-6 border-t border-white/5">
              <p className="font-mono text-xs text-center text-white/20 tracking-widest">
                &copy; 2026 CLOUDLENS // MIT LICENSE
              </p>
            </div>
          </div>
          
          {/* 底部装饰线 */}
          <div className="h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
        </div>
      </div>

      {/* 加载Google字体 */}
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=JetBrains+Mono:wght@300;500&display=swap');
      `}</style>
    </div>
  )
}
