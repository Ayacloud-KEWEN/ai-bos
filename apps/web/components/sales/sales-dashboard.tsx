"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, Loader2, Target, Zap, Crosshair, UserCircle } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ICP { segment: string; description: string; why_fit: string; }
interface Persona { role: string; goals: string[]; pain_points: string[]; }
interface SalesResp {
  has_data: boolean; executive_summary: string | null;
  icp: ICP[]; buyer_personas: Persona[]; pain_points: string[];
  buying_triggers: string[]; sales_opportunities: string[];
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

export function SalesDashboard({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<SalesResp>({
    queryKey: ["sales", companyId],
    queryFn: () => apiClient.get(`/companies/${companyId}/sales`) as unknown as Promise<SalesResp>,
    refetchInterval: (q) => (q.state.data && !q.state.data.has_data ? 5000 : false),
  });
  const gen = useMutation({
    mutationFn: () => apiClient.post(`/companies/${companyId}/sales/generate`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sales", companyId] }),
  });

  if (isLoading) return <div className="p-12 text-center text-muted-foreground animate-pulse">Loading sales intelligence…</div>;
  if (!data?.has_data) {
    return (
      <Card><CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <Users className="h-10 w-10 text-muted-foreground/50" />
        <p className="font-medium">No sales intelligence yet</p>
        <p className="max-w-md text-sm text-muted-foreground">An enterprise sales director derives ICP, buyer personas, pain points, buying triggers and sales plays.</p>
        <Button onClick={() => gen.mutate()} disabled={gen.isPending} className="gap-2">
          {gen.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</> : <><Users className="h-4 w-4" /> Generate</>}
        </Button>
      </CardContent></Card>
    );
  }

  return (
    <div className="space-y-6">
      {data.executive_summary && <Card><CardContent className="py-5"><p className="text-base leading-relaxed text-foreground/85">{data.executive_summary}</p></CardContent></Card>}

      {data.icp?.length > 0 && (
        <Card><CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><Crosshair className="h-5 w-5 text-indigo-500" /> Ideal Customer Profiles</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">{data.icp.map((x, i) => (
            <div key={i} className="rounded-lg border p-3"><p className="font-medium">{x.segment}</p><p className="text-sm text-muted-foreground">{x.description}</p>{x.why_fit && <p className="mt-1 text-xs text-emerald-600">✓ {x.why_fit}</p>}</div>
          ))}</CardContent></Card>
      )}

      {data.buyer_personas?.length > 0 && (
        <Card><CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><UserCircle className="h-5 w-5 text-sky-500" /> Buyer Personas</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">{data.buyer_personas.map((p, i) => (
            <div key={i} className="rounded-lg border p-3">
              <p className="font-medium">{p.role}</p>
              {p.goals?.length > 0 && <p className="mt-1 text-xs"><span className="text-muted-foreground">目标：</span>{p.goals.join("; ")}</p>}
              {p.pain_points?.length > 0 && <p className="mt-0.5 text-xs"><span className="text-muted-foreground">痛点：</span>{p.pain_points.join("; ")}</p>}
            </div>
          ))}</CardContent></Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <List title="Pain Points" items={data.pain_points} icon={Zap} tone="text-rose-500" />
        <List title="Buying Triggers" items={data.buying_triggers} icon={Target} tone="text-amber-500" />
      </div>
      <List title="Sales Opportunities" items={data.sales_opportunities} icon={Target} tone="text-emerald-600" />
    </div>
  );
}
