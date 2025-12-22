"use client"

import { useEffect, useMemo } from "react"
import { useRouter } from "next/navigation"
import AccountsPage from "@/app/_pages/accounts"

export default function AccountsEntry() {
  const router = useRouter()

  const account = useMemo(() => {
    if (typeof window === "undefined") return null
    return localStorage.getItem("currentAccount")
  }, [])

  useEffect(() => {
    if (account) {
      router.replace(`/a/${encodeURIComponent(account)}/settings/accounts`)
    }
  }, [router, account])

  if (account) return null
  return <AccountsPage />
}








