"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, LineChart, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell, BarChart,
} from "recharts";
import {
  TrendingUp, TrendingDown, Activity, ShieldAlert, Sparkles,
  Wallet, PieChart as PieIcon, AlertTriangle, Target, Lightbulb, FileWarning, Pencil,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { formatCompact, formatPct, growthColor, currencySymbol } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FinancialDataEditor } from "@/components/financials/financial-data-editor";

const SCORE_META: Record<string, { label: string; invert?: boolean }> = {
  financial_health: { label: "Financial Health" },
  growth: { label: "Growth" },
  profitability: { label: "Profitability" },
  liquidity: { label: "Liquidity" },
  risk: { label: "Risk", invert: true },
};

const PIE_COLORS = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

function scoreColor(score: number, invert = false): string {
  const s = invert ? 100 - score : score;
  if (s >= 75) return "#10b981";
  if (s >= 50) return "#f59e0b";
  return "#ef4444";
}

function ScoreGauge({ id, value }: { id: string; value: number }) {
  const meta = SCORE_META[id];
  const color = scoreColor(value, meta?.invert);
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border bg-card p-4">
      <div className="relative h-20 w-20">
        <svg viewBox="0 0 36 36" className="h-20 w-20 -rotate-90">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" strokeWidth="3" className="text-muted/30" />
          <circle
            cx="18" cy="18" r="15.9" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round"
            strokeDasharray={`${value}, 100`}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xl font-bold">{value}</span>
      </div>
      <span className="text-center text-xs font-medium text-muted-foreground">{meta?.label || id}</span>
    </div>
  );
}

function KpiCard({ label, value, sub, subColor, icon: Icon }: {
  label: string; value: string; sub?: string; subColor?: string; icon: React.ElementType;
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{label}</p>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight">{value}</p>
      {sub && <p className={`mt-1 text-xs font-medium ${subColor || "text-muted-foreground"}`}>{sub}</p>}
    </div>
  );
}

