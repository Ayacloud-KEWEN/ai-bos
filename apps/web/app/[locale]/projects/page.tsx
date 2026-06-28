"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, FolderKanban, ChevronRight, Loader2 } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";

interface Proj { id: string; name: string; objective: string; company_id: string | null; status: string; playbooks_count: number; progress: number; }

export default function ProjectsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [companyId, setCompanyId] = useState("");

  const { data: projects = [], isLoading } = useQuery<Proj[]>({
    queryKey: ["projects"],
    queryFn: () => apiClient.get("/projects") as unknown as Promise<Proj[]>,
  });
  const { data: companies = [] } = useQuery<any[]>({
    queryKey: ["companies"],
    queryFn: () => apiClient.get("/companies/") as unknown as Promise<any[]>,
  });

  const create = useMutation({
    mutationFn: () => apiClient.post("/projects", { name, objective, company_id: companyId || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setOpen(false); setName(""); setObjective(""); setCompanyId("");
    },
  });

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground mt-1">Turn company intelligence into executable playbooks.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button className="gap-2"><Plus className="h-4 w-4" /> New Project</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>New Project</DialogTitle><DialogDescription>Organize execution around a goal and (optionally) a company.</DialogDescription></DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1.5"><label className="text-sm font-medium">Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Enter the EU market" /></div>
              <div className="space-y-1.5"><label className="text-sm font-medium">Objective</label><Input value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="What success looks like" /></div>
              <div className="space-y-1.5"><label className="text-sm font-medium">Linked company (optional)</label>
                <select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
                  <option value="">— None —</option>
                  {companies.filter((c) => !(c.status || "").startsWith("Discovered")).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-2 border-t pt-3">
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button disabled={!name || create.isPending} onClick={() => create.mutate()}>{create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create"}</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? <div className="text-muted-foreground animate-pulse">Loading…</div> : projects.length === 0 ? (
        <div className="py-16 flex flex-col items-center justify-center border-2 border-dashed rounded-lg text-muted-foreground">
          <FolderKanban className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p>No projects yet.</p><p className="text-sm mt-1">Create one to generate executable playbooks from your company intelligence.</p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Card key={p.id} className="cursor-pointer hover:border-primary/40 hover:shadow-md transition-all group" onClick={() => router.push(`/projects/${p.id}`)}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg"><FolderKanban className="h-5 w-5 text-primary" /><span className="truncate">{p.name}</span></CardTitle>
                <CardDescription className="line-clamp-2">{p.objective || "No objective set"}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2"><Badge variant="outline">{p.status}</Badge><Badge variant="secondary">{p.playbooks_count} playbook(s)</Badge></div>
                <div><div className="flex justify-between text-xs text-muted-foreground mb-1"><span>Progress</span><span>{p.progress}%</span></div><Progress value={p.progress} className="h-2" /></div>
                <div className="flex items-center justify-end text-sm text-primary opacity-0 group-hover:opacity-100 transition-opacity">Open <ChevronRight className="h-4 w-4" /></div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
