import type { ReactNode } from "react"
import { AccountSync } from "./account-sync"

export default async function AccountLayout({
  children,
  params,
}: {
  children: ReactNode
  params: Promise<{ account: string }>
}) {
  const { account } = await params

  return (
    <>
      <AccountSync account={account} />
      {children}
    </>
  )
}









