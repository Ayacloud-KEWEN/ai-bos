"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, Loader2, TrendingUp, Rocket, ShieldAlert, Layers } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Segment { name: string; description: string; }
interface MarketResp {
  has_data: boolean; executive_summary: string | null;
  tam: string | null; sam: string | null; som: string | null; market_growth: string | null;
  trends: string[]; drivers: string[]; barriers: string[]; segments: Segment[];
}

function List({ title, items, icon: Icon, tone }: { title: string; items: string[]; icon: React.ElementType; tone: string }) {
  if (!items?.length) return null;
  return (
    <Card><CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><Icon className={`h-5 w-5 ${tone}`} /> {title}</CardTitle></CardHeader>
      <CardContent><ul className="space-y-2">{items.map((it, i) => (
        <li key={i} className="flex gap-2 text-sm text-foreground/80"><span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${tone.replace("text-", "bg-")}`} />{it}</li>
      ))}</ul></CardContent></Card>
  );
}

function TamCard({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-xl border bg-card p-4 text-center">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium leading-snug">{value || "—"}</p>
    </div>
  );
}

export function MarketDashboard({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<MarketResp>({
    queryKey: ["market", companyId],
    queryFn: () => apiClient.get(`/companies/${companyId}/market`) as unknown as Promise<MarketResp>,
    refetchInterval: (q) => (q.state.data && !q.state.data.has_data ? 5000 : false),
  });
  const gen = useMutation({
    mutationFn: () => apiClient.post(`/companies/${companyId}/market/generate`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["market", companyId] }),
  });

  if (isLoading) return <div className="p-12 text-center text-muted-foreground animate-pulse">Loading market research…</div>;
  if (!data?.has_data) {
    return (
      <Card><CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <Globe className="h-10 w-10 text-muted-foreground/50" />
        <p className="font-medium">No market research yet</p>
        <p className="max-w-md text-sm text-muted-foreground">A market research consultant estimates TAM/SAM/SOM, growth, drivers, barriers and trends. Estimates are labeled — verify before decisions.</p>
        <Button onClick={() => gen.mutate()} disabled={gen.isPending} className="gap-2">
          {gen.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</> : <><Globe className="h-4 w-4" /> Generate</>}
        </Button>
      </CardContent></Card>
    );
  }

  return (
    <div className="space-y-6">
      {data.executive_summary && <Card><CardContent className="py-5"><p className="text-base leading-relaxed text-foreground/85">{data.executive_summary}</p></CardContent></Card>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <TamCard label="TAM" value={data.tam} />
        <TamCard label="SAM" value={data.sam} />
        <TamCard label="SOM" value={data.som} />
        <TamCard label="Growth" value={data.market_growth} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <List title="Trends" items={data.trends} icon={TrendingUp} tone="text-indigo-500" />
        <List title="Growth Drivers" items={data.drivers} icon={Rocket} tone="text-emerald-500" />
        <List title="Barriers to Entry" items={data.barriers} icon={ShieldAlert} tone="text-rose-500" />
        {data.segments?.length > 0 && (
          <Card><CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><Layers className="h-5 w-5 text-violet-500" /> Market Segments</CardTitle></CardHeader>
            <CardContent><ul className="space-y-2">{data.segments.map((s, i) => (
              <li key={i} className="text-sm"><span className="font-medium">{s.name}</span>{s.description && <span className="text-muted-foreground"> — {s.description}</span>}</li>
            ))}</ul></CardContent></Card>
        )}
      </div>
    </div>
  );
}
