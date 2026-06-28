"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { GraduationCap, Play, Loader2, Rocket, Banknote, Globe, Package, Shield, History } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const ICON: Record<string, React.ElementType> = { startup: Rocket, fundraising: Banknote, market_entry: Globe, product_launch: Package, crisis: Shield };

export default function AcademyPage() {
  const router = useRouter();
  const { data: scen } = useQuery<{ scenarios: any[] }>({
    queryKey: ["scenarios"], queryFn: () => apiClient.get("/academy/scenarios") as unknown as Promise<any>,
  });
  const { data: sims = [], refetch } = useQuery<any[]>({
    queryKey: ["simulations"], queryFn: () => apiClient.get("/academy/simulations") as unknown as Promise<any[]>,
  });

  const start = useMutation({
    mutationFn: (key: string) => apiClient.post("/academy/simulations", { scenario_key: key }) as unknown as Promise<{ id: string }>,
    onSuccess: (r) => router.push(`/academy/simulations/${r.id}`),
  });

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2"><GraduationCap className="h-7 w-7 text-primary" /> Business Academy</h1>
        <p className="text-muted-foreground mt-1">Interactive AI business simulations — make decisions, see consequences, get coached & scored.</p>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Simulations</h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {(scen?.scenarios || []).map((s) => {
            const Icon = ICON[s.key] || Rocket;
            return (
              <Card key={s.key} className="flex flex-col">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-lg"><Icon className="h-5 w-5 text-primary" /> {s.title}</CardTitle>
                  <CardDescription>{s.scenario}</CardDescription>
                </CardHeader>
                <CardContent className="mt-auto flex items-center justify-between">
                  <Badge variant="secondary">{s.track}</Badge>
                  <Button size="sm" className="gap-1.5" disabled={start.isPending} onClick={() => start.mutate(s.key)}>
                    {start.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Start
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {sims.length > 0 && (
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground"><History className="h-4 w-4" /> My Simulations</h2>
          <div className="space-y-2">
            {sims.map((s) => (
              <div key={s.id} className="flex cursor-pointer items-center justify-between rounded-lg border p-3 hover:bg-muted/30" onClick={() => router.push(`/academy/simulations/${s.id}`)}>
                <div><p className="text-sm font-medium">{s.title}</p><p className="text-xs text-muted-foreground">{s.track} · round {s.round}</p></div>
                <Badge variant={s.status === "completed" ? "secondary" : "outline"}>{s.status}</Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
