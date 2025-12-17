"use client"

import { useEffect } from "react"
import { useParams, useRouter } from "next/navigation"

export default function ResourceDetailRedirect() {
  const router = useRouter()
  const params = useParams<{ id: string }>()

  useEffect(() => {
    const account = localStorage.getItem("currentAccount")
    if (account && params?.id) {
      router.replace(`/a/${encodeURIComponent(account)}/resources/${encodeURIComponent(params.id)}`)
    } else {
      router.replace("/settings/accounts")
    }
  }, [router, params?.id])

  return null
}





