"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { login as authLogin, logout as authLogout, fetchCurrentUser, getCurrentUser } from '@/lib/auth'

interface User {
  username: string
  role?: string
  email?: string | null
}

interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [authenticated, setAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  // 初始化时检查登录状态
  useEffect(() => {
    const checkAuth = async () => {
      const currentUser = await fetchCurrentUser()
      setAuthenticated(Boolean(currentUser))
      setUser(currentUser)
      setLoading(false)
    }

    void checkAuth()
  }, [])

  const login = async (username: string, password: string): Promise<boolean> => {
    const currentUser = await authLogin(username, password)

    if (currentUser) {
      setAuthenticated(true)
      setUser(currentUser)
      return true
    }

    setAuthenticated(false)
    setUser(null)
    return false
  }

  const logout = async (): Promise<void> => {
    await authLogout()
    setAuthenticated(false)
    setUser(null)
    
    // 重定向到登录页
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: authenticated,
        user,
        loading,
        login,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
