"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Cpu, Cloud, KeyRound, Loader2, ShieldCheck } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface Provider {
  key: string; label: string; needs_key: boolean; model: string; default_model: string; configured: boolean;
}
interface ModelSettings { active: string; providers: Provider[]; }

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = useState<Record<string, { model: string; api_key: string }>>({});

  const { data, isLoading } = useQuery<ModelSettings>({
    queryKey: ["model-settings"],
    queryFn: () => apiClient.get("/settings/model") as unknown as Promise<ModelSettings>,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["model-settings"] });

  const activate = useMutation({
    mutationFn: (provider: string) => apiClient.put("/settings/model", { active_provider: provider }),
    onSuccess: invalidate,
  });

  const saveConfig = useMutation({
    mutationFn: (p: { provider: string; model: string; api_key: string }) =>
      apiClient.put("/settings/model", { config: p }),
    onSuccess: (_d, vars) => {
      invalidate();
      setDrafts((s) => ({ ...s, [vars.provider]: { model: vars.model, api_key: "" } }));
    },
  });

  if (isLoading || !data) {
    return <div className="p-8 text-muted-foreground animate-pulse">Loading settings…</div>;
  }

  return (
    <div className="flex flex-col gap-6 p-8 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">Configure the AI model powering company analysis.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">AI Model Provider</CardTitle>
          <CardDescription>
            Local Ollama is the default (data never leaves your machine). Switch to an online model for
            faster, parallel analysis of large documents. Sensitive companies can stay on local.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.providers.map((p) => {
            const active = p.key === data.active;
            const draft = drafts[p.key] ?? { model: p.model, api_key: "" };
            const online = p.needs_key;
            return (
              <div key={p.key} className={`rounded-xl border p-4 transition-colors ${active ? "border-primary bg-primary/5" : "hover:bg-muted/30"}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {online ? <Cloud className="h-5 w-5 text-sky-500" /> : <Cpu className="h-5 w-5 text-emerald-500" />}
                    <div>
                      <div className="flex items-center gap-2 font-medium">
                        {p.label}
                        {!online && <Badge variant="secondary" className="text-[10px]"><ShieldCheck className="mr-1 h-3 w-3" />Private</Badge>}
                        {active && <Badge className="text-[10px]">Active</Badge>}
                      </div>
                      <p className="text-xs text-muted-foreground">Model: {p.model}</p>
                    </div>
                  </div>
                  {active ? (
                    <span className="flex items-center gap-1 text-sm font-medium text-primary"><Check className="h-4 w-4" /> In use</span>
                  ) : (
                    <Button size="sm" variant="outline"
                      disabled={(online && !p.configured) || activate.isPending}
                      onClick={() => activate.mutate(p.key)}>
                      {online && !p.configured ? "Add key first" : "Use this"}
                    </Button>
                  )}
                </div>

                {online && (
                  <div className="mt-4 grid gap-3 border-t pt-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">Model</label>
                      <Input value={draft.model}
                        placeholder={p.default_model}
                        onChange={(e) => setDrafts((s) => ({ ...s, [p.key]: { ...draft, model: e.target.value } }))} />
                    </div>
                    <div className="space-y-1.5">
                      <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground"><KeyRound className="h-3 w-3" /> API Key {p.configured && <span className="text-emerald-600">(已配置)</span>}</label>
                      <Input type="password" value={draft.api_key}
                        placeholder={p.configured ? "•••••• (leave blank to keep)" : "Paste API key"}
                        onChange={(e) => setDrafts((s) => ({ ...s, [p.key]: { ...draft, api_key: e.target.value } }))} />
                    </div>
                    <div className="sm:col-span-2 flex justify-end">
                      <Button size="sm"
                        disabled={saveConfig.isPending}
                        onClick={() => saveConfig.mutate({ provider: p.key, model: draft.model, api_key: draft.api_key })}>
                        {saveConfig.isPending ? <><Loader2 className="mr-1.5 h-4 w-4 animate-spin" />Saving</> : "Save"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Tip: DeepSeek is recommended for Chinese filings — cheap, strong Chinese, 64K context, and parallel
        requests make large prospectuses analyze in minutes instead of being limited by local serial inference.
      </p>
    </div>
  );
}
