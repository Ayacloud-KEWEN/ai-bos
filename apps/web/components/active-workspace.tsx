"use client";

import { useEffect, useState } from "react";
import { Building2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useGlobalStore } from "@/hooks/use-global-store";

export function ActiveWorkspace() {
  // 解决 Next.js SSR 水合(Hydration) 不匹配的问题
  const [isMounted, setIsMounted] = useState(false);
  const activeCompanyName = useGlobalStore((state) => state.activeCompanyName);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted || !activeCompanyName) return null;

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground animate-in fade-in slide-in-from-left-2 duration-500">
      <Building2 className="h-4 w-4" />
      <span className="hidden sm:inline-block">Workspace:</span>
      <Badge variant="secondary" className="font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border-indigo-200">
        {activeCompanyName}
      </Badge>
    </div>
  );
}