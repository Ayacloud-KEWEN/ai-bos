"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Loader2, Target, ArrowRight, AlertTriangle, Lightbulb, RefreshCw } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Briefing {
  has_data: boolean;
  summary: string | null;
  what_happened: string | null;
  why_it_matters: string | null;
  recommended_actions: string[];
  key_risks: string[];
  opportunities: string[];
  next_actions: string[];
}

function List({ title, items, icon: Icon, tone }: { title: string; items: string[]; icon: React.ElementType; tone: string }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className={`mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide ${tone}`}>
        <Icon className="h-3.5 w-3.5" /> {title}
      </div>
      <ul className="space-y-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex gap-2 text-sm text-foreground/80">
            <span className={`mt-1.5 h-1 w-1 shrink-0 rounded-full ${tone.replace("text-", "bg-")}`} />{it}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CompanyBriefing({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<Briefing>({
    queryKey: ["briefing", companyId],
    queryFn: () => apiClient.get(`/companies/${companyId}/briefing`) as unknown as Promise<Briefing>,
  });

  const gen = useMutation({
    mutationFn: () => apiClient.post(`/companies/${companyId}/briefing/generate`, {}),
    onSuccess: () => {
      // 轮询直到生成
      const t = setInterval(async () => {
        const r = (await apiClient.get(`/companies/${companyId}/briefing`)) as unknown as Briefing;
        if (r.has_data) { clearInterval(t); queryClient.invalidateQueries({ queryKey: ["briefing", companyId] }); }
      }, 4000);
      setTimeout(() => clearInterval(t), 120000);
    },
  });

  if (isLoading) return null;

  if (!data?.has_data) {
    return (
      <Card>
        <CardContent className="flex items-center justify-between gap-4 py-5">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-indigo-500" />
            <div>
              <p className="font-medium">Executive Briefing</p>
              <p className="text-sm text-muted-foreground">Synthesize financials, competition & due diligence into a CEO-level briefing.</p>
            </div>
          </div>
          <Button onClick={() => gen.mutate()} disabled={gen.isPending} className="gap-2">
            {gen.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</> : <><Sparkles className="h-4 w-4" /> Generate</>}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-5 w-5 text-indigo-500" /> Executive Briefing</CardTitle>
          <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground" onClick={() => gen.mutate()} disabled={gen.isPending}>
            {gen.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} Regenerate
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {data.summary && <p className="rounded-lg border bg-primary/5 p-4 text-base font-medium leading-relaxed">{data.summary}</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          {data.what_happened && <div><div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">What happened</div><p className="text-sm text-foreground/80">{data.what_happened}</p></div>}
          {data.why_it_matters && <div><div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Why it matters</div><p className="text-sm text-foreground/80">{data.why_it_matters}</p></div>}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <List title="Recommended actions" items={data.recommended_actions} icon={Target} tone="text-indigo-600" />
          <List title="Next actions" items={data.next_actions} icon={ArrowRight} tone="text-emerald-600" />
          <List title="Key risks" items={data.key_risks} icon={AlertTriangle} tone="text-rose-600" />
          <List title="Opportunities" items={data.opportunities} icon={Lightbulb} tone="text-amber-600" />
        </div>
      </CardContent>
    </Card>
  );
}
