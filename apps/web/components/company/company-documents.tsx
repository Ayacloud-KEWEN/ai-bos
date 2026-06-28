"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, ExternalLink, Paperclip } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Doc { id: string; filename: string; size: number; uploaded_at: string | null; }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function fmtSize(b: number): string {
  if (!b) return "";
  if (b >= 1024 * 1024) return (b / 1024 / 1024).toFixed(1) + " MB";
  if (b >= 1024) return (b / 1024).toFixed(0) + " KB";
  return b + " B";
}

export function CompanyDocuments({ companyId }: { companyId: string }) {
  const { data: docs = [] } = useQuery<Doc[]>({
    queryKey: ["documents", companyId],
    queryFn: () => apiClient.get(`/companies/${companyId}/documents`) as unknown as Promise<Doc[]>,
  });

  if (!docs.length) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Paperclip className="h-5 w-5 text-muted-foreground" /> Source Documents ({docs.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {docs.map((d) => (
          <a
            key={d.id}
            href={`${API_BASE}/companies/${companyId}/documents/${d.id}/file`}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 rounded-lg border p-3 transition-colors hover:border-primary/40 hover:bg-muted/30"
          >
            <FileText className="h-5 w-5 shrink-0 text-rose-500" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{d.filename}</p>
              <p className="text-xs text-muted-foreground">
                {fmtSize(d.size)}{d.uploaded_at ? ` · ${new Date(d.uploaded_at).toLocaleDateString()}` : ""}
              </p>
            </div>
            <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </a>
        ))}
      </CardContent>
    </Card>
  );
}
