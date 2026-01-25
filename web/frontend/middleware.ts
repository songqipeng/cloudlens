import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// 不需要认证的路径
const PUBLIC_PATHS = ['/login', '/api']

// 静态资源路径
const STATIC_PATHS = ['/_next', '/favicon.ico', '/images', '/fonts']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // 跳过静态资源
  if (STATIC_PATHS.some(path => pathname.startsWith(path))) {
    return NextResponse.next()
  }

  // 跳过公开路径
  if (PUBLIC_PATHS.some(path => pathname.startsWith(path))) {
    return NextResponse.next()
  }

  // 检查认证token
  const authToken = request.cookies.get('cloudlens_auth_token')?.value

  if (!authToken) {
    // 未登录，重定向到登录页
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // 验证token（简单验证：检查是否过期）
  try {
    const payload = JSON.parse(atob(authToken))
    if (!payload.exp || payload.exp < Date.now()) {
      // token已过期
      const response = NextResponse.redirect(new URL('/login', request.url))
      // 清除过期的cookie
      response.cookies.delete('cloudlens_auth_token')
      return response
    }
  } catch {
    // token无效
    const response = NextResponse.redirect(new URL('/login', request.url))
    response.cookies.delete('cloudlens_auth_token')
    return response
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * 匹配所有路径除了:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
