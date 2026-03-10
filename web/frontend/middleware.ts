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

  // 检查认证 cookie（实际有效性由后端 /api/auth/me 和 API 鉴权负责）
  const authToken = request.cookies.get('cloudlens_auth_token')?.value

  if (!authToken) {
    // 未登录，重定向到登录页
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
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
