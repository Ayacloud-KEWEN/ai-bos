import { redirect } from "@/i18n/routing";

// 首页直接进 Dashboard；未登录会被 api-client 拦截并转到 /login。
export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  redirect({ href: "/dashboard", locale });
}
