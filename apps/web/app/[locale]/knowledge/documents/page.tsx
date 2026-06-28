"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, UploadCloud, FileText, Trash2, Loader2, Sparkles, Send, BookOpen } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface Doc { id: string; title: string; filename: string; size: number; chunk_count: number; status: string; }

export default function KnowledgeBasePage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<{ answer: string; sources: any[] } | null>(null);

  const { data: docs = [] } = useQuery<Doc[]>({
    queryKey: ["kb-docs"],
    queryFn: () => apiClient.get("/knowledge/documents") as unknown as Promise<Doc[]>,
    refetchInterval: (q) => ((q.state.data || []).some((d: Doc) => d.status === "Indexing") ? 4000 : false),
  });

  const upload = useMutation({
    mutationFn: () => {
      const fd = new FormData(); fd.append("title", title || file!.name); fd.append("file", file!);
      return apiClient.post("/knowledge/documents", fd, { headers: { "Content-Type": "multipart/form-data" }, timeout: 120000 });
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["kb-docs"] }); setTitle(""); setFile(null); },
  });
  const del = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/knowledge/documents/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["kb-docs"] }),
  });
  const ask = useMutation({
    mutationFn: () => apiClient.post("/knowledge/ask", { question }) as unknown as Promise<{ answer: string; sources: any[] }>,
    onSuccess: (r) => setAnswer(r),
  });

  const ready = docs.filter((d) => d.status === "Ready").length;

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2"><Database className="h-7 w-7 text-primary" /> Knowledge Base</h1>
        <p className="text-muted-foreground mt-1">Org-level knowledge — frameworks, case studies, research. Reusable across companies & agents.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 上传 + 列表 */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Add Document</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title (e.g. Porter's Five Forces framework)" />
              <div className="flex items-center gap-3">
                <Input type="file" id="kb-file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.csv,.html" className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] || null)} />
                <label htmlFor="kb-file" className="flex flex-1 cursor-pointer items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm hover:bg-muted/30">
                  <UploadCloud className="h-4 w-4 text-muted-foreground" />{file ? file.name : "Select a file (PDF/Word/PPT/Excel…)"}
                </label>
                <Button disabled={!file || upload.isPending} onClick={() => upload.mutate()}>{upload.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Upload"}</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Documents ({docs.length})</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {docs.length === 0 ? <p className="py-6 text-center text-sm text-muted-foreground">No documents yet.</p> :
                docs.map((d) => (
                  <div key={d.id} className="flex items-center gap-3 rounded-lg border p-3">
                    <FileText className="h-5 w-5 shrink-0 text-rose-500" />
                    <a href={`${API_BASE}/knowledge/documents/${d.id}/file`} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1 hover:underline">
                      <p className="truncate text-sm font-medium">{d.title}</p>
                      <p className="text-xs text-muted-foreground">{d.chunk_count} chunks</p>
                    </a>
                    <Badge variant={d.status === "Ready" ? "secondary" : d.status === "Failed" ? "destructive" : "outline"} className="text-[10px]">
                      {d.status === "Indexing" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}{d.status}
                    </Badge>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => del.mutate(d.id)}><Trash2 className="h-4 w-4 text-rose-500" /></Button>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>

        {/* 问答 */}
        <Card className="flex flex-col">
          <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-5 w-5 text-indigo-500" /> Ask the Knowledge Base</CardTitle></CardHeader>
          <CardContent className="flex flex-1 flex-col gap-3">
            <p className="text-xs text-muted-foreground">{ready} document(s) ready. Ask across all of them.</p>
            <div className="flex gap-2">
              <Input value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && question && ask.mutate()} placeholder="e.g. 如何做市场进入分析？" />
              <Button size="icon" disabled={!question || ask.isPending} onClick={() => ask.mutate()}>{ask.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
            </div>
            {answer && (
              <div className="flex-1 space-y-3 overflow-y-auto">
                <div className="rounded-lg border bg-muted/30 p-3 text-sm leading-relaxed whitespace-pre-wrap">{answer.answer}</div>
                {answer.sources?.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs font-medium text-muted-foreground flex items-center gap-1"><BookOpen className="h-3 w-3" /> Sources</p>
                    {answer.sources.map((s, i) => <div key={i} className="rounded border p-2 text-xs"><b>{s.title}</b><br />{s.snippet}</div>)}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
