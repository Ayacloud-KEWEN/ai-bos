"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Compass, Loader2, Target, TrendingUp, Layers, Shield } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Option { title: string; description: string; impact: number; feasibility: number; risk: number; investment: string; rationale?: string; }
interface Rec { title: string; rationale?: string; expected_outcome?: string; }
interface Force { force: string; level: number; summary: string; }
interface StrategyResp {
  has_data: boolean;
  executive_summary: string | null;
  strategic_options: Option[];
  recommendations: Rec[];
  porters_five_forces: Force[];
  growth_opportunities: string[];
}

function Dots({ n, tone }: { n: number; tone: string }) {
  return <span className="flex gap-0.5">{[1,2,3,4,5].map(i => <span key={i} className={`h-2 w-2 rounded-full ${i <= n ? tone : "bg-muted"}`} />)}</span>;
}

function forceColor(v: number) { return v >= 67 ? "#ef4444" : v >= 34 ? "#f59e0b" : "#10b981"; }

export function StrategyDashboard({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<StrategyResp>({
    queryKey: ["strategy", companyId],
    queryFn: () => apiClient.get(`/companies/${companyId}/strategy`) as unknown as Promise<StrategyResp>,
    refetchInterval: (q) => (q.state.data && !q.state.data.has_data ? 5000 : false),
  });

  const gen = useMutation({
    mutationFn: () => apiClient.post(`/companies/${companyId}/strategy/generate`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategy", companyId] }),
  });

  if (isLoading) return <div className="p-12 text-center text-muted-foreground animate-pulse">Loading strategy…</div>;

  if (!data?.has_data) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <Compass className="h-10 w-10 text-muted-foreground/50" />
          <p className="font-medium">No strategy analysis yet</p>
          <p className="max-w-md text-sm text-muted-foreground">
            A McKinsey-style strategist synthesizes financials, competition and due diligence into scored
            strategic options, prioritized recommendations and Porter's Five Forces.
          </p>
          <Button onClick={() => gen.mutate()} disabled={gen.isPending} className="gap-2">
            {gen.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</> : <><Compass className="h-4 w-4" /> Generate strategy</>}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {data.executive_summary && (
        <Card><CardContent className="py-5"><p className="text-base leading-relaxed text-foreground/85">{data.executive_summary}</p></CardContent></Card>
      )}

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Layers className="h-5 w-5 text-indigo-500" /> Strategic Options</CardTitle>
          <CardDescription>Scored by impact / feasibility / risk</CardDescription></CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow><TableHead>Option</TableHead><TableHead>Impact</TableHead><TableHead>Feasibility</TableHead><TableHead>Risk</TableHead><TableHead>Investment</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.strategic_options.map((o, i) => (
                <TableRow key={i}>
                  <TableCell className="align-top"><div className="font-medium">{o.title}</div><div className="text-xs text-muted-foreground">{o.description}</div></TableCell>
                  <TableCell className="align-top"><Dots n={o.impact} tone="bg-indigo-500" /></TableCell>
                  <TableCell className="align-top"><Dots n={o.feasibility} tone="bg-emerald-500" /></TableCell>
                  <TableCell className="align-top"><Dots n={o.risk} tone="bg-rose-500" /></TableCell>
                  <TableCell className="align-top text-sm">{o.investment}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Target className="h-5 w-5 text-indigo-500" /> Prioritized Recommendations</CardTitle></CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {data.recommendations.map((r, i) => (
                <li key={i} className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">{i+1}</span>
                  <div><p className="text-sm font-medium">{r.title}</p>{r.expected_outcome && <p className="text-xs text-muted-foreground">{r.expected_outcome}</p>}</div>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="h-5 w-5 text-emerald-500" /> Growth Opportunities</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.growth_opportunities.map((g, i) => (
                <li key={i} className="flex gap-2 text-sm text-foreground/80"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />{g}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Shield className="h-5 w-5 text-amber-500" /> Porter's Five Forces</CardTitle>
          <CardDescription>Higher intensity = more adverse</CardDescription></CardHeader>
        <CardContent className="space-y-3">
          {data.porters_five_forces.map((p, i) => (
            <div key={i}>
              <div className="flex items-center justify-between text-sm"><span className="font-medium">{p.force}</span><span className="text-xs text-muted-foreground">{p.level}/100</span></div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full" style={{ width: `${p.level}%`, backgroundColor: forceColor(p.level) }} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{p.summary}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
