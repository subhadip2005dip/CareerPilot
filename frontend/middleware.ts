import NextAuth from "next-auth";
import authConfig from "./auth.config";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const { auth } = NextAuth(authConfig);

export default auth((req) => {
  const { nextUrl, auth: session } = req as NextRequest & { auth: unknown };
  const isLoggedIn = !!session;
  const path = nextUrl.pathname;

  if (path.startsWith("/profile") && !isLoggedIn) {
    return NextResponse.redirect(new URL("/", nextUrl));
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/profile/:path*",
  ],
};