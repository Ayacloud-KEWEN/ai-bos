"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Circle, CircleDot, CheckCircle2, Target, Package, Flag } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Step { id: string; order: number; title: string; objective: string; owner: string; deliverable: string; kpi: string; status: string; }
interface PB {
  id: string; title: string; objective: string; category: string; difficulty: string;
  estimated_time: string; expected_outcome: string; status: string; progress: number;
  steps: Step[]; deliverables: string[]; kpis: string[]; success_criteria: string[];
}

const NEXT: Record<string, string> = { todo: "doing", doing: "done", done: "todo" };
const ICON: Record<string, React.ElementType> = { todo: Circle, doing: CircleDot, done: CheckCircle2 };
const TONE: Record<string, string> = { todo: "text-muted-foreground", doing: "text-amber-500", done: "text-emerald-600" };

export function PlaybookView({ playbookId }: { playbookId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<PB>({
    queryKey: ["playbook", playbookId],
    queryFn: () => apiClient.get(`/playbooks/${playbookId}`) as unknown as Promise<PB>,
    refetchInterval: (q) => (q.state.data?.status === "Generating" ? 4000 : false),
  });

  const setStatus = useMutation({
    mutationFn: ({ stepId, status }: { stepId: string; status: string }) =>
      apiClient.patch(`/playbooks/${playbookId}/steps/${stepId}`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["playbook", playbookId] }),
  });

  if (isLoading || !data) return <div className="p-6 text-sm text-muted-foreground animate-pulse">Loading playbook…</div>;
  if (data.status === "Generating") return <div className="p-6 text-sm text-muted-foreground flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Generating executable playbook…</div>;
  if (data.status === "Failed") return <div className="p-6 text-sm text-destructive">Generation failed. Ensure the company has analysis, then regenerate.</div>;

  return (
    <div className="space-y-5">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-semibold">{data.title}</h3>
          {data.category && <Badge variant="secondary">{data.category}</Badge>}
          {data.difficulty && <Badge variant="outline">{data.difficulty}</Badge>}
          {data.estimated_time && <span className="text-xs text-muted-foreground">{data.estimated_time}</span>}
        </div>
        {data.objective && <p className="mt-1 text-sm text-muted-foreground">{data.objective}</p>}
        <div className="mt-3 flex items-center gap-3">
          <Progress value={data.progress} className="h-2 flex-1" />
          <span className="text-sm font-medium">{data.progress}%</span>
        </div>
      </div>

      <div className="space-y-2">
        {data.steps.map((s) => {
          const Icon = ICON[s.status] || Circle;
          return (
            <div key={s.id} className="flex gap-3 rounded-lg border p-3">
              <button title="Click to advance status" className="mt-0.5 shrink-0" onClick={() => setStatus.mutate({ stepId: s.id, status: NEXT[s.status] || "todo" })}>
                <Icon className={`h-5 w-5 ${TONE[s.status]}`} />
              </button>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-muted-foreground">{s.order}</span>
                  <span className={`text-sm font-medium ${s.status === "done" ? "line-through text-muted-foreground" : ""}`}>{s.title}</span>
                </div>
                {s.objective && <p className="mt-0.5 text-xs text-muted-foreground">{s.objective}</p>}
                <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  {s.owner && <span>👤 {s.owner}</span>}
                  {s.deliverable && <span>📦 {s.deliverable}</span>}
                  {s.kpi && <span>🎯 {s.kpi}</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <MiniList title="Deliverables" items={data.deliverables} icon={Package} />
        <MiniList title="KPIs" items={data.kpis} icon={Target} />
        <MiniList title="Success Criteria" items={data.success_criteria} icon={Flag} />
      </div>
    </div>
  );
}

function MiniList({ title, items, icon: Icon }: { title: string; items: string[]; icon: React.ElementType }) {
  if (!items?.length) return null;
  return (
    <Card><CardHeader className="pb-2"><CardTitle className="flex items-center gap-1.5 text-sm"><Icon className="h-4 w-4 text-muted-foreground" /> {title}</CardTitle></CardHeader>
      <CardContent><ul className="space-y-1">{items.map((it, i) => <li key={i} className="text-xs text-foreground/80">• {it}</li>)}</ul></CardContent></Card>
  );
}
