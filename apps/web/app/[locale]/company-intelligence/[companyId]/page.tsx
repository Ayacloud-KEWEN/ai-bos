"use client";

import { useParams } from "next/navigation";
import { ArrowLeft, Download, Building2, Globe, Users, TrendingUp, Target, Network } from "lucide-react";
import { Link } from "@/i18n/routing";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// 模拟读取单个公司的详细情报
const mockCompanyData = {
  id: "c_001",
  name: "Aya Cloud",
  industry: "AI & Creative Studio",
  website: "ayacloud.com",
  employees: "50-200",
  revenue: "$15M - $25M",
  headquarters: "Paris, France",
  summary: "Aya Cloud is a leading AI-driven creative studio focusing on game development, enterprise SaaS solutions, and next-generation interactive experiences.",
};

export default function CompanyDetailPage() {
  const params = useParams();
  const { companyId } = params;

  return (
    <div className="flex flex-col gap-6 p-8">
      {/* 顶部导航与操作栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild className="h-8 w-8">
            <Link href="/company-intelligence/companies">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{mockCompanyData.name}</h1>
              <Badge variant="default">Active Monitoring</Badge>
            </div>
            <p className="text-muted-foreground mt-1 flex items-center gap-4 text-sm">
              <span className="flex items-center gap-1"><Building2 className="h-3 w-3"/> {mockCompanyData.industry}</span>
              <span className="flex items-center gap-1"><Globe className="h-3 w-3"/> {mockCompanyData.headquarters}</span>
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2">
            <Network className="h-4 w-4" /> View Knowledge Graph
          </Button>
          <Button className="gap-2">
            <Download className="h-4 w-4" /> Export Report
          </Button>
        </div>
      </div>

      {/* 核心情报 Tabs 切换区 */}
      <Tabs defaultValue="overview" className="w-full mt-4">
        <TabsList className="grid w-full grid-cols-4 max-w-[600px]">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="financials">Financials</TabsTrigger>
          <TabsTrigger value="competitors">Competitors</TabsTrigger>
          <TabsTrigger value="sales">Sales Intelligence</TabsTrigger>
        </TabsList>
        
        {/* 概览标签页 */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Executive Summary</CardTitle>
                <CardDescription>AI-generated overview from latest documents.</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="leading-relaxed text-sm">{mockCompanyData.summary}</p>
                <div className="mt-6 grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-muted-foreground">Estimated Revenue</p>
                    <p className="font-semibold">{mockCompanyData.revenue}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-muted-foreground">Employee Count</p>
                    <p className="font-semibold">{mockCompanyData.employees}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Company Scanner Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-muted-foreground">Intelligence Score</span>
                  <span className="font-bold text-primary">98/100</span>
                </div>
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-muted-foreground">Docs Analyzed</span>
                  <span className="font-medium">45 Files</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Last Scan</span>
                  <span className="font-medium">2 hours ago</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 财务标签页 (占位) */}
        <TabsContent value="financials" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5" /> Financial Intelligence</CardTitle>
              <CardDescription>Revenue, Gross Profit, and Historical Trends.</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center border-t bg-muted/10">
              <p className="text-muted-foreground">Financial charts and analysis will render here.</p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 竞争对手标签页 (占位) */}
        <TabsContent value="competitors" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Target className="h-5 w-5" /> Competitive Matrix</CardTitle>
              <CardDescription>Direct and indirect competitors identified by AI.</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center border-t bg-muted/10">
              <p className="text-muted-foreground">Competitive analysis battlecards will render here.</p>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* 销售情报标签页 (占位) */}
        <TabsContent value="sales" className="mt-6">
           <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Users className="h-5 w-5" /> Sales Intelligence</CardTitle>
              <CardDescription>Ideal Customer Profiles, Pain Points, and Buying Triggers.</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center border-t bg-muted/10">
              <p className="text-muted-foreground">ICP and Sales opportunities will render here.</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}