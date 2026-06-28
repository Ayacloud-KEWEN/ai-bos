"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bot, Plus, Sparkles, Loader2, ChevronRight, Trash2 } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";

interface Agent { id: string; name: string; role: string; goal: string; }
interface Template { key: string; name: string; role: string; goal: string; }

export default function AgentLibraryPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [goal, setGoal] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [provider, setProvider] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [useKb, setUseKb] = useState(false);

  const { data: agents = [], isLoading } = useQuery<Agent[]>({
    queryKey: ["agents"], queryFn: () => apiClient.get("/agents") as unknown as Promise<Agent[]>,
  });
  const { data: tplData } = useQuery<{ templates: Template[] }>({
    queryKey: ["agent-templates"], queryFn: () => apiClient.get("/agents/templates") as unknown as Promise<any>,
  });
  const { data: companies = [] } = useQuery<any[]>({
    queryKey: ["companies"], queryFn: () => apiClient.get("/companies/") as unknown as Promise<any[]>,
  });
  const { data: providers } = useQuery<any>({
    queryKey: ["model-settings"], queryFn: () => apiClient.get("/settings/model") as unknown as Promise<any>,
  });

  const fromTemplate = useMutation({
    mutationFn: (key: string) => apiClient.post(`/agents/from-template/${key}`, {}) as unknown as Promise<{ id: string }>,
    onSuccess: (r) => { queryClient.invalidateQueries({ queryKey: ["agents"] }); router.push(`/agents/${r.id}`); },
  });
  const create = useMutation({
    mutationFn: () => apiClient.post("/agents", { name, role, goal, system_prompt: systemPrompt, provider, knowledge_company_id: companyId || null, use_knowledge_base: useKb }) as unknown as Promise<{ id: string }>,
    onSuccess: (r) => { queryClient.invalidateQueries({ queryKey: ["agents"] }); setOpen(false); router.push(`/agents/${r.id}`); },
  });
  const del = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/agents/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground mt-1">Configurable AI specialists — give them a role, a prompt, and optional company knowledge.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button className="gap-2"><Plus className="h-4 w-4" /> New Agent</Button></DialogTrigger>
          <DialogContent className="sm:max-w-[560px]">
            <DialogHeader><DialogTitle>New Agent</DialogTitle><DialogDescription>Define a custom AI specialist.</DialogDescription></DialogHeader>
            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5"><label className="text-sm font-medium">Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. My CFO" /></div>
                <div className="space-y-1.5"><label className="text-sm font-medium">Role</label><Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="AI CFO Assistant" /></div>
              </div>
              <div className="space-y-1.5"><label className="text-sm font-medium">Goal</label><Input value={goal} onChange={(e) => setGoal(e.target.value)} /></div>
              <div className="space-y-1.5"><label className="text-sm font-medium">System Prompt</label>
                <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows={4} className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm" placeholder="You are a senior financial analyst…" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5"><label className="text-sm font-medium">Model</label>
                  <select value={provider} onChange={(e) => setProvider(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
                    <option value="">Active default</option>
                    {(providers?.providers || []).map((p: any) => <option key={p.key} value={p.key} disabled={!p.configured}>{p.label}</option>)}
                  </select></div>
                <div className="space-y-1.5"><label className="text-sm font-medium">Knowledge (company)</label>
                  <select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
                    <option value="">None</option>
                    {companies.filter((c) => !(c.status || "").startsWith("Discovered")).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select></div>
              </div>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input type="checkbox" checked={useKb} onChange={(e) => setUseKb(e.target.checked)} className="h-4 w-4 rounded border-input" />
                Use organization Knowledge Base
              </label>
              <div className="flex justify-end gap-2 border-t pt-3">
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button disabled={!name || create.isPending} onClick={() => create.mutate()}>{create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create"}</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* 模板快速创建 */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Start from a template</p>
        <div className="flex flex-wrap gap-2">
          {(tplData?.templates || []).map((t) => (
            <button key={t.key} onClick={() => fromTemplate.mutate(t.key)} disabled={fromTemplate.isPending}
              className="flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm hover:bg-muted/50">
              <Sparkles className="h-3.5 w-3.5 text-indigo-500" /> {t.name}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? <div className="text-muted-foreground animate-pulse">Loading…</div> : agents.length === 0 ? (
        <div className="py-12 flex flex-col items-center justify-center border-2 border-dashed rounded-lg text-muted-foreground">
          <Bot className="h-12 w-12 text-muted-foreground/30 mb-4" /><p>No agents yet. Start from a template above.</p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((a) => (
            <Card key={a.id} className="cursor-pointer hover:border-primary/40 hover:shadow-md transition-all group relative" onClick={() => router.push(`/agents/${a.id}`)}>
              <Button variant="ghost" size="icon" className="absolute top-2 right-2 h-7 w-7 opacity-0 group-hover:opacity-100"
                onClick={(e) => { e.stopPropagation(); if (confirm("Delete agent?")) del.mutate(a.id); }}><Trash2 className="h-3.5 w-3.5 text-rose-500" /></Button>
              <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-lg"><Bot className="h-5 w-5 text-primary" />{a.name}</CardTitle>
                <CardDescription>{a.role}</CardDescription></CardHeader>
              <CardContent><p className="text-sm text-muted-foreground line-clamp-2">{a.goal}</p>
                <div className="mt-2 flex justify-end text-sm text-primary opacity-0 group-hover:opacity-100"><span>Chat</span><ChevronRight className="h-4 w-4" /></div></CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
