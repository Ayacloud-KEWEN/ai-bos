"use client";

import { useRef, useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Database, Loader2, Sparkles, FileText, User } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

interface Source { document_id: string; snippet: string; }
interface Msg { role: "user" | "assistant"; content: string; sources?: Source[]; }

export function CompanyChat({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: status } = useQuery<{ indexed: boolean; chunk_count: number }>({
    queryKey: ["index-status", companyId],
    queryFn: () =>
      apiClient.get(`/companies/${companyId}/index/status`) as unknown as Promise<{ indexed: boolean; chunk_count: number }>,
    refetchInterval: (q) => (q.state.data && !q.state.data.indexed ? 4000 : false),
  });

  const buildIndex = useMutation({
    mutationFn: () => apiClient.post(`/companies/${companyId}/index`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["index-status", companyId] }),
  });

  const ask = useMutation({
    mutationFn: (question: string) =>
      apiClient.post(`/companies/${companyId}/chat`, {
        question,
        history: messages.map((m) => ({ role: m.role, content: m.content })),
      }) as unknown as Promise<{ answer: string; sources: Source[] }>,
    onSuccess: (res) => {
      setMessages((m) => [...m, { role: "assistant", content: res.answer, sources: res.sources }]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, ask.isPending]);

  const send = () => {
    const q = input.trim();
    if (!q || ask.isPending) return;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    ask.mutate(q);
  };

  // 未建立索引
  if (status && !status.indexed) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <Database className="h-10 w-10 text-muted-foreground/50" />
          <p className="font-medium">Knowledge base not built yet</p>
          <p className="max-w-md text-sm text-muted-foreground">
            Build a searchable index from this company’s uploaded documents to chat with them
            (retrieval-augmented). Uses local embeddings; answers use your selected model.
          </p>
          <Button onClick={() => buildIndex.mutate()} disabled={buildIndex.isPending} className="gap-2">
            {buildIndex.isPending || (buildIndex.isSuccess && !status.indexed)
              ? <><Loader2 className="h-4 w-4 animate-spin" /> Building…</>
              : <><Database className="h-4 w-4" /> Build knowledge base</>}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const suggestions = ["这家公司的主要风险是什么？", "营收和盈利情况如何？", "主要竞争对手有哪些？"];

  return (
    <Card className="flex h-[600px] flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center text-muted-foreground">
            <Sparkles className="h-8 w-8 text-primary/60" />
            <p className="text-sm">Ask anything about this company — grounded in its documents.</p>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button key={s} onClick={() => { setInput(s); }}
                  className="rounded-full border px-3 py-1 text-xs hover:bg-muted/50">{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
              {m.role === "user" ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4 text-primary" />}
            </div>
            <div className={`max-w-[80%] space-y-2 ${m.role === "user" ? "items-end" : ""}`}>
              <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted/50"}`}>
                <p className="whitespace-pre-wrap">{m.content}</p>
              </div>
              {m.sources && m.sources.length > 0 && (
                <details className="text-xs text-muted-foreground">
                  <summary className="cursor-pointer select-none">{m.sources.length} 处来源</summary>
                  <div className="mt-2 space-y-1.5">
                    {m.sources.map((s, j) => (
                      <div key={j} className="flex gap-1.5 rounded-md border bg-background p-2">
                        <FileText className="mt-0.5 h-3 w-3 shrink-0 text-rose-400" />
                        <span>{s.snippet}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        ))}

        {ask.isPending && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted"><Sparkles className="h-4 w-4 text-primary" /></div>
            <div className="flex items-center rounded-2xl bg-muted/50 px-4 py-3"><Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /></div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 border-t p-3">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="问点什么…（如：主要风险？营收趋势？）"
          disabled={ask.isPending}
        />
        <Button onClick={send} disabled={!input.trim() || ask.isPending} size="icon"><Send className="h-4 w-4" /></Button>
      </div>
    </Card>
  );
}
