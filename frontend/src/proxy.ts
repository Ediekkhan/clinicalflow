import { NextRequest, NextResponse } from 'next/server';

const ownerRoles = new Set(['owner', 'admin', 'system_admin']);

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (!pathname.startsWith('/dashboard/admin')) {
    return NextResponse.next();
  }

  const role = request.cookies.get('synaptiverse_role')?.value;
  const ownerToken = request.cookies.get('synaptiverse_owner')?.value;
  const expectedOwnerToken = process.env.SYNAPTIVERSE_OWNER_TOKEN;
  const hasOwnerToken = Boolean(expectedOwnerToken && ownerToken === expectedOwnerToken);

  if (role && ownerRoles.has(role)) {
    return NextResponse.next();
  }

  if (hasOwnerToken) {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = '/login';
  loginUrl.searchParams.set('next', `${pathname}${search}`);
  loginUrl.searchParams.set('reason', 'owner-only');

  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ['/dashboard/admin/:path*'],
};
