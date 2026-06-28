"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { 
  Plus, Building, MapPin, Activity,
  UploadCloud, FileText, Trash2, Edit, ChevronRight, Search, Network, GitCompare
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ManageCompanyDialog } from "@/components/company/manage-company-dialog";
import { OnlineScanDialog } from "@/components/company/online-scan-dialog";

// 定义后端返回的公司数据结构
interface Company {
  id: string;
  name: string;
  industry: string;
  sector?: string;
  location: string;
  status: string;
  intelligence_score: number;
  documents_analyzed: number;
  summary: string;
  updated_at: string;
}

export default function CompaniesPage() {
  const t = useTranslations("Sidebar"); // 如果你还没配好多语言，这里可以暂时忽略
  const router = useRouter();
  const queryClient = useQueryClient();
  
  // 状态管理
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [manageCompany, setManageCompany] = useState<Company | null>(null);

  // 筛选与分类
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState<string>("all");
  const [hideStubs, setHideStubs] = useState(true);

  // ==========================================
  // 1. 数据查询与提交 (React Query)
  // ==========================================

  // 获取真实公司列表
  const { data: companies = [], isLoading } = useQuery<Company[]>({
    queryKey: ["companies"],
    queryFn: () => apiClient.get("/companies/"),
  });

  // 提交文档与分析的 Mutation
  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      return apiClient.post("/companies/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000, // 覆盖默认 15s：AI 文档解析 + 向量化耗时较长
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          }
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["companies"] }); // 刷新列表
      setIsDialogOpen(false); // 关闭弹窗
      setNewCompanyName("");
      setSelectedFile(null);
      setUploadProgress(0);
    },
  });

  // 删除公司 Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/companies/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["companies"] }),
  });

  // ==========================================
  // 2. 交互处理函数
  // ==========================================

  const handleExecuteUpload = () => {
    if (!selectedFile || !newCompanyName) return;
    const formData = new FormData();
    formData.append("name", newCompanyName);
    formData.append("file", selectedFile);
    uploadMutation.mutate(formData);
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止点击事件冒泡，防止误触跳转
    if (confirm("Are you sure you want to delete this company's intelligence data? This action is irreversible.")) {
      deleteMutation.mutate(id);
    }
  };

  const handleManage = (company: Company, e: React.MouseEvent) => {
    e.stopPropagation();
    setManageCompany(company);
  };

  // ==========================================
  // 2b. 筛选与按行业分组
  // ==========================================
  const isStub = (c: Company) => (c.status || "").startsWith("Discovered");
  const allSectors = Array.from(
    new Set(companies.map((c) => c.sector).filter(Boolean) as string[])
  ).sort();

  const filtered = companies.filter((c) => {
    if (hideStubs && isStub(c)) return false;
    if (sectorFilter !== "all" && (c.sector || "Uncategorized") !== sectorFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      if (!`${c.name} ${c.industry || ""} ${c.sector || ""}`.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // 按标准行业分组（"全部行业"时分组展示，便于分类查看）
  const grouped: Record<string, Company[]> = {};
  for (const c of filtered) {
    const key = c.sector || "Uncategorized";
    (grouped[key] ||= []).push(c);
  }
  const groupKeys = Object.keys(grouped).sort();

  const renderCard = (company: Company) => (
    <Card
      key={company.id}
      className="flex flex-col hover:border-primary/40 hover:shadow-md transition-all duration-300 cursor-pointer group relative overflow-hidden"
      onClick={() => router.push(`/company-intelligence/companies/${company.id}`)}
    >
      <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 z-10 translate-x-2 group-hover:translate-x-0">
        <Button
          variant="secondary" size="icon" className="h-8 w-8 bg-background/90 backdrop-blur shadow-sm hover:bg-muted"
          onClick={(e) => handleManage(company, e)}
          title="Re-upload report / Edit info"
        >
          <Edit className="h-4 w-4 text-muted-foreground" />
        </Button>
        <Button
          variant="destructive" size="icon" className="h-8 w-8 opacity-90 hover:opacity-100 shadow-sm"
          onClick={(e) => handleDelete(company.id, e)}
          title="Delete Intelligence Data"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <CardHeader className="pb-3">
        <div className="flex justify-between items-start pr-16">
          <div className="space-y-1">
            <CardTitle className="text-xl flex items-center gap-2">
              <Building className="h-5 w-5 text-primary" />
              <span className="truncate max-w-[180px]">{company.name}</span>
            </CardTitle>
            <CardDescription className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {company.location || "Unknown"}
            </CardDescription>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge variant="outline" className="bg-primary/5 text-primary/80 border-primary/20">
            {company.status}
          </Badge>
          {company.sector && (
            <Badge variant="secondary" className="text-xs font-normal">{company.sector}</Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-4">
        <div className="flex justify-between items-center bg-muted/30 p-3 rounded-lg border border-muted/50">
          <div className="space-y-1">
            <span className="text-xs text-muted-foreground flex items-center gap-1"><Activity className="h-3 w-3" /> Score</span>
            <p className="text-lg font-bold text-primary">{company.intelligence_score}</p>
          </div>
          <div className="space-y-1 text-right">
            <span className="text-xs text-muted-foreground flex items-center gap-1 justify-end"><FileText className="h-3 w-3" /> Docs</span>
            <p className="text-lg font-bold">{company.documents_analyzed}</p>
          </div>
        </div>
        <div className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">{company.summary}</div>
      </CardContent>

      <CardFooter className="pt-0 pb-4">
        <div className="w-full flex items-center justify-between text-sm text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
          <span>View Full Intelligence</span>
          <ChevronRight className="h-4 w-4 transform group-hover:translate-x-1 transition-transform" />
        </div>
      </CardFooter>
    </Card>
  );

  // ==========================================
  // 3. UI 渲染
  // ==========================================

  return (
    <div className="flex flex-col gap-6 p-8 animate-in fade-in duration-500">
      
      {/* 顶部标题与操作栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Company Intelligence</h1>
          <p className="text-muted-foreground mt-2">
            Upload financial reports to generate vector-based intelligence.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
        <OnlineScanDialog />
        <Button variant="outline" className="gap-2" onClick={() => router.push("/company-intelligence/knowledge-graph")}>
          <Network className="h-4 w-4" />
          Knowledge Graph
        </Button>
        <Button variant="outline" className="gap-2" onClick={() => router.push("/company-intelligence/compare")}>
          <GitCompare className="h-4 w-4" />
          Compare
        </Button>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2 shadow-sm">
              <Plus className="h-4 w-4" />
              Add Company
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Agent Document Scanner</DialogTitle>
              <DialogDescription>
                Upload a financial report. Local AI will extract entities and save 768-dim vector embeddings.
              </DialogDescription>
            </DialogHeader>
            
            <div className="mt-4 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Target Company Name</label>
                <Input 
                  placeholder="e.g. Aya Cloud" 
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                />
              </div>

              <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 flex flex-col items-center justify-center text-center transition-colors hover:bg-muted/20">
                <Input 
                  type="file" 
                  className="hidden" 
                  id="file-upload" 
                  accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.csv,.html"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                />
                <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                  <UploadCloud className="h-8 w-8 text-muted-foreground mb-2" />
                  <span className="text-sm font-medium text-primary hover:underline">
                    {selectedFile ? selectedFile.name : "Click to select a document (PDF, Word, PPT, Excel…)"}
                  </span>
                </label>
              </div>

              {uploadMutation.isPending && (
                <div className="space-y-2 pt-2 animate-in slide-in-from-bottom-2">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>LangChain Pipeline Running...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} className="h-2" />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6 border-t pt-4">
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
              <Button 
                onClick={handleExecuteUpload} 
                disabled={!selectedFile || !newCompanyName || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? "Executing..." : "Launch Analysis"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {/* 筛选栏 */}
      {!isLoading && companies.length > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name, industry…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="all">All sectors</option>
            {allSectors.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" checked={hideStubs} onChange={(e) => setHideStubs(e.target.checked)} className="h-4 w-4 rounded border-input" />
            Hide discovered competitors
          </label>
          <span className="text-sm text-muted-foreground sm:ml-auto">{filtered.length} compan{filtered.length === 1 ? "y" : "ies"}</span>
        </div>
      )}

      {/* 数据渲染（按行业分组） */}
      {isLoading ? (
        <div className="mt-10 flex justify-center items-center h-40 text-muted-foreground animate-pulse border-2 border-dashed rounded-lg">
          Loading AI Intelligence Engine...
        </div>
      ) : companies.length === 0 ? (
        <div className="py-16 flex flex-col items-center justify-center border-2 border-dashed rounded-lg text-muted-foreground">
          <Building className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p>No intelligence data found in pgvector.</p>
          <p className="text-sm mt-1">Click 'Add Company' to launch a LangChain agent scan.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 flex flex-col items-center justify-center border-2 border-dashed rounded-lg text-muted-foreground">
          <Building className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p>No companies match your filters.</p>
        </div>
      ) : sectorFilter !== "all" ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(renderCard)}
        </div>
      ) : (
        // 全部行业：按标准行业分组展示，便于分类查看
        <div className="space-y-8">
          {groupKeys.map((sector) => (
            <div key={sector}>
              <div className="mb-3 flex items-center gap-2">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{sector}</h2>
                <Badge variant="secondary" className="text-xs">{grouped[sector].length}</Badge>
              </div>
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {grouped[sector].map(renderCard)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 公司管理弹窗：重新上传财报 / 补充信息 */}
      <ManageCompanyDialog
        company={manageCompany}
        open={!!manageCompany}
        onOpenChange={(v) => { if (!v) setManageCompany(null); }}
      />
    </div>
  );
}