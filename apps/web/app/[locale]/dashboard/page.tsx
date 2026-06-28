"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2, FileText, Activity, Bell, Radar as RadarIcon, Gauge, RefreshCw, Loader2,
  TrendingUp, AlertTriangle, FileWarning, ChevronRight,
} from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Cell, Tooltip } from "recharts";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const BAR = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#64748b"];
const sevColor: Record<string, string> = { critical: "text-rose-600", warning: "text-amber-600", info: "text-sky-600" };

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<any>({
    queryKey: ["dashboard"],
    queryFn: () => apiClient.get("/dashboard/summary") as unknown as Promise<any>,
  });

  const monitor = useMutation({
    mutationFn: () => apiClient.post("/monitoring/run", {}) as unknown as Promise<{ checked: number; new_alerts: number }>,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
  });

  if (isLoading || !data) return <div className="p-8 text-muted-foreground animate-pulse">Loading dashboard…</div>;

  const t = data.totals;
  const stats = [
    { label: "Companies", value: t.companies, icon: Building2 },
    { label: "Documents", value: t.documents, icon: FileText },
    { label: "Financial Reports", value: t.financial_reports, icon: TrendingUp },
    { label: "Monitored", value: t.monitored, icon: RadarIcon },
    { label: "Avg Score", value: t.avg_intelligence_score, icon: Gauge },
    { label: "Unread Alerts", value: t.unread_alerts, icon: Bell },
  ];

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Portfolio intelligence overview & continuous monitoring.</p>
        </div>
        <Button onClick={() => monitor.mutate()} disabled={monitor.isPending} className="gap-2">
          {monitor.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Checking…</> : <><RefreshCw className="h-4 w-4" /> Run monitoring</>}
        </Button>
      </div>

      {monitor.isSuccess && monitor.data && (
        <div className="rounded-lg border bg-muted/30 px-4 py-2 text-sm text-muted-foreground">
          Monitoring complete · checked {monitor.data.checked} companies · {monitor.data.new_alerts} new alert(s).
        </div>
      )}

      {/* 统计卡 */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="flex flex-col gap-1 py-4">
              <div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">{s.label}</span><s.icon className="h-4 w-4 text-muted-foreground" /></div>
              <span className="text-2xl font-bold">{s.value}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 行业分布 */}
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="text-base">Companies by Sector</CardTitle></CardHeader>
          <CardContent>
            {data.sector_distribution?.length ? (
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.sector_distribution} layout="vertical" margin={{ left: 20, right: 20 }}>
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="sector" width={140} tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {data.sector_distribution.map((_: any, i: number) => <Cell key={i} fill={BAR[i % BAR.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <p className="py-12 text-center text-sm text-muted-foreground">No companies yet.</p>}
          </CardContent>
        </Card>

        {/* 告警 */}
        <Card>
          <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Bell className="h-5 w-5 text-amber-500" /> Recent Alerts</CardTitle>
            <CardDescription>{t.unread_alerts} unread</CardDescription></CardHeader>
          <CardContent className="space-y-2">
            {data.recent_alerts?.length ? data.recent_alerts.map((a: any) => (
              <div key={a.id} className="flex cursor-pointer gap-2 rounded-lg border p-2.5 hover:bg-muted/30"
                onClick={() => a.company_id && router.push(`/company-intelligence/companies/${a.company_id}`)}>
                <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${sevColor[a.severity] || "text-muted-foreground"}`} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{a.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{a.company_name}</p>
                </div>
              </div>
            )) : <p className="flex items-center gap-2 py-6 text-sm text-muted-foreground"><FileWarning className="h-4 w-4" /> No alerts. Run monitoring to check for changes.</p>}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 情报评分榜 */}
        <Card>
          <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Activity className="h-5 w-5 text-indigo-500" /> Top by Intelligence Score</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {data.top_companies?.map((c: any, i: number) => (
              <div key={c.id} className="flex cursor-pointer items-center justify-between rounded-lg px-2 py-2 hover:bg-muted/40"
                onClick={() => router.push(`/company-intelligence/companies/${c.id}`)}>
                <div className="flex items-center gap-3"><span className="text-sm font-bold text-muted-foreground">{i + 1}</span>
                  <div><p className="text-sm font-medium">{c.name}</p><p className="text-xs text-muted-foreground">{c.sector || c.industry}</p></div></div>
                <Badge variant="secondary">{c.intelligence_score}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 近期公司 */}
        <Card>
          <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Building2 className="h-5 w-5 text-emerald-500" /> Recent Companies</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {data.recent_companies?.map((c: any) => (
              <div key={c.id} className="flex cursor-pointer items-center justify-between rounded-lg px-2 py-2 hover:bg-muted/40"
                onClick={() => router.push(`/company-intelligence/companies/${c.id}`)}>
                <div><p className="text-sm font-medium">{c.name}</p><p className="text-xs text-muted-foreground">{c.status}</p></div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
