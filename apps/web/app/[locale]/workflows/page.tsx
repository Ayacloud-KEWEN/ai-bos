"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { GitMerge, Plus, Sparkles, Loader2, ChevronRight } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface WF { id: string; name: string; description: string; node_count: number; }

export default function WorkflowsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: workflows = [], isLoading } = useQuery<WF[]>({
    queryKey: ["workflows"],
    queryFn: () => apiClient.get("/workflows") as unknown as Promise<WF[]>,
  });

  const newBlank = useMutation({
    mutationFn: () => apiClient.post("/workflows", { name: "Untitled Workflow", nodes: [], edges: [] }) as unknown as Promise<{ id: string }>,
    onSuccess: (r) => router.push(`/workflows/${r.id}`),
  });
  const newTemplate = useMutation({
    mutationFn: () => apiClient.post("/workflows/template", {}) as unknown as Promise<{ id: string }>,
    onSuccess: (r) => { queryClient.invalidateQueries({ queryKey: ["workflows"] }); router.push(`/workflows/${r.id}`); },
  });

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Workflows</h1>
          <p className="text-muted-foreground mt-1">Visual pipelines that auto-orchestrate intelligence analysis (LangGraph).</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => newTemplate.mutate()} disabled={newTemplate.isPending}>
            {newTemplate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Full Pipeline Template
          </Button>
          <Button className="gap-2" onClick={() => newBlank.mutate()} disabled={newBlank.isPending}><Plus className="h-4 w-4" /> New Workflow</Button>
        </div>
      </div>

      {isLoading ? <div className="text-muted-foreground animate-pulse">Loading…</div> : workflows.length === 0 ? (
        <div className="py-16 flex flex-col items-center justify-center border-2 border-dashed rounded-lg text-muted-foreground">
          <GitMerge className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p>No workflows yet.</p><p className="text-sm mt-1">Start from the full-pipeline template, then run it against any company.</p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {workflows.map((w) => (
            <Card key={w.id} className="cursor-pointer hover:border-primary/40 hover:shadow-md transition-all group" onClick={() => router.push(`/workflows/${w.id}`)}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg"><GitMerge className="h-5 w-5 text-primary" />{w.name}</CardTitle>
                <CardDescription className="line-clamp-2">{w.description || "No description"}</CardDescription>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <Badge variant="secondary">{w.node_count} nodes</Badge>
                <ChevronRight className="h-4 w-4 text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
