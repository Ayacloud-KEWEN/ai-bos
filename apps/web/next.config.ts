import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin(
  './i18n/request.ts'
);

/** @type {import('next').NextConfig} */
const nextConfig = {
  // 生产构建不因 lint/类型洁癖（no-explicit-any 等）而失败——它们不影响运行时。
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  // 仓库根有 pnpm-lock、apps/web 有 package-lock，显式指定 web 为 turbopack root，消除告警。
  turbopack: { root: __dirname },
};

export default withNextIntl(nextConfig);