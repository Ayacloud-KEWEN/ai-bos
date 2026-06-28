import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  // 匹配所有非静态资源的路径
  matcher: ['/', '/(zh|en|fr)/:path*', '/((?!_next|_vercel|.*\\..*).*)']
};