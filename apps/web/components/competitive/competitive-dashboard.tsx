"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Swords, Shield, TrendingUp, AlertTriangle, Lightbulb, Crosshair,
  Trophy, ThumbsDown, MessageSquare, Cpu, FileWarning,
} from "lucide-react";

import { ExternalLink } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Link } from "@/i18n/routing";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

interface Competitor {
  name: string; type: string; description: string;
  strengths: string[]; weaknesses: string[]; threat_level: number;
  company_id?: string | null;
}
interface CompetitiveResponse {
  has_data: boolean;
  market_position: string | null;
  positioning_score: number;
  swot: { strengths: string[]; weaknesses: string[]; opportunities: string[]; threats: string[] };
  competitors: Competitor[];
  battlecards: { competitor: string; why_we_win: string[]; why_we_lose: string[]; objection_handling: string[] }[];
  technology_trends: string[];
}

const TYPE_COLOR: Record<string, string> = {
  Direct: "bg-rose-50 text-rose-700 border-rose-200",
  Indirect: "bg-amber-50 text-amber-700 border-amber-200",
  Substitute: "bg-sky-50 text-sky-700 border-sky-200",
  Emerging: "bg-violet-50 text-violet-700 border-violet-200",
};

function ThreatDots({ level }: { level: number }) {
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`h-2 w-2 rounded-full ${i <= level ? "bg-rose-500" : "bg-muted"}`} />
      ))}
    </span>
  );
}

function SwotCard({ title, items, icon: Icon, color }: {
  title: string; items: string[]; icon: React.ElementType; color: string;
}) {
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="mb-3 flex items-center gap-2 font-semibold">
        <Icon className="h-4 w-4" /> {title}
      </div>
      <ul className="space-y-2">
        {(items?.length ? items : ["—"]).map((it, i) => (
          <li key={i} className="flex gap-2 text-sm leading-relaxed">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-current opacity-60" />
            <span className="opacity-90">{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CompetitiveDashboard({ companyId }: { companyId: string }) {
  const { data, isLoading } = useQuery<CompetitiveResponse>({
    queryKey: ["competitive", companyId],
    queryFn: () =>
      apiClient.get(`/companies/${companyId}/competitive`) as unknown as Promise<CompetitiveResponse>,
    refetchInterval: (query) => (query.state.data?.has_data ? false : 5000),
  });

  if (isLoading) {
    return <div className="p-12 text-center text-muted-foreground animate-pulse">Analyzing competitive landscape…</div>;
  }

  if (!data || !data.has_data) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <FileWarning className="h-10 w-10 text-muted-foreground/50 animate-pulse" />
          <p className="font-medium">Competitive intelligence is being generated…</p>
          <p className="max-w-md text-sm text-muted-foreground">
            The Competitive Intelligence Agent (Gartner + Bain style) is mapping competitors, SWOT and
            battlecards in the background. This page refreshes automatically when ready.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* 市场定位 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base"><Crosshair className="h-5 w-5 text-indigo-500" /> Market Position</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl text-sm leading-relaxed text-foreground/80">{data.market_position}</p>
          <div className="shrink-0 rounded-xl border bg-primary/5 px-5 py-3 text-center">
            <p className="text-xs font-medium text-muted-foreground">Moat / Positioning</p>
            <p className="text-3xl font-black text-primary">{data.positioning_score}</p>
          </div>
        </CardContent>
      </Card>

      {/* SWOT 四象限 */}
      <div className="grid gap-4 md:grid-cols-2">
        <SwotCard title="Strengths" items={data.swot.strengths} icon={Shield} color="border-emerald-200 bg-emerald-50/50 text-emerald-900" />
        <SwotCard title="Weaknesses" items={data.swot.weaknesses} icon={ThumbsDown} color="border-rose-200 bg-rose-50/50 text-rose-900" />
        <SwotCard title="Opportunities" items={data.swot.opportunities} icon={Lightbulb} color="border-sky-200 bg-sky-50/50 text-sky-900" />
        <SwotCard title="Threats" items={data.swot.threats} icon={AlertTriangle} color="border-amber-200 bg-amber-50/50 text-amber-900" />
      </div>

      {/* 竞争矩阵 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base"><Swords className="h-5 w-5 text-rose-500" /> Competitive Matrix</CardTitle>
          <CardDescription>Direct, indirect, substitute and emerging players</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Competitor</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Strengths</TableHead>
                <TableHead>Weaknesses</TableHead>
                <TableHead className="text-right">Threat</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.competitors.map((c, i) => (
                <TableRow key={i}>
                  <TableCell className="align-top">
                    {c.company_id ? (
                      <Link
                        href={`/company-intelligence/companies/${c.company_id}`}
                        className="group/link flex items-center gap-1 font-medium text-primary hover:underline"
                      >
                        {c.name}
                        <ExternalLink className="h-3 w-3 opacity-0 transition-opacity group-hover/link:opacity-100" />
                      </Link>
                    ) : (
                      <div className="font-medium">{c.name}</div>
                    )}
                    <div className="text-xs text-muted-foreground">{c.description}</div>
                  </TableCell>
                  <TableCell className="align-top">
                    <Badge variant="outline" className={TYPE_COLOR[c.type] || ""}>{c.type}</Badge>
                  </TableCell>
                  <TableCell className="align-top text-xs text-foreground/70">
                    {(c.strengths || []).join(", ") || "—"}
                  </TableCell>
                  <TableCell className="align-top text-xs text-foreground/70">
                    {(c.weaknesses || []).join(", ") || "—"}
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="flex justify-end"><ThreatDots level={c.threat_level} /></div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 战卡 */}
      {data.battlecards?.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.battlecards.map((b, i) => (
            <Card key={i}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Swords className="h-4 w-4 text-rose-500" /> Battlecard · vs {b.competitor}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <BattleRow icon={Trophy} tone="text-emerald-600" label="Why we win" items={b.why_we_win} />
                <BattleRow icon={ThumbsDown} tone="text-rose-600" label="Why we lose" items={b.why_we_lose} />
                <BattleRow icon={MessageSquare} tone="text-sky-600" label="Objection handling" items={b.objection_handling} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 技术趋势 */}
      {data.technology_trends?.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base"><Cpu className="h-5 w-5 text-violet-500" /> Technology & Industry Trends</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {data.technology_trends.map((t, i) => (
              <Badge key={i} variant="secondary" className="text-xs font-normal">{t}</Badge>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function BattleRow({ icon: Icon, tone, label, items }: {
  icon: React.ElementType; tone: string; label: string; items: string[];
}) {
  if (!items?.length) return null;
  return (
    <div>
      <div className={`mb-1.5 flex items-center gap-1.5 font-medium ${tone}`}>
        <Icon className="h-4 w-4" /> {label}
      </div>
      <ul className="space-y-1 pl-1">
        {items.map((it, i) => (
          <li key={i} className="flex gap-2 text-foreground/80">
            <span className={`mt-1.5 h-1 w-1 shrink-0 rounded-full ${tone.replace("text-", "bg-")}`} />
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}
