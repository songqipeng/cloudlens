/**
 * 全局状态管理（使用Zustand）
 * 统一管理应用状态，避免状态分散和重复
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface PageState {
    loading: boolean
    error: string | null
    data: any
    lastUpdated?: number
}

interface AppState {
    // 全局状态
    currentAccount: string | null
    setCurrentAccount: (account: string | null) => void
    
    // 页面状态管理
    pageStates: Record<string, PageState>
    setPageState: (page: string, state: Partial<PageState>) => void
    clearPageState: (page: string) => void
    
    // UI状态
    sidebarOpen: boolean
    setSidebarOpen: (open: boolean) => void
    
    // 主题（未来扩展）
    theme: 'light' | 'dark' | 'auto'
    setTheme: (theme: 'light' | 'dark' | 'auto') => void
}

export const useAppStore = create<AppState>()(
    persist(
        (set) => ({
            // 全局状态
            currentAccount: null,
            setCurrentAccount: (account) => set({ currentAccount: account }),
            
            // 页面状态管理
            pageStates: {},
            setPageState: (page, state) => set((prev) => ({
                pageStates: {
                    ...prev.pageStates,
                    [page]: { 
                        ...prev.pageStates[page],
                        ...state,
                        lastUpdated: Date.now()
                    }
                }
            })),
            clearPageState: (page) => set((prev) => {
                const newStates = { ...prev.pageStates }
                delete newStates[page]
                return { pageStates: newStates }
            }),
            
            // UI状态
            sidebarOpen: true,
            setSidebarOpen: (open) => set({ sidebarOpen: open }),
            
            // 主题
            theme: 'auto',
            setTheme: (theme) => set({ theme }),
        }),
        {
            name: 'cloudlens-store',
            partialize: (state) => ({
                currentAccount: state.currentAccount,
                sidebarOpen: state.sidebarOpen,
                theme: state.theme,
                // 不持久化页面状态（每次刷新重新加载）
            }),
        }
    )
)

// 便捷hooks
export const usePageState = (page: string) => {
    const pageState = useAppStore((state) => state.pageStates[page] || {
        loading: false,
        error: null,
        data: null
    })
    const setPageState = useAppStore((state) => state.setPageState)
    
    return {
        ...pageState,
        setLoading: (loading: boolean) => setPageState(page, { loading }),
        setError: (error: string | null) => setPageState(page, { error }),
        setData: (data: any) => setPageState(page, { data }),
        clear: () => setPageState(page, { loading: false, error: null, data: null })
    }
}


