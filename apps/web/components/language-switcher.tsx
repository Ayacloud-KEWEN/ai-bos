"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/routing";
import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function LanguageSwitcher() {
  // 获取当前语言环境
  const locale = useLocale();
  // 注意：这里必须使用我们在 routing.ts 中包装过的 useRouter 和 usePathname
  const router = useRouter();
  const pathname = usePathname();

  const switchLanguage = (newLocale: "en" | "zh" | "fr") => {
    // 替换当前路由，只改变语言前缀，保持路径不变
    router.replace(pathname, { locale: newLocale });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Languages className="h-[1.2rem] w-[1.2rem]" />
          <span className="sr-only">Toggle language</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem 
          onClick={() => switchLanguage("en")} 
          className={locale === "en" ? "bg-muted font-bold" : ""}
        >
          English
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => switchLanguage("zh")} 
          className={locale === "zh" ? "bg-muted font-bold" : ""}
        >
          中文
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => switchLanguage("fr")} 
          className={locale === "fr" ? "bg-muted font-bold" : ""}
        >
          Français
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}