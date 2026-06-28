"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, GitCompare, Check } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCompact, formatPct } from "@/lib/format";

const COLORS = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b"];

export default function ComparePage() {
  const router = useRouter();
  const [selected, setSelected] = useState<string[]>([]);

  const { data: companies = [] } = useQuery<any[]>({
    queryKey: ["companies"], queryFn: () => apiClient.get("/companies/") as unknown as Promise<any[]>,
  });
  const real = companies.filter((c) => !(c.status || "").startsWith("Discovered"));

  const { data, isFetching } = useQuery<{ companies: any[] }>({
    queryKey: ["compare", selected],
    queryFn: () => apiClient.get(`/compare?ids=${selected.join(",")}`) as unknown as Promise<any>,
    enabled: selected.length >= 2,
  });

  const toggle = (id: string) =>
    setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : s.length < 4 ? [...s, id] : s);

  const cos = data?.companies || [];

  // 数值行：value 取法 + 是否越大越好
  const rows: { label: string; get: (c: any) => number | null; fmt: (v: any, c: any) => string; higher: boolean }[] = [
    { label: "Intelligence Score", get: (c) => c.intelligence_score, fmt: (v) => v ?? "—", higher: true },
    { label: "Latest Revenue", get: (c) => c.latest_revenue, fmt: (v, c) => formatCompact(v, c.currency), higher: true },
    { label: "Revenue YoY", get: (c) => c.yoy_revenue_growth, fmt: (v) => formatPct(v, true), higher: true },
    { label: "Net Margin", get: (c) => c.net_margin, fmt: (v) => formatPct(v), higher: true },
    { label: "Gross Margin", get: (c) => c.gross_margin, fmt: (v) => formatPct(v), higher: true },
    { label: "Financial Health", get: (c) => c.financial_scores?.financial_health, fmt: (v) => v ?? "—", higher: true },
    { label: "Profitability", get: (c) => c.financial_scores?.profitability, fmt: (v) => v ?? "—", higher: true },
    { label: "Risk (lower better)", get: (c) => c.financial_scores?.risk, fmt: (v) => v ?? "—", higher: false },
    { label: "DD Attractiveness", get: (c) => c.dd_score, fmt: (v) => v ?? "—", higher: true },
    { label: "Moat / Positioning", get: (c) => c.positioning_score, fmt: (v) => v ?? "—", higher: true },
  ];

  const bestIdx = (r: typeof rows[0]) => {
    const vals = cos.map((c) => r.get(c));
    const nums = vals.map((v, i) => ({ v, i })).filter((x) => typeof x.v === "number");
    if (!nums.length) return -1;
    return nums.reduce((a, b) => (r.higher ? (b.v! > a.v! ? b : a) : (b.v! < a.v! ? b : a))).i;
  };

  const chartData = [
    { metric: "Intelligence", key: "intelligence_score" },
    { metric: "Fin. Health", key: "fh" },
    { metric: "DD Score", key: "dd_score" },
    { metric: "Positioning", key: "positioning_score" },
  ].map((m) => {
    const row: any = { metric: m.metric };
    cos.forEach((c) => {
      row[c.name] = m.key === "fh" ? (c.financial_scores?.financial_health || 0)
        : m.key === "intelligence_score" ? (c.intelligence_score || 0)
        : (c[m.key] || 0);
    });
    return row;
  });

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.push("/company-intelligence/companies")}><ArrowLeft className="h-5 w-5" /></Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2"><GitCompare className="h-7 w-7 text-primary" /> Compare Companies</h1>
          <p className="text-muted-foreground mt-1">Select 2–4 companies for a side-by-side intelligence / M&A view.</p>
        </div>
      </div>

      {/* 选择器 */}
      <div className="flex flex-wrap gap-2">
        {real.map((c) => {
          const on = selected.includes(c.id);
          return (
            <button key={c.id} onClick={() => toggle(c.id)}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm ${on ? "border-primary bg-primary/10 text-primary" : "hover:bg-muted/50"}`}>
              {on && <Check className="h-3.5 w-3.5" />}{c.name}
            </button>
          );
        })}
      </div>

      {selected.length < 2 ? (
        <div className="py-16 text-center text-muted-foreground border-2 border-dashed rounded-lg">Select at least 2 companies above.</div>
      ) : isFetching ? (
        <div className="text-muted-foreground animate-pulse">Comparing…</div>
      ) : (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">Score Comparison</CardTitle></CardHeader>
            <CardContent>
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis dataKey="metric" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} width={32} />
                    <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {cos.map((c, i) => <Bar key={c.id} dataKey={c.name} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />)}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Metrics</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="p-2 text-left font-medium text-muted-foreground">Metric</th>
                    {cos.map((c, i) => <th key={c.id} className="p-2 text-left"><span style={{ color: COLORS[i % COLORS.length] }}>●</span> {c.name}<div className="text-xs font-normal text-muted-foreground">{c.sector}</div></th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const best = bestIdx(r);
                    return (
                      <tr key={r.label} className="border-b">
                        <td className="p-2 text-muted-foreground">{r.label}</td>
                        {cos.map((c, i) => (
                          <td key={c.id} className={`p-2 ${i === best ? "font-bold text-primary" : ""}`}>{r.fmt(r.get(c), c)}</td>
                        ))}
                      </tr>
                    );
                  })}
                  <tr className="border-b align-top">
                    <td className="p-2 text-muted-foreground">DD Recommendation</td>
                    {cos.map((c) => <td key={c.id} className="p-2 text-xs">{c.dd_recommendation || "—"}</td>)}
                  </tr>
                  <tr className="align-top">
                    <td className="p-2 text-muted-foreground">Key Strengths</td>
                    {cos.map((c) => <td key={c.id} className="p-2 text-xs">{(c.strengths || []).map((s: string, j: number) => <div key={j}>• {s}</div>)}</td>)}
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
