"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  // 在组件内部初始化 QueryClient，确保每个用户请求在 SSR 时有独立实例，避免状态泄漏
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 数据 60 秒内被认为是新鲜的，不重复请求
            refetchOnWindowFocus: false, // 开发阶段关掉窗口聚焦自动刷新，避免请求刷屏
            retry: 1, // 失败后默认重试 1 次
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}