function InsightList({ title, items, icon: Icon, tone }: {
  title: string; items: string[]; icon: React.ElementType; tone: string;
}) {
  if (!items?.length) return null;
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className={`h-5 w-5 ${tone}`} /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2.5">
          {items.map((it, i) => (
            <li key={i} className="flex gap-2.5 text-sm leading-relaxed">
              <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${tone.replace("text-", "bg-")}`} />
              <span className="text-foreground/80">{it}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

interface FinancialResponse {
  has_data: boolean;
  currency: string;
  fiscal_year: string | null;
  scores: Record<string, number> | null;
  executive_summary: string | null;
  key_findings: string[];
  growth_drivers: string[];
  risks: string[];
  opportunities: string[];
  segment_revenue: any[];
  geographic_revenue: any[];
  trend: { periods: any[]; summary: Record<string, any> };
}

export function FinancialDashboard({ companyId }: { companyId: string }) {
  const [editing, setEditing] = useState(false);
  const { data, isLoading } = useQuery<FinancialResponse>({
    queryKey: ["financials", companyId],
    queryFn: () =>
      apiClient.get(`/companies/${companyId}/financials`) as unknown as Promise<FinancialResponse>,
    // 财报由后台任务异步生成：未就绪时每 5s 轮询一次，直到拿到数据
    refetchInterval: (query) => (query.state.data?.has_data ? false : 5000),
  });

  if (isLoading) {
    return <div className="p-12 text-center text-muted-foreground animate-pulse">Running CFA-level financial analysis…</div>;
  }

  if (!data || !data.has_data) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <FileWarning className="h-10 w-10 text-muted-foreground/50 animate-pulse" />
          <p className="font-medium">Financial intelligence is being generated…</p>
          <p className="max-w-md text-sm text-muted-foreground">
            The CFA-level Financial Intelligence Agent is extracting revenue, margins, cash flow and
            balance-sheet metrics in the background. This page refreshes automatically when ready
            (usually under a minute). If it stays empty, the document may not contain financial statements.
          </p>
        </CardContent>
      </Card>
    );
  }

  const cur = data.currency as string;
  const sym = currencySymbol(cur);
  const periods: any[] = data.trend?.periods || [];
  const summary = data.trend?.summary || {};
  const scores = data.scores || {};

  const chartData = periods.map((p) => ({
    period: p.period,
    revenue: p.revenue,
    netProfit: p.net_profit,
    operatingProfit: p.operating_profit,
    grossMargin: p.gross_margin,
    operatingMargin: p.operating_margin,
    netMargin: p.net_margin,
    ocf: p.operating_cash_flow,
    fcf: p.free_cash_flow,
  }));

  const fmtAxis = (v: number) => formatCompact(v, cur);
  const tooltipStyle = { borderRadius: 8, border: "1px solid hsl(var(--border))", fontSize: 12 } as const;

  if (editing) {
    return (
      <FinancialDataEditor
        companyId={companyId}
        periods={periods}
        currency={cur}
        onClose={() => setEditing(false)}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 顶部操作栏：人工校正入口 */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{summary.periods_count} reporting period(s) · {sym}{cur}</p>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setEditing(true)}>
          <Pencil className="h-4 w-4" /> Edit data
        </Button>
      </div>

      {/* AI 评分仪表盘 */}
      {scores && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {Object.entries(SCORE_META).map(([id]) => (
            <ScoreGauge key={id} id={id} value={(scores as any)[id] ?? 0} />
          ))}
        </div>
      )}

      {/* 关键 KPI */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Latest Revenue" icon={Activity}
          value={formatCompact(summary.latest_revenue, cur)}
          sub={summary.yoy_revenue_growth != null ? `${formatPct(summary.yoy_revenue_growth, true)} YoY` : undefined}
          subColor={growthColor(summary.yoy_revenue_growth)} />
        <KpiCard label="Revenue CAGR" icon={summary.revenue_cagr >= 0 ? TrendingUp : TrendingDown}
          value={formatPct(summary.revenue_cagr)}
          sub={`over ${summary.periods_count} periods`} />
        <KpiCard label="Net Margin" icon={Sparkles}
          value={formatPct(summary.latest_net_margin)} sub="latest period" />
        <KpiCard label="Gross Margin" icon={PieIcon}
          value={formatPct(summary.latest_gross_margin)} sub="latest period" />
      </div>

      {/* 营收与利润趋势 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="h-5 w-5 text-indigo-500" /> Revenue & Profit Trend</CardTitle>
          <CardDescription>Revenue (bars) vs operating & net profit (lines), in {sym}{cur}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={fmtAxis} tick={{ fontSize: 11 }} width={60} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => formatCompact(v, cur)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="revenue" name="Revenue" fill="#4f46e5" radius={[4, 4, 0, 0]} barSize={36} />
                <Line dataKey="operatingProfit" name="Operating Profit" stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3 }} />
                <Line dataKey="netProfit" name="Net Profit" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 利润率趋势 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><Activity className="h-5 w-5 text-emerald-500" /> Margin Trends</CardTitle>
            <CardDescription>Profitability quality over time (%)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
                  <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={42} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => `${v}%`} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line dataKey="grossMargin" name="Gross" stroke="#4f46e5" strokeWidth={2} dot={{ r: 3 }} />
                  <Line dataKey="operatingMargin" name="Operating" stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3 }} />
                  <Line dataKey="netMargin" name="Net" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* 现金流 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><Wallet className="h-5 w-5 text-amber-500" /> Cash Flow</CardTitle>
            <CardDescription>Operating vs free cash flow, in {sym}{cur}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
                  <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={fmtAxis} tick={{ fontSize: 11 }} width={60} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => formatCompact(v, cur)} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="ocf" name="Operating CF" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="fcf" name="Free CF" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 营收结构（分部 / 地区） */}
      {(data.segment_revenue?.length > 0 || data.geographic_revenue?.length > 0) && (
        <div className="grid gap-6 lg:grid-cols-2">
          {data.segment_revenue?.length > 0 && (
            <RevenueBreakdown title="Revenue by Segment" items={data.segment_revenue} cur={cur} />
          )}
          {data.geographic_revenue?.length > 0 && (
            <RevenueBreakdown title="Revenue by Geography" items={data.geographic_revenue} cur={cur} nameKey="region" />
          )}
        </div>
      )}

      {/* AI 执行摘要 */}
      {data.executive_summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-5 w-5 text-indigo-500" /> CFO Executive Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="rounded-xl border bg-muted/30 p-5 text-sm leading-relaxed text-foreground/80">{data.executive_summary}</p>
          </CardContent>
        </Card>
      )}

      {/* 洞察四象限 */}
      <div className="grid gap-6 lg:grid-cols-2">
        <InsightList title="Key Findings" items={data.key_findings} icon={Target} tone="text-indigo-500" />
        <InsightList title="Growth Drivers" items={data.growth_drivers} icon={TrendingUp} tone="text-emerald-500" />
        <InsightList title="Risks & Red Flags" items={data.risks} icon={AlertTriangle} tone="text-rose-500" />
        <InsightList title="Opportunities" items={data.opportunities} icon={Lightbulb} tone="text-amber-500" />
      </div>
    </div>
  );
}

function RevenueBreakdown({ title, items, cur, nameKey = "name" }: {
  title: string; items: any[]; cur: string; nameKey?: string;
}) {
  const pieData = items.map((it) => ({ name: it[nameKey] ?? it.name ?? it.region, value: it.value }));
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><PieIcon className="h-5 w-5 text-violet-500" /> {title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} innerRadius={45} paddingAngle={2}>
                {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: any) => formatCompact(v, cur)} contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
