"use client"

import { useEffect } from "react"
import { useParams, useRouter } from "next/navigation"

export default function CustomDashboardDetailRedirect() {
  const router = useRouter()
  const params = useParams<{ id: string }>()

  useEffect(() => {
    const account = localStorage.getItem("currentAccount")
    if (account && params?.id) {
      router.replace(`/a/${encodeURIComponent(account)}/custom-dashboards/${encodeURIComponent(params.id)}`)
    } else if (account) {
      router.replace(`/a/${encodeURIComponent(account)}/custom-dashboards`)
    } else {
      router.replace("/settings/accounts")
    }
  }, [router, params?.id])

  return null
}






