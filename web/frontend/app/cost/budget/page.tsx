"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export default function BudgetRedirect() {
  const router = useRouter()

  useEffect(() => {
    const account = localStorage.getItem("currentAccount")
    if (account) {
      router.replace(`/a/${encodeURIComponent(account)}/cost/budget`)
    } else {
      router.replace("/settings/accounts")
    }
  }, [router])

  return null
}




