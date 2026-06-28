"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, GraduationCap, Loader2, Send, Trophy, MessageCircle, CheckCircle2 } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function scoreColor(v: number) { return v >= 75 ? "text-emerald-600" : v >= 50 ? "text-amber-600" : "text-rose-600"; }

export default function SimulationPage() {
  const params = useParams();
  const router = useRouter();
  const simId = params.id as string;
  const queryClient = useQueryClient();
  const [decision, setDecision] = useState("");

  const { data: sim } = useQuery<any>({
    queryKey: ["sim", simId], queryFn: () => apiClient.get(`/academy/simulations/${simId}`) as unknown as Promise<any>,
  });

  const act = useMutation({
    mutationFn: (d: string) => apiClient.post(`/academy/simulations/${simId}/act`, { decision: d }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["sim", simId] }); setDecision(""); },
  });

  if (!sim) return <div className="p-8 text-muted-foreground animate-pulse">Loading simulation…</div>;
  const done = sim.status === "completed";

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 p-8 animate-in fade-in duration-500">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.push("/academy/courses")}><ArrowLeft className="h-5 w-5" /></Button>
        <GraduationCap className="h-6 w-6 text-primary" />
        <div className="flex-1"><h1 className="text-xl font-bold">{sim.title}</h1><p className="text-xs text-muted-foreground">{sim.track} · round {sim.round}</p></div>
        <Badge variant={done ? "secondary" : "outline"}>{sim.status}</Badge>
      </div>

      {/* 历史回合 */}
      {(sim.history || []).map((h: any, i: number) => (
        <div key={i} className="space-y-2">
          <Card><CardContent className="py-3 text-sm whitespace-pre-wrap">{h.situation}</CardContent></Card>
          <div className="flex justify-end"><div className="max-w-[85%] rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">{h.decision}</div></div>
          {h.outcome && (
            <Card className="border-muted">
              <CardContent className="space-y-2 py-3 text-sm">
                <p className="whitespace-pre-wrap">{h.outcome}</p>
                {h.feedback && <p className="flex gap-2 rounded-md bg-muted/40 p-2 text-xs"><MessageCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-indigo-500" />{h.feedback}</p>}
                <div className="text-xs">Decision score: <span className={`font-bold ${scoreColor(h.score)}`}>{h.score}</span></div>
              </CardContent>
            </Card>
          )}
        </div>
      ))}

      {/* 当前情境 / 结果 */}
      {!done && sim.current?.situation && (
        <Card className="border-primary/30">
          <CardHeader className="pb-2"><CardTitle className="text-base">现在轮到你 · Your move</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm whitespace-pre-wrap">{sim.current.situation}</p>
            {!act.isPending && (sim.current.options || []).length > 0 && (
              <div className="flex flex-col gap-2">
                {sim.current.options.map((o: string, i: number) => (
                  <button key={i} onClick={() => act.mutate(o)} className="rounded-lg border px-3 py-2 text-left text-sm hover:border-primary/50 hover:bg-primary/5">{o}</button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <Input value={decision} onChange={(e) => setDecision(e.target.value)} onKeyDown={(e) => e.key === "Enter" && decision && act.mutate(decision)} placeholder="或自由输入你的决策…" disabled={act.isPending} />
              <Button size="icon" disabled={!decision || act.isPending} onClick={() => act.mutate(decision)}>{act.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
            </div>
            {act.isPending && <p className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" /> 导师正在推演后果…</p>}
          </CardContent>
        </Card>
      )}

      {/* 最终评估 */}
      {done && sim.final_assessment && (
        <Card className="border-emerald-300">
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><Trophy className="h-5 w-5 text-amber-500" /> Final Assessment</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm leading-relaxed">{sim.final_assessment.summary}</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(sim.final_assessment.scores || {}).map(([k, v]: any) => (
                <div key={k} className="rounded-lg border p-3 text-center">
                  <p className={`text-2xl font-bold ${scoreColor(Number(v))}`}>{v}</p>
                  <p className="text-xs text-muted-foreground capitalize">{k}</p>
                </div>
              ))}
            </div>
            <Button variant="outline" className="gap-2" onClick={() => router.push("/academy/courses")}><CheckCircle2 className="h-4 w-4" /> Back to Academy</Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
