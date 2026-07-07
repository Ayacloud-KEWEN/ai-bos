"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from 'next-intl';
import { Link } from "@/i18n/routing"; // 使用 next-intl 包装的 Link
import { apiClient } from "@/lib/api-client";
import {
  LayoutDashboard,
  Building2,
  FolderKanban,
  BookOpenText,
  GitMerge,
  Bot,
  Database,
  GraduationCap,
  Store,
  LineChart,
  Settings,
  LogOut,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
} from "@/components/ui/sidebar";

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const t = useTranslations('Sidebar');
  const [me, setMe] = useState<{ username: string | null; auth_required: boolean } | null>(null);

  useEffect(() => {
    apiClient.get("/auth/me").then((r) => setMe(r as any)).catch(() => {});
  }, []);

  const logout = () => {
    localStorage.removeItem("ai_bos_access_token");
    router.push("/login");
  };

  // 我们将 title 替换为词典文件里的对应键名
  const navigationItems = [
    { translationKey: "dashboard", url: "/dashboard", icon: LayoutDashboard },
    { translationKey: "companyIntelligence", url: "/company-intelligence/companies", icon: Building2 },
    { translationKey: "projects", url: "/projects", icon: FolderKanban },
    { translationKey: "playbooks", url: "/playbooks/library", icon: BookOpenText },
    { translationKey: "workflows", url: "/workflows", icon: GitMerge },
    { translationKey: "agents", url: "/agents/library", icon: Bot },
    { translationKey: "knowledgeBase", url: "/knowledge/documents", icon: Database },
    { translationKey: "businessAcademy", url: "/academy/courses", icon: GraduationCap },
    { translationKey: "marketplace", url: "/marketplace/playbooks", icon: Store },
    { translationKey: "analytics", url: "/analytics", icon: LineChart },
  ];

  return (
    <Sidebar variant="sidebar" collapsible="icon">
      <SidebarHeader className="pt-4 pb-2 px-4">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
            AI
          </div>
          <span className="truncate font-semibold text-lg tracking-tight">AI-BOS</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Main Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navigationItems.map((item) => {
                // 确保路径匹配逻辑能兼容前面的语言前缀
                const isActive = pathname.includes(item.url);
                return (
                  <SidebarMenuItem key={item.translationKey}>
                    <SidebarMenuButton asChild isActive={isActive} tooltip={t(item.translationKey)}>
                      <Link href={item.url}>
                        <item.icon />
                        <span>{t(item.translationKey)}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={pathname.includes("/settings")} tooltip={t("settings")}>
              <Link href="/settings">
                <Settings />
                <span>{t("settings")}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          {me?.auth_required && (
            <SidebarMenuItem>
              <SidebarMenuButton onClick={logout} tooltip="Log out">
                <LogOut />
                <span>{me.username ? `Log out (${me.username})` : "Log out"}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}