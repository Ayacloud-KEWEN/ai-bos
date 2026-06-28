"use client";

import {
  TrendingUp, ShieldCheck, Swords, AlertTriangle, Lightbulb, Sparkles, Crosshair,
} from "lucide-react";

import { Link } from "@/i18n/routing";
import { formatCompact, formatPct, currencySymbol } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Highlights {
  financial?: {
    health: number | null; growth: number | null; profitability: number | null;
    currency: string; latest_revenue: number | null; net_margin: number | null; yoy_growth: number | null;
  } | null;
  due_diligence?: { overall_score: number; recommendation: string } | null;
  competitive?: {
    positioning_score: number; market_position: string; strengths: string[];
    competitors: { name: string; company_id: string | null; threat_level: number }[];
  } | null;
  key_risks: string[];
  opportunities: string[];
}

function ScoreChip({ label, value }: { label: string; value: number | null | undefined }) {
  if (value == null) return null;
  const color = value >= 70 ? "text-emerald-600" : value >= 45 ? "text-amber-600" : "text-rose-600";
  return (
    <div className="rounded-lg border bg-card px-3 py-2 text-center">
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}

export function OverviewHighlights({ highlights }: { highlights?: Highlights }) {
  if (!highlights) return null;
  const { financial: f, due_diligence: dd, competitive: c } = highlights;
  const sym = f ? currencySymbol(f.currency) : "$";

  const hasAny = f || dd || c || highlights.key_risks?.length || highlights.opportunities?.length;
  if (!hasAny) return null;

  return (
    <div className="space-y-6">
      {/* 关键评分总览 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-5 w-5 text-indigo-500" /> Key Highlights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            <ScoreChip label="Fin. Health" value={f?.health} />
            <ScoreChip label="Growth" value={f?.growth} />
            <ScoreChip label="Profitability" value={f?.profitability} />
            <ScoreChip label="Moat" value={c?.positioning_score} />
            <ScoreChip label="DD Score" value={dd?.overall_score} />
          </div>

          {/* 财务 KPI */}
          {f && (f.latest_revenue != null || f.net_margin != null) && (
            <div className="flex flex-wrap gap-4 rounded-lg border bg-muted/20 p-3 text-sm">
              {f.latest_revenue != null && (
                <span className="flex items-center gap-1.5"><TrendingUp className="h-4 w-4 text-indigo-500" />
                  Latest Revenue: <b>{formatCompact(f.latest_revenue, f.currency)}</b>
                  {f.yoy_growth != null && <span className="text-muted-foreground">({formatPct(f.yoy_growth, true)} YoY)</span>}
                </span>
              )}
              {f.net_margin != null && <span>Net Margin: <b>{formatPct(f.net_margin)}</b></span>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 投资建议 */}
      {dd?.recommendation && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="h-5 w-5 text-emerald-500" /> Investment Recommendation</CardTitle></CardHeader>
          <CardContent><p className="text-sm leading-relaxed text-foreground/80">{dd.recommendation}</p></CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 竞争定位 + 竞品 */}
        {c && (
          <Card>
            <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><Crosshair className="h-5 w-5 text-indigo-500" /> Market Position</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {c.market_position && <p className="text-sm leading-relaxed text-foreground/80">{c.market_position}</p>}
              {c.competitors?.length > 0 && (
                <div>
                  <p className="mb-1.5 text-xs font-medium text-muted-foreground flex items-center gap-1"><Swords className="h-3.5 w-3.5" /> Top competitors</p>
                  <div className="flex flex-wrap gap-1.5">
                    {c.competitors.map((cp, i) => cp.company_id ? (
                      <Link key={i} href={`/company-intelligence/companies/${cp.company_id}`}>
                        <Badge variant="secondary" className="cursor-pointer hover:bg-primary/10">{cp.name}</Badge>
                      </Link>
                    ) : <Badge key={i} variant="secondary">{cp.name}</Badge>)}
                  </div>
                </div>
              )}
              {c.strengths?.length > 0 && (
                <ul className="space-y-1.5 pt-1">
                  {c.strengths.map((s, i) => (
                    <li key={i} className="flex gap-2 text-sm text-foreground/80"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" />{s}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )}

        {/* 风险 + 机会 */}
        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><AlertTriangle className="h-5 w-5 text-rose-500" /> Key Risks & Opportunities</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {highlights.key_risks?.length > 0 && (
              <ul className="space-y-1.5">
                {highlights.key_risks.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm text-foreground/80"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-rose-500" />{r}</li>
                ))}
              </ul>
            )}
            {highlights.opportunities?.length > 0 && (
              <ul className="space-y-1.5 border-t pt-3">
                {highlights.opportunities.map((o, i) => (
                  <li key={i} className="flex gap-2 text-sm text-foreground/80"><Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />{o}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
