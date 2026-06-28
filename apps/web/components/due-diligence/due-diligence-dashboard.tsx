"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ShieldCheck, Scale, Settings, Store, Cpu, AlertOctagon, Lightbulb,
  Gavel, FileWarning, CheckCircle2,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface RiskCategory { key: string; label: string; score: number; summary: string; findings: string[]; }
interface DueDiligenceResponse {
  has_data: boolean;
  overall_score: number;
  recommendation: string | null;
  executive_summary: string | null;
  language: string;
  risk_categories: RiskCategory[];
  red_flags: string[];
  opportunities: string[];
}

const CAT_ICON: Record<string, React.ElementType> = {
  financial: Scale, legal: Gavel, operational: Settings, commercial: Store, technology: Cpu,
};

// 风险分越高越红（higher score = more risk）
function riskColor(score: number): string {
  if (score >= 67) return "#ef4444";
  if (score >= 34) return "#f59e0b";
  return "#10b981";
}
function riskLabel(score: number): string {
  if (score >= 67) return "High";
  if (score >= 34) return "Medium";
  return "Low";
}

export function DueDiligenceDashboard({ companyId }: { companyId: string }) {
  const { data, isLoading } = useQuery<DueDiligenceResponse>({
    queryKey: ["due-diligence", companyId],
    queryFn: () =>
      apiClient.get(`/companies/${companyId}/due-diligence`) as unknown as Promise<DueDiligenceResponse>,
    refetchInterval: (q) => (q.state.data?.has_data ? false : 5000),
  });

  if (isLoading) {
    return <div className="p-12 text-center text-muted-foreground animate-pulse">Running due-diligence risk assessment…</div>;
  }

  if (!data || !data.has_data) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <FileWarning className="h-10 w-10 text-muted-foreground/50 animate-pulse" />
          <p className="font-medium">Due-diligence analysis is being generated…</p>
          <p className="max-w-md text-sm text-muted-foreground">
            The Due Diligence Agent assesses financial, legal, operational, commercial and technology
            risk. Output follows the source document’s language (中文文档将输出中文). Refreshes automatically when ready.
          </p>
        </CardContent>
      </Card>
    );
  }

  const recColor =
    data.overall_score >= 67 ? "border-emerald-200 bg-emerald-50/60 text-emerald-900"
    : data.overall_score >= 40 ? "border-amber-200 bg-amber-50/60 text-amber-900"
    : "border-rose-200 bg-rose-50/60 text-rose-900";

  return (
    <div className="space-y-6">
      {/* 综合评分 + 建议 */}
      <Card>
        <CardContent className="flex flex-col gap-5 py-6 sm:flex-row sm:items-center">
          <div className="flex shrink-0 flex-col items-center">
            <div className="relative h-28 w-28">
              <svg viewBox="0 0 36 36" className="h-28 w-28 -rotate-90">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" strokeWidth="3" className="text-muted/30" />
                <circle cx="18" cy="18" r="15.9" fill="none" strokeWidth="3" strokeLinecap="round"
                  stroke={data.overall_score >= 67 ? "#10b981" : data.overall_score >= 40 ? "#f59e0b" : "#ef4444"}
                  strokeDasharray={`${data.overall_score}, 100`} />
              </svg>
              <span className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-black">{data.overall_score}</span>
                <span className="text-[10px] text-muted-foreground">/ 100</span>
              </span>
            </div>
            <span className="mt-2 text-xs font-medium text-muted-foreground">Attractiveness</span>
          </div>
          <div className={`flex-1 rounded-xl border p-4 ${recColor}`}>
            <div className="mb-1.5 flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4" /> Recommendation
            </div>
            <p className="text-sm leading-relaxed">{data.recommendation}</p>
          </div>
        </CardContent>
      </Card>

      {/* 执行摘要 */}
      {data.executive_summary && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Due-Diligence Summary</CardTitle></CardHeader>
          <CardContent>
            <p className="rounded-xl border bg-muted/30 p-5 text-sm leading-relaxed text-foreground/80">{data.executive_summary}</p>
          </CardContent>
        </Card>
      )}

      {/* 五大风险维度 */}
      <div className="grid gap-4 md:grid-cols-2">
        {data.risk_categories.map((cat, i) => {
          const Icon = CAT_ICON[cat.key] || Scale;
          const color = riskColor(cat.score);
          return (
            <Card key={i}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Icon className="h-4 w-4 text-muted-foreground" /> {cat.label || cat.key}
                  </CardTitle>
                  <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ color, backgroundColor: `${color}1a` }}>
                    {riskLabel(cat.score)} · {cat.score}
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full" style={{ width: `${cat.score}%`, backgroundColor: color }} />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-foreground/80">{cat.summary}</p>
                {cat.findings?.length > 0 && (
                  <ul className="mt-3 space-y-1.5">
                    {cat.findings.map((f, j) => (
                      <li key={j} className="flex gap-2 text-xs text-muted-foreground">
                        <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" />{f}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* 红旗 & 机会 */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base"><AlertOctagon className="h-5 w-5 text-rose-500" /> Red Flags</CardTitle>
          </CardHeader>
          <CardContent>
            {data.red_flags?.length ? (
              <ul className="space-y-2.5">
                {data.red_flags.map((f, i) => (
                  <li key={i} className="flex gap-2.5 text-sm"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-500" /><span className="text-foreground/80">{f}</span></li>
                ))}
              </ul>
            ) : (
              <p className="flex items-center gap-2 text-sm text-emerald-600"><CheckCircle2 className="h-4 w-4" /> No critical red flags identified.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base"><Lightbulb className="h-5 w-5 text-amber-500" /> Opportunities</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2.5">
              {(data.opportunities || []).map((f, i) => (
                <li key={i} className="flex gap-2.5 text-sm"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" /><span className="text-foreground/80">{f}</span></li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
