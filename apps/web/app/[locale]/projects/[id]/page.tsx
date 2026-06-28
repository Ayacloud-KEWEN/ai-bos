"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FolderKanban, Building, Sparkles, Loader2, BookOpen, ChevronDown } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Link } from "@/i18n/routing";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { PlaybookView } from "@/components/playbook/playbook-view";

const GOAL_PRESETS = ["进入新市场 / Market entry", "B2B 销售管道 / Sales pipeline", "融资 / Fundraising", "增长战略 / Growth strategy", "降本增效 / Cost optimization"];

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const queryClient = useQueryClient();

  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: project, isLoading } = useQuery<any>({
    queryKey: ["project", projectId],
    queryFn: () => apiClient.get(`/projects/${projectId}`) as unknown as Promise<any>,
    refetchInterval: 8000,
  });
  const { data: companies = [] } = useQuery<any[]>({
    queryKey: ["companies"],
    queryFn: () => apiClient.get("/companies/") as unknown as Promise<any[]>,
  });

  const gen = useMutation({
    mutationFn: () => apiClient.post("/playbooks/generate", {
      company_id: companyId || project?.company_id, goal, project_id: projectId,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setOpen(false); setGoal("");
    },
  });

  if (isLoading || !project) return <div className="p-8 text-muted-foreground animate-pulse">Loading project…</div>;

  const effectiveCompany = companyId || project.company_id;

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/projects")} className="mt-1"><ArrowLeft className="h-5 w-5" /></Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2"><FolderKanban className="h-7 w-7 text-primary" /> {project.name}</h1>
          <div className="flex items-center gap-4 mt-2 text-muted-foreground text-sm">
            <Badge variant="outline">{project.status}</Badge>
            {project.company_name && <Link href={`/company-intelligence/companies/${project.company_id}`} className="flex items-center gap-1 text-primary hover:underline"><Building className="h-4 w-4" /> {project.company_name}</Link>}
          </div>
          {project.objective && <p className="mt-2 text-sm text-foreground/80 max-w-2xl">{project.objective}</p>}
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button className="gap-2"><Sparkles className="h-4 w-4" /> Generate Playbook</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Generate Executable Playbook</DialogTitle><DialogDescription>AI turns the company's intelligence into a step-by-step playbook.</DialogDescription></DialogHeader>
            <div className="space-y-3">
              {!project.company_id && (
                <div className="space-y-1.5"><label className="text-sm font-medium">Company</label>
                  <select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
                    <option value="">— Select company —</option>
                    {companies.filter((c) => !(c.status || "").startsWith("Discovered")).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
              )}
              <div className="space-y-1.5"><label className="text-sm font-medium">Goal</label>
                <Input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="e.g. 进入欧洲市场" />
                <div className="flex flex-wrap gap-1.5 pt-1">{GOAL_PRESETS.map((g) => <button key={g} onClick={() => setGoal(g)} className="rounded-full border px-2.5 py-0.5 text-xs hover:bg-muted/50">{g}</button>)}</div>
              </div>
              <div className="flex justify-end gap-2 border-t pt-3">
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button disabled={!goal || !effectiveCompany || gen.isPending} onClick={() => gen.mutate()}>{gen.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate"}</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {project.playbooks?.length === 0 ? (
        <div className="py-16 flex flex-col items-center justify-center border-2 border-dashed rounded-lg text-muted-foreground">
          <BookOpen className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p>No playbooks yet.</p><p className="text-sm mt-1">Generate one from a company's intelligence to start executing.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {project.playbooks.map((pb: any) => (
            <Card key={pb.id}>
              <CardHeader className="cursor-pointer pb-3" onClick={() => setExpanded(expanded === pb.id ? null : pb.id)}>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base"><BookOpen className="h-5 w-5 text-primary" /> {pb.title}
                    <Badge variant={pb.status === "Ready" ? "secondary" : "outline"} className="ml-1 text-[10px]">{pb.status}</Badge></CardTitle>
                  <div className="flex items-center gap-3 w-48">
                    <Progress value={pb.progress} className="h-2 flex-1" />
                    <span className="text-xs text-muted-foreground">{pb.progress}%</span>
                    <ChevronDown className={`h-4 w-4 transition-transform ${expanded === pb.id ? "rotate-180" : ""}`} />
                  </div>
                </div>
              </CardHeader>
              {expanded === pb.id && <CardContent className="border-t pt-4"><PlaybookView playbookId={pb.id} /></CardContent>}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
