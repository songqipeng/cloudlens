import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AccountProvider } from "@/contexts/account-context";
import { LocaleProvider } from "@/contexts/locale-context";
import { AuthProvider } from "@/contexts/auth-context";
import { ToastContainer } from "@/components/ui/toast";
import { AIChatbot } from "@/components/ai-chatbot";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CloudLens - 多云资源治理平台",
  description: "企业级多云资源治理与分析工具",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning：避免浏览器扩展（如有道 data-yd-*）改写 <html>/<body> 属性触发误报
    <html lang="zh" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <LocaleProvider>
          <AuthProvider>
            <AccountProvider>
              {children}
              <ToastContainer />
              <AIChatbot />
            </AccountProvider>
          </AuthProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
