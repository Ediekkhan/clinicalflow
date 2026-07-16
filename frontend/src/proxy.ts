import { NextRequest, NextResponse } from 'next/server';

const protectedPortals = [
  { prefix: '/dashboard/admin', roles: new Set(['admin']), login: '/auth/login' },
  { prefix: '/nurse', roles: new Set(['nurse', 'admin']), login: '/auth/login' },
  { prefix: '/hospital', roles: new Set(['doctor', 'nurse', 'hospital_admin', 'admin']), login: '/hospital/login' },
  { prefix: '/specialist', roles: new Set(['specialist']), login: '/specialist/login' },
  { prefix: '/clinic', roles: new Set(['nurse', 'admin']), login: '/auth/login' },
  { prefix: '/pharmacy', roles: new Set(['admin']), login: '/auth/login' },
  { prefix: '/lab', roles: new Set(['admin']), login: '/auth/login' },
  { prefix: '/hmo', roles: new Set(['admin']), login: '/auth/login' },
  { prefix: '/moh', roles: new Set(['admin']), login: '/auth/login' },
  { prefix: '/dashboard', roles: new Set(['patient']), login: '/login' },
  { prefix: '/my-visit', roles: new Set(['patient']), login: '/login' },
] as const;

const publicPortalPaths = new Set(['/hospital/login', '/specialist/login']);

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (publicPortalPaths.has(pathname)) {
    return NextResponse.next();
  }

  const portal = protectedPortals.find(({ prefix }) => pathname === prefix || pathname.startsWith(`${prefix}/`));
  if (!portal) return NextResponse.next();

  const role = request.cookies.get('synaptiverse_role')?.value;
  if (role && portal.roles.has(role as never)) return NextResponse.next();

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = portal.login;
  loginUrl.searchParams.set('next', `${pathname}${search}`);
  loginUrl.searchParams.set('reason', role ? 'role-required' : 'authentication-required');

  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ['/dashboard/:path*', '/my-visit', '/nurse/:path*', '/hospital/:path*', '/specialist/:path*', '/clinic/:path*'],
};
