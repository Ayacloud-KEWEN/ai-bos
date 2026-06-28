"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, Search, Loader2, Download, Building } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";

interface Source { key: string; label: string; regions: string[]; needs_key: boolean; available: boolean; }
interface Candidate { source: string; name: string; external_id: string; extra: Record<string, any>; }

export function OnlineScanDialog() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [source, setSource] = useState("sec_edgar");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [importingId, setImportingId] = useState<number | null>(null);

  const { data: sourcesData } = useQuery<{ sources: Source[] }>({
    queryKey: ["scan-sources"],
    queryFn: () => apiClient.get("/scan/sources") as unknown as Promise<{ sources: Source[] }>,
    enabled: open,
  });

  const search = useMutation({
    mutationFn: () => apiClient.post("/scan/search", { name, source }) as unknown as Promise<{ candidates: Candidate[] }>,
    onSuccess: (d) => setCandidates(d.candidates),
  });

  const doImport = useMutation({
    mutationFn: (c: Candidate) =>
      apiClient.post("/scan/import", { source: c.source, external_id: c.external_id, name: c.name, extra: c.extra }) as unknown as Promise<{ company_id: string }>,
    onSuccess: (d) => {
      queryClient.invalidateQueries({ queryKey: ["companies"] });
      setOpen(false);
      setCandidates([]); setName("");
      router.push(`/company-intelligence/companies/${d.company_id}`);
    },
    onSettled: () => setImportingId(null),
  });

  const sources = sourcesData?.sources || [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2"><Globe className="h-4 w-4" /> Search Online</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>Search company online</DialogTitle>
          <DialogDescription>
            Pull intelligence directly from authoritative sources (SEC EDGAR, 巨潮资讯…). No document upload needed.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-2 space-y-3">
          <div className="flex gap-2">
            <select
              value={source}
              onChange={(e) => { setSource(e.target.value); setCandidates([]); }}
              className="h-9 rounded-md border border-input bg-transparent px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {sources.map((s) => (
                <option key={s.key} value={s.key} disabled={!s.available}>
                  {s.label}{s.available ? "" : " (即将支持)"}
                </option>
              ))}
            </select>
            <Input
              placeholder="公司名 / 代码（如 Apple、宁德时代）"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && name.trim() && search.mutate()}
            />
            <Button onClick={() => search.mutate()} disabled={!name.trim() || search.isPending} className="gap-1.5">
              {search.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Search
            </Button>
          </div>

          {search.isError && <p className="text-sm text-rose-600">搜索失败，请换个关键词或数据源。</p>}

          <div className="max-h-[340px] space-y-2 overflow-y-auto">
            {candidates.map((c, i) => (
              <div key={`${c.source}-${c.external_id}-${i}`} className="flex items-center justify-between gap-3 rounded-lg border p-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Building className="h-4 w-4 shrink-0 text-primary" />
                    <span className="truncate font-medium">{c.name}</span>
                  </div>
                  <div className="mt-0.5 flex flex-wrap gap-1.5 text-xs text-muted-foreground">
                    {c.extra?.ticker && <Badge variant="secondary" className="text-[10px]">{c.extra.ticker}</Badge>}
                    {c.extra?.code && <Badge variant="secondary" className="text-[10px]">{c.extra.code}</Badge>}
                    {c.extra?.region && <span>{c.extra.region}</span>}
                  </div>
                </div>
                <Button size="sm" className="gap-1.5"
                  disabled={doImport.isPending}
                  onClick={() => { setImportingId(i); doImport.mutate(c); }}>
                  {importingId === i ? <><Loader2 className="h-4 w-4 animate-spin" /> Importing</> : <><Download className="h-4 w-4" /> Import</>}
                </Button>
              </div>
            ))}
            {search.isSuccess && candidates.length === 0 && (
              <p className="py-6 text-center text-sm text-muted-foreground">未找到匹配公司。</p>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
