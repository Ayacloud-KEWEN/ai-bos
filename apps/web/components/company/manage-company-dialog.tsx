"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, FileUp, PencilLine, Loader2 } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

interface CompanyLite {
  id: string; name: string; industry?: string; sector?: string; location?: string;
  documents_analyzed?: number;
}

export function ManageCompanyDialog({
  company, open, onOpenChange,
}: {
  company: CompanyLite | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [sector, setSector] = useState("");
  const [location, setLocation] = useState("");

  // 进入弹窗时用当前公司值初始化表单
  const seed = (c: CompanyLite) => {
    setName(c.name || "");
    setIndustry(c.industry || "");
    setSector(c.sector || "");
    setLocation(c.location || "");
    setFile(null);
    setProgress(0);
  };

  const { data: sectorData } = useQuery<{ sectors: string[] }>({
    queryKey: ["sectors"],
    queryFn: () => apiClient.get("/companies/sectors") as unknown as Promise<{ sectors: string[] }>,
    staleTime: Infinity,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["companies"] });
    if (company) {
      queryClient.invalidateQueries({ queryKey: ["company", company.id] });
      queryClient.invalidateQueries({ queryKey: ["financials", company.id] });
      queryClient.invalidateQueries({ queryKey: ["competitive", company.id] });
      queryClient.invalidateQueries({ queryKey: ["peers", company.id] });
    }
  };

  const reuploadMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("file", file as File);
      return apiClient.post(`/companies/${company!.id}/reupload`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
        onUploadProgress: (e) => e.total && setProgress(Math.round((e.loaded * 100) / e.total)),
      });
    },
    onSuccess: () => { invalidate(); onOpenChange(false); },
  });

  const editMutation = useMutation({
    mutationFn: () =>
      apiClient.patch(`/companies/${company!.id}`, { name, industry, sector, location }),
    onSuccess: () => { invalidate(); onOpenChange(false); },
  });

  if (!company) return null;

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => { if (v && company) seed(company); onOpenChange(v); }}
    >
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>Manage · {company.name}</DialogTitle>
          <DialogDescription>
            Re-upload a newer report to refresh the analysis, or correct the company’s basic information.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="reupload" className="mt-2">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="reupload" className="gap-1.5"><FileUp className="h-4 w-4" /> Re-upload Report</TabsTrigger>
            <TabsTrigger value="edit" className="gap-1.5"><PencilLine className="h-4 w-4" /> Edit Info</TabsTrigger>
          </TabsList>

          {/* 重新上传财报/文档 */}
          <TabsContent value="reupload" className="mt-4 space-y-4">
            <p className="text-sm text-muted-foreground">
              Adds to existing intelligence: refreshes the executive summary & vector and
              <span className="font-medium text-foreground"> re-runs financial + competitive analysis</span>.
              Currently {company.documents_analyzed ?? 0} document(s) analyzed.
            </p>
            <div className="rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 text-center transition-colors hover:bg-muted/20">
              <Input type="file" id="reupload-file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.csv,.html" className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <label htmlFor="reupload-file" className="flex cursor-pointer flex-col items-center">
                <UploadCloud className="mb-2 h-8 w-8 text-muted-foreground" />
                <span className="text-sm font-medium text-primary hover:underline">
                  {file ? file.name : "Click to select a file (PDF, Word, PPT, Excel…)"}
                </span>
              </label>
            </div>
            {reuploadMutation.isPending && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Re-analyzing…</span><span>{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}
            <div className="flex justify-end gap-3 border-t pt-4">
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button disabled={!file || reuploadMutation.isPending} onClick={() => reuploadMutation.mutate()}>
                {reuploadMutation.isPending ? <><Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> Processing</> : "Re-analyze"}
              </Button>
            </div>
          </TabsContent>

          {/* 补充/修正基础信息 */}
          <TabsContent value="edit" className="mt-4 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Company Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Industry (free text)</label>
                <Input value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="e.g. Cloud data analytics" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Location</label>
                <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Paris, France" />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Standard Sector (used for peer comparison)</label>
              <select
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="">— Select sector —</option>
                {(sectorData?.sectors || []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-3 border-t pt-4">
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button disabled={!name || editMutation.isPending} onClick={() => editMutation.mutate()}>
                {editMutation.isPending ? <><Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> Saving</> : "Save Changes"}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
