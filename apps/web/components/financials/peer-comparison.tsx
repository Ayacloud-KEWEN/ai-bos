"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from "recharts";
import { Users, Trophy } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { formatCompact, formatPct } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface PeerRow {
  company_id: string; name: string; is_target: boolean;
  revenue: number | null; revenue_growth: number | null; revenue_cagr: number | null;
  gross_margin: number | null; net_margin: number | null;
  financial_health: number | null; growth_score: number | null; profitability_score: number | null;
}
interface PeerResponse {
  industry: string; peer_count: number; has_peers: boolean;
  peers: PeerRow[];
  benchmarks: Record<string, { industry_avg: number | null; target_percentile: number | null }>;
}

const TARGET = "#4f46e5";
const PEER = "#94a3b8";

export function PeerComparison({ companyId }: { companyId: string }) {
  const { data, isLoading } = useQuery<PeerResponse>({
    queryKey: ["peers", companyId],
    queryFn: () =>
      apiClient.get(`/companies/${companyId}/peers`) as unknown as Promise<PeerResponse>,
  });

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Benchmarking against industry peers…</div>;
  }

  if (!data || !data.has_peers) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <Users className="h-9 w-9 text-muted-foreground/50" />
          <p className="font-medium">Not enough peers yet</p>
          <p className="max-w-md text-sm text-muted-foreground">
            Peer benchmarking compares this company against others in
            <span className="font-medium"> {data?.industry || "the same industry"}</span>.
            Upload at least one more company in the same industry to unlock the comparison.
          </p>
        </CardContent>
      </Card>
    );
  }

  const marginData = data.peers
    .filter((p) => p.net_margin != null || p.gross_margin != null)
    .map((p) => ({ name: p.name, net: p.net_margin, gross: p.gross_margin, isTarget: p.is_target }));

  const growthData = data.peers
    .filter((p) => p.revenue_growth != null)
    .map((p) => ({ name: p.name, growth: p.revenue_growth, isTarget: p.is_target }));

  const tip = { borderRadius: 8, fontSize: 12 } as const;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Benchmarking against <span className="font-medium text-foreground">{data.peer_count}</span> companies in
          <span className="font-medium text-foreground"> {data.industry}</span>.
        </p>
      </div>

      {/* 行业百分位摘要 */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { k: "net_margin", label: "Net Margin" },
          { k: "revenue_growth", label: "Revenue Growth" },
          { k: "financial_health", label: "Health Score" },
          { k: "profitability_score", label: "Profitability" },
        ].map(({ k, label }) => {
          const b = data.benchmarks[k];
          const pct = b?.target_percentile;
          return (
            <div key={k} className="rounded-xl border bg-card p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">{label}</p>
                {pct != null && <Trophy className="h-4 w-4 text-amber-500" />}
              </div>
              <p className="mt-2 text-2xl font-bold">
                {pct != null ? `${pct}th` : "—"}
                {pct != null && <span className="ml-1 text-sm font-normal text-muted-foreground">pctile</span>}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Industry avg: {k.includes("margin") || k.includes("growth") ? formatPct(b?.industry_avg) : (b?.industry_avg ?? "—")}
              </p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 利润率对比 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Margins vs Peers</CardTitle>
            <CardDescription>Net & gross margin (%)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={marginData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={50} />
                  <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={42} />
                  <Tooltip contentStyle={tip} formatter={(v: any) => `${v}%`} />
                  <Bar dataKey="net" name="Net Margin" radius={[4, 4, 0, 0]}>
                    {marginData.map((d, i) => <Cell key={i} fill={d.isTarget ? TARGET : PEER} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* 增长对比 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Revenue Growth vs Peers</CardTitle>
            <CardDescription>Latest YoY revenue growth (%)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={growthData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={50} />
                  <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={42} />
                  <Tooltip contentStyle={tip} formatter={(v: any) => `${v}%`} />
                  <Bar dataKey="growth" name="Revenue Growth" radius={[4, 4, 0, 0]}>
                    {growthData.map((d, i) => <Cell key={i} fill={d.isTarget ? TARGET : PEER} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 对标明细表 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Peer Benchmark Table</CardTitle>
          <CardDescription>Highlighted row is the current company</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead className="text-right">Revenue</TableHead>
                <TableHead className="text-right">Growth</TableHead>
                <TableHead className="text-right">Gross %</TableHead>
                <TableHead className="text-right">Net %</TableHead>
                <TableHead className="text-right">Health</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.peers.map((p) => (
                <TableRow key={p.company_id} className={p.is_target ? "bg-primary/5 font-medium" : ""}>
                  <TableCell>
                    {p.name}
                    {p.is_target && <Badge variant="outline" className="ml-2 text-[10px]">This company</Badge>}
                  </TableCell>
                  <TableCell className="text-right">{formatCompact(p.revenue)}</TableCell>
                  <TableCell className="text-right">{formatPct(p.revenue_growth, true)}</TableCell>
                  <TableCell className="text-right">{formatPct(p.gross_margin)}</TableCell>
                  <TableCell className="text-right">{formatPct(p.net_margin)}</TableCell>
                  <TableCell className="text-right">{p.financial_health ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
