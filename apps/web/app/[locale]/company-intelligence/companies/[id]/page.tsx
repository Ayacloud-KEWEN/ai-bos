"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building, MapPin, Activity, Target, Zap, TrendingUp, FileDown, Package, FileText as FileTextIcon, Presentation, Swords, Mail } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FinancialDashboard } from "@/components/financials/financial-dashboard";
import { PeerComparison } from "@/components/financials/peer-comparison";
import { CompetitiveDashboard } from "@/components/competitive/competitive-dashboard";
import { DueDiligenceDashboard } from "@/components/due-diligence/due-diligence-dashboard";
import { OverviewHighlights } from "@/components/company/overview-highlights";
import { CompanyBriefing } from "@/components/company/company-briefing";
import { StrategyDashboard } from "@/components/strategy/strategy-dashboard";
import { SalesDashboard } from "@/components/sales/sales-dashboard";
import { MarketDashboard } from "@/components/market/market-dashboard";
import { CompanyDocuments } from "@/components/company/company-documents";
import { CompanyChat } from "@/components/company/company-chat";
import { CompanyQuote } from "@/components/company/company-quote";
import { fileUrl } from "@/lib/file-url";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";

export default function CompanyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const companyId = params.id as string;

  const { data: company, isLoading } = useQuery<any>({
    queryKey: ["company", companyId],
    queryFn: () => apiClient.get(`/companies/${companyId}`) as unknown as Promise<any>,
  });

  if (isLoading) return <div className="p-8 text-muted-foreground animate-pulse">Loading AI Intelligence Data...</div>;
  if (!company) return <div className="p-8 text-destructive">Company not found.</div>;

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      {/* 顶部导航与基础信息 */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()} className="mt-1">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                <Building className="h-7 w-7 text-primary" />
                {company.name}
              </h1>
              <div className="flex items-center gap-4 mt-2 text-muted-foreground">
                <span className="flex items-center gap-1"><MapPin className="h-4 w-4" /> {company.location}</span>
                <span className="flex items-center gap-1"><Target className="h-4 w-4" /> {company.industry}</span>
                <Badge variant="secondary" className="ml-2 bg-indigo-50 text-indigo-700">{company.status}</Badge>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => window.open(fileUrl(`/companies/${companyId}/report`), "_blank")}
              >
                <FileDown className="h-4 w-4" /> Export Report
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="gap-2"><Package className="h-4 w-4" /> Assets</Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Generate deliverable</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => window.open(fileUrl(`/companies/${companyId}/assets/investor-memo.docx`), "_blank")}><FileTextIcon className="mr-2 h-4 w-4" /> Investor Memo (Word)</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => window.open(fileUrl(`/companies/${companyId}/assets/sales-deck.pptx`), "_blank")}><Presentation className="mr-2 h-4 w-4" /> Sales Deck (PPT)</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => window.open(fileUrl(`/companies/${companyId}/assets/battlecard.docx`), "_blank")}><Swords className="mr-2 h-4 w-4" /> Battlecard (Word)</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => window.open(fileUrl(`/companies/${companyId}/assets/outreach-email.txt`), "_blank")}><Mail className="mr-2 h-4 w-4" /> Outreach Email (Text)</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <div className="text-right bg-primary/5 p-4 rounded-xl border border-primary/10">
                <p className="text-sm font-medium text-muted-foreground mb-1">Global Intelligence Score</p>
                <p className="text-4xl font-black text-primary">{company.intelligence_score}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full mt-4">
        <TabsList className="flex flex-wrap h-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="financials">Financials</TabsTrigger>
          <TabsTrigger value="peers">Peer Comparison</TabsTrigger>
          <TabsTrigger value="competitors">Competitors</TabsTrigger>
          <TabsTrigger value="due-diligence">Due Diligence</TabsTrigger>
          <TabsTrigger value="strategy">Strategy</TabsTrigger>
          <TabsTrigger value="sales">Sales</TabsTrigger>
          <TabsTrigger value="market">Market</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6 space-y-6">
      {/* 上市公司股价 + 详情链接 */}
      <CompanyQuote companyId={companyId} />

      {/* CEO 执行简报 */}
      <CompanyBriefing companyId={companyId} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：多维数据雷达图 */}
        <Card className="col-span-1 lg:col-span-1 shadow-sm border-muted">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="h-5 w-5 text-amber-500" />
              Capability Radar
            </CardTitle>
            <CardDescription>768-dim vector mapped to 5 core business metrics.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="w-full h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={company.radar_data}>
                  <PolarGrid strokeOpacity={0.2} />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "currentColor", fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                  <Radar name="AI Assessment" dataKey="score" stroke="#4f46e5" fill="#4f46e5" fillOpacity={0.4} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* 右侧：AI 摘要与核心情报 */}
        <Card className="col-span-1 lg:col-span-2 shadow-sm border-muted">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-emerald-500" />
              Executive AI Summary
            </CardTitle>
            <CardDescription>Generated by Qwen2.5 Local Engine</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="bg-muted/30 p-6 rounded-xl border border-muted-foreground/10">
              <p className="text-base leading-relaxed text-foreground/80">
                {company.summary}
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-muted p-4 rounded-lg flex items-start gap-3">
                <TrendingUp className="h-8 w-8 text-blue-500 opacity-80" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Documents Analyzed</p>
                  <p className="text-2xl font-bold mt-1">{company.documents_analyzed}</p>
                </div>
              </div>
              <div className="border border-muted p-4 rounded-lg flex items-start gap-3">
                <Target className="h-8 w-8 text-purple-500 opacity-80" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Vector Dimensionality</p>
                  <p className="text-xl font-bold mt-1">768-dim Space</p>
                  <p className="text-xs text-muted-foreground mt-1">Ready for Semantic RAG</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

          {/* 跨维度重点提炼 */}
          <div className="mt-6">
            <OverviewHighlights highlights={company.highlights} />
          </div>

          {/* 原始文档附件 */}
          <div className="mt-6">
            <CompanyDocuments companyId={companyId} />
          </div>
        </TabsContent>

        <TabsContent value="financials" className="mt-6">
          <FinancialDashboard companyId={companyId} />
        </TabsContent>

        <TabsContent value="peers" className="mt-6">
          <PeerComparison companyId={companyId} />
        </TabsContent>

        <TabsContent value="competitors" className="mt-6">
          <CompetitiveDashboard companyId={companyId} />
        </TabsContent>

        <TabsContent value="due-diligence" className="mt-6">
          <DueDiligenceDashboard companyId={companyId} />
        </TabsContent>

        <TabsContent value="strategy" className="mt-6">
          <StrategyDashboard companyId={companyId} />
        </TabsContent>

        <TabsContent value="sales" className="mt-6">
          <SalesDashboard companyId={companyId} />
        </TabsContent>

        <TabsContent value="market" className="mt-6">
          <MarketDashboard companyId={companyId} />
        </TabsContent>

        <TabsContent value="chat" className="mt-6">
          <CompanyChat companyId={companyId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}