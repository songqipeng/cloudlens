"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { Locale, defaultLocale, getTranslations, Translations } from "@/lib/i18n"

interface LocaleContextType {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: Translations
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined)

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(defaultLocale)

  // 从localStorage读取保存的语言设置
  useEffect(() => {
    const savedLocale = localStorage.getItem('cloudlens_locale') as Locale
    if (savedLocale && (savedLocale === 'en' || savedLocale === 'zh')) {
      setLocaleState(savedLocale)
    }
  }, [])

  // 保存语言设置到localStorage
  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale)
    localStorage.setItem('cloudlens_locale', newLocale)
  }

  const t = getTranslations(locale)

  return (
    <LocaleContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LocaleContext.Provider>
  )
}

export function useLocale() {
  const context = useContext(LocaleContext)
  if (context === undefined) {
    throw new Error('useLocale must be used within a LocaleProvider')
  }
  return context
}




