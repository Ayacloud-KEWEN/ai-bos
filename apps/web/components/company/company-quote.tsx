"use client";

import { useQuery } from "@tanstack/react-query";
import { TrendingUp, TrendingDown, ExternalLink, LineChart, FileSearch } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface QuoteResp {
  available: boolean; symbol?: string; display?: string; market?: string;
  detail_url?: string; filings_url?: string; filings_label?: string;
  quote?: { price: number; currency: string; change: number; change_pct: number; exchange: string; market_state: string; market_time: number } | null;
}

export function CompanyQuote({ companyId }: { companyId: string }) {
  const { data } = useQuery<QuoteResp>({
    queryKey: ["quote", companyId],
    queryFn: () => apiClient.get(`/companies/${companyId}/quote`) as unknown as Promise<QuoteResp>,
    refetchInterval: 60000,
    staleTime: 30000,
  });

  if (!data || !data.available) return null;
  const q = data.quote;
  const up = (q?.change ?? 0) >= 0;
  const Arrow = up ? TrendingUp : TrendingDown;
  const tone = up ? "text-emerald-600" : "text-rose-600";

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10"><LineChart className="h-5 w-5 text-primary" /></div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">{data.display}</span>
              <Badge variant="secondary" className="text-[10px]">{q?.exchange || data.market}</Badge>
              {q?.market_state && q.market_state !== "REGULAR" && <Badge variant="outline" className="text-[10px]">{q.market_state}</Badge>}
            </div>
            {q && q.price != null ? (
              <div className="mt-0.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold">{q.price.toLocaleString()}</span>
                <span className="text-xs text-muted-foreground">{q.currency}</span>
                <span className={`flex items-center gap-0.5 text-sm font-medium ${tone}`}>
                  <Arrow className="h-3.5 w-3.5" />{up ? "+" : ""}{q.change} ({up ? "+" : ""}{q.change_pct}%)
                </span>
              </div>
            ) : <p className="mt-0.5 text-sm text-muted-foreground">Quote unavailable</p>}
            {q?.market_time && <p className="text-[11px] text-muted-foreground">as of {new Date(q.market_time * 1000).toLocaleString()}</p>}
          </div>
        </div>
        <div className="flex gap-2">
          {data.detail_url && <a href={data.detail_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted/40"><ExternalLink className="h-3.5 w-3.5" /> Quote</a>}
          {data.filings_url && <a href={data.filings_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted/40"><FileSearch className="h-3.5 w-3.5" /> {data.filings_label || "Filings"}</a>}
        </div>
      </CardContent>
    </Card>
  );
}
