"use client";

import { useRef, useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ArrowLeft, Bot, Send, Loader2, User, Sparkles, Database } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

interface Msg { role: "user" | "assistant"; content: string; sources?: { snippet: string }[]; }

export default function AgentChatPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params.id as string;
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: agent } = useQuery<any>({
    queryKey: ["agent", agentId],
    queryFn: () => apiClient.get(`/agents/${agentId}`) as unknown as Promise<any>,
  });

  const ask = useMutation({
    mutationFn: (question: string) => apiClient.post(`/agents/${agentId}/chat`, {
      question, history: messages.map((m) => ({ role: m.role, content: m.content })),
    }) as unknown as Promise<{ answer: string; sources: { snippet: string }[] }>,
    onSuccess: (res) => setMessages((m) => [...m, { role: "assistant", content: res.answer, sources: res.sources }]),
  });

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, ask.isPending]);

  const send = () => {
    const q = input.trim();
    if (!q || ask.isPending) return;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput(""); ask.mutate(q);
  };

  if (!agent) return <div className="p-8 text-muted-foreground animate-pulse">Loading agent…</div>;

  return (
    <div className="flex h-[calc(100vh-1rem)] flex-col p-6">
      <div className="flex items-center gap-3 pb-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/agents/library")}><ArrowLeft className="h-5 w-5" /></Button>
        <Bot className="h-7 w-7 text-primary" />
        <div className="flex-1">
          <h1 className="text-xl font-bold">{agent.name}</h1>
          <p className="text-sm text-muted-foreground">{agent.role}{agent.goal ? ` · ${agent.goal}` : ""}</p>
        </div>
        {agent.knowledge_company_name && <Badge variant="secondary" className="gap-1"><Database className="h-3 w-3" /> {agent.knowledge_company_name}</Badge>}
        {agent.use_knowledge_base && <Badge variant="secondary" className="gap-1"><Database className="h-3 w-3" /> Knowledge Base</Badge>}
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden">
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-muted-foreground">
              <Sparkles className="h-8 w-8 text-primary/60" />
              <p className="text-sm max-w-md">{agent.goal || `Chat with ${agent.name}.`}{agent.knowledge_company_name ? ` Grounded in ${agent.knowledge_company_name}'s documents.` : ""}</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-primary" />}
              </div>
              <div className={`max-w-[80%] space-y-2`}>
                <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted/50"}`}>
                  <p className="whitespace-pre-wrap">{m.content}</p>
                </div>
                {m.sources && m.sources.length > 0 && (
                  <details className="text-xs text-muted-foreground"><summary className="cursor-pointer">{m.sources.length} 处来源</summary>
                    <div className="mt-1 space-y-1">{m.sources.map((s, j) => <div key={j} className="rounded border bg-background p-2">{s.snippet}</div>)}</div>
                  </details>
                )}
              </div>
            </div>
          ))}
          {ask.isPending && <div className="flex gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted"><Bot className="h-4 w-4 text-primary" /></div><div className="flex items-center rounded-2xl bg-muted/50 px-4 py-3"><Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /></div></div>}
        </div>
        <div className="flex items-center gap-2 border-t p-3">
          <Input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask the agent…" disabled={ask.isPending} />
          <Button onClick={send} disabled={!input.trim() || ask.isPending} size="icon"><Send className="h-4 w-4" /></Button>
        </div>
      </Card>
    </div>
  );
}
