"use client"

import { useEffect } from "react"
import { useAccount } from "@/contexts/account-context"

export function AccountSync({ account }: { account: string }) {
  const { setCurrentAccount } = useAccount()

  useEffect(() => {
    setCurrentAccount(decodeURIComponent(account))
  }, [account, setCurrentAccount])

  return null
}










