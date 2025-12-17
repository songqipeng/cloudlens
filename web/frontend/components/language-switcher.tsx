"use client"

import { Globe } from "lucide-react"
import { useLocale } from "@/contexts/locale-context"
import { Locale } from "@/lib/i18n"
import { Button } from "@/components/ui/button"
import { DropdownMenu } from "@/components/ui/dropdown"

export function LanguageSwitcher() {
  const { locale, setLocale } = useLocale()

  const languages: { code: Locale; label: string; native: string }[] = [
    { code: 'en', label: 'English', native: 'English' },
    { code: 'zh', label: 'Chinese', native: '中文' },
  ]

  return (
    <DropdownMenu
      trigger={
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0 hover:bg-primary/10"
          aria-label="Switch language"
          title={locale === 'zh' ? '切换语言' : 'Switch Language'}
        >
          <Globe className="h-4 w-4" />
        </Button>
      }
      items={languages.map((lang) => ({
        label: lang.native,
        onClick: () => setLocale(lang.code),
      }))}
      align="right"
    />
  )
}
