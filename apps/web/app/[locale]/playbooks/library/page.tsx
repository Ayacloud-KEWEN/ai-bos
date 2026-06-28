"use client";

import { useTranslations } from "next-intl";
import { Search, Plus, BookOpenText, Play, Clock, BarChart, Bot, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Link } from "@/i18n/routing";

// 占位 Playbook 数据 (基于 Master Spec 的标准模板)
const playbooks = [
    {
        id: "pb_001",
        title: "European Market Entry",
        description: "End-to-end execution plan for launching products in the EU market, including compliance, localization, and channel partner strategies.",
        category: "Strategy",
        difficulty: "Hard",
        estimatedTime: "4 Weeks",
        agents: 3,
        runs: 12,
        isAiGenerated: true,
    },
    {
        id: "pb_002",
        title: "B2B Sales Pipeline Builder",
        description: "Automated workflow to extract ICPs, generate buyer personas, and create personalized outreach battlecards.",
        category: "Sales",
        difficulty: "Medium",
        estimatedTime: "1 Week",
        agents: 2,
        runs: 45,
        isAiGenerated: false,
    },
    {
        id: "pb_003",
        title: "Series A Fundraising",
        description: "Comprehensive investor outreach playbook. Generates investor memos, pitch decks, and due diligence preparation lists.",
        category: "Fundraising",
        difficulty: "Hard",
        estimatedTime: "6 Weeks",
        agents: 4,
        runs: 3,
        isAiGenerated: true,
    },
    {
        id: "pb_004",
        title: "Competitive Sales Campaign",
        description: "Rapid deployment playbook to counter a specific competitor's new product launch with targeted marketing and sales assets.",
        category: "Marketing",
        difficulty: "Easy",
        estimatedTime: "3 Days",
        agents: 1,
        runs: 28,
        isAiGenerated: false,
    },
];

export default function PlaybookLibraryPage() {
    const t = useTranslations("Sidebar");

    return (
        <div className="flex flex-col gap-6 p-8">
            {/* 顶部标题与操作区 */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{t("playbooks")} Library</h1>
                    <p className="text-muted-foreground mt-2">
                        Transform intelligence into execution with AI-powered business methodologies.
                    </p>
                </div>
                <div className="flex gap-3">
                    <Button variant="secondary" className="gap-2">
                        <Plus className="h-4 w-4" />
                        Create from Scratch
                    </Button>
                    <Button className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white">
                        <Sparkles className="h-4 w-4" />
                        AI Generate Playbook
                    </Button>
                </div>
            </div>

            {/* 搜索与分类导航 */}
            <div className="flex flex-col sm:flex-row justify-between gap-4 mt-2">
                <Tabs defaultValue="all" className="w-full sm:w-auto">
                    <TabsList>
                        <TabsTrigger value="all">All</TabsTrigger>
                        <TabsTrigger value="sales">Sales</TabsTrigger>
                        <TabsTrigger value="marketing">Marketing</TabsTrigger>
                        <TabsTrigger value="strategy">Strategy</TabsTrigger>
                        <TabsTrigger value="fundraising">Fundraising</TabsTrigger>
                    </TabsList>
                </Tabs>

                <div className="relative w-full sm:max-w-xs">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        type="search"
                        placeholder="Search playbooks..."
                        className="pl-8 bg-background"
                    />
                </div>
            </div>

            {/* Playbook 卡片网格 */}
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3 mt-4">
                {playbooks.map((playbook) => (
                    <Card key={playbook.id} className="flex flex-col hover:border-primary/50 transition-all shadow-sm hover:shadow-md">
                        <CardHeader className="pb-4">
                            <div className="flex justify-between items-start mb-2">
                                <Badge variant="outline" className="bg-background text-xs">
                                    {playbook.category}
                                </Badge>
                                {playbook.isAiGenerated && (
                                    <Badge variant="secondary" className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-none flex items-center gap-1 text-xs">
                                        <Sparkles className="h-3 w-3" /> AI Generated
                                    </Badge>
                                )}
                            </div>
                            <CardTitle className="text-xl flex items-center gap-2">
                                <BookOpenText className="h-5 w-5 text-muted-foreground" />
                                {playbook.title}
                            </CardTitle>
                            <CardDescription className="line-clamp-2 mt-2 leading-relaxed">
                                {playbook.description}
                            </CardDescription>
                        </CardHeader>

                        <CardContent className="flex-1">
                            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground bg-muted/30 p-3 rounded-md">
                                <div className="flex items-center gap-1.5">
                                    <BarChart className="h-4 w-4" />
                                    <span>{playbook.difficulty}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <Clock className="h-4 w-4" />
                                    <span>{playbook.estimatedTime}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <Bot className="h-4 w-4" />
                                    <span>{playbook.agents} Agents</span>
                                </div>
                            </div>
                        </CardContent>

                        <CardFooter className="flex items-center justify-between border-t pt-4 bg-muted/10 mt-auto rounded-b-xl">
                            <span className="text-xs text-muted-foreground">Executed {playbook.runs} times</span>
                            <div className="flex gap-2">
                                <Button variant="ghost" size="sm">Details</Button>
                                <Button size="sm" className="gap-1.5" asChild>
                                    <Link href={`/workflows/${playbook.id}`}>
                                        <Play className="h-3.5 w-3.5 fill-current" /> Execute
                                    </Link>
                                </Button>
                            </div>
                        </CardFooter>
                    </Card>
                ))}
            </div>
        </div>
    );
}