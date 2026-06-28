"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ReactFlow, Background, Controls, MiniMap, BackgroundVariant, addEdge,
  useNodesState, useEdgesState, type Node, type Edge, type Connection,
} from "@xyflow/react";
import { ArrowLeft, Save, Play, Plus, Loader2, CheckCircle2 } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

const STATUS_STYLE: Record<string, { border: string; bg: string }> = {
  pending: { border: "#cbd5e1", bg: "var(--background)" },
  running: { border: "#f59e0b", bg: "#fffbeb" },
  done: { border: "#10b981", bg: "#ecfdf5" },
  failed: { border: "#ef4444", bg: "#fef2f2" },
};

function styleFor(status?: string) {
  const s = STATUS_STYLE[status || "pending"];
  return { border: `2px solid ${s.border}`, background: s.bg, borderRadius: 10, padding: "8px 14px", fontSize: 12, fontWeight: 600, minWidth: 150 };
}

export default function WorkflowBuilderPage() {
  const params = useParams();
  const router = useRouter();
  const wfId = params.id as string;

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [name, setName] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const typeLabel = useRef<Record<string, string>>({});

  const { data: nodeTypes } = useQuery<{ node_types: { type: string; label: string }[] }>({
    queryKey: ["node-types"],
    queryFn: () => apiClient.get("/workflows/node-types") as unknown as Promise<any>,
  });
  const { data: companies = [] } = useQuery<any[]>({
    queryKey: ["companies"], queryFn: () => apiClient.get("/companies/") as unknown as Promise<any[]>,
  });

  // 载入工作流
  const { data: wf } = useQuery<any>({
    queryKey: ["workflow", wfId],
    queryFn: () => apiClient.get(`/workflows/${wfId}`) as unknown as Promise<any>,
  });
  useEffect(() => {
    if (!wf) return;
    setName(wf.name);
    setNodes((wf.nodes || []).map((n: any) => ({
      id: n.id, position: n.position || { x: 0, y: 0 },
      data: { label: labelOf(n.type), ntype: n.type, config: n.config || {} },
      style: styleFor("pending"),
    })));
    setEdges((wf.edges || []).map((e: any) => ({ id: e.id, source: e.source, target: e.target, animated: true })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wf, nodeTypes]);

  function labelOf(type: string) {
    if (nodeTypes) for (const nt of nodeTypes.node_types) typeLabel.current[nt.type] = nt.label;
    return typeLabel.current[type] || type;
  }

  const onConnect = useCallback((c: Connection) => setEdges((eds) => addEdge({ ...c, animated: true }, eds)), [setEdges]);

  const addNode = (type: string, label: string) => {
    const id = `n${Date.now() % 100000}`;
    setNodes((nds) => [...nds, {
      id, position: { x: 120 + Math.random() * 200, y: 100 + Math.random() * 200 },
      data: { label, ntype: type, config: {} }, style: styleFor("pending"),
    }]);
  };

  const save = async () => {
    setSaving(true);
    try {
      const outNodes = nodes.map((n) => ({ id: n.id, type: (n.data as any).ntype, position: n.position, config: (n.data as any).config || {} }));
      const outEdges = edges.map((e) => ({ id: e.id, source: e.source, target: e.target }));
      await apiClient.put(`/workflows/${wfId}`, { name, nodes: outNodes, edges: outEdges });
    } finally { setSaving(false); }
  };

  const run = async () => {
    if (!companyId) return;
    await save();
    const r = (await apiClient.post(`/workflows/${wfId}/run`, { company_id: companyId })) as unknown as { run_id: string };
    setRunId(r.run_id); setRunStatus("running");
  };

  // 轮询运行状态 → 给节点上色
  useEffect(() => {
    if (!runId || runStatus !== "running") return;
    const t = setInterval(async () => {
      const r = (await apiClient.get(`/workflows/runs/${runId}`)) as unknown as { status: string; node_states: Record<string, any> };
      setNodes((nds) => nds.map((n) => ({ ...n, style: styleFor(r.node_states?.[n.id]?.status) })));
      if (r.status !== "running") { setRunStatus(r.status); clearInterval(t); }
    }, 3000);
    return () => clearInterval(t);
  }, [runId, runStatus, setNodes]);

  return (
    <div className="flex h-[calc(100vh-1rem)] flex-col">
      <div className="flex items-center gap-3 border-b p-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/workflows")}><ArrowLeft className="h-5 w-5" /></Button>
        <input value={name} onChange={(e) => setName(e.target.value)} className="flex-1 bg-transparent text-lg font-semibold outline-none" placeholder="Workflow name" />
        <select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="h-9 rounded-md border border-input bg-transparent px-3 text-sm">
          <option value="">Run on company…</option>
          {companies.filter((c) => !(c.status || "").startsWith("Discovered")).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <Button variant="outline" className="gap-1.5" onClick={save} disabled={saving}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save</Button>
        <Button className="gap-1.5" onClick={run} disabled={!companyId || runStatus === "running"}>
          {runStatus === "running" ? <><Loader2 className="h-4 w-4 animate-spin" /> Running</> : runStatus === "completed" ? <><CheckCircle2 className="h-4 w-4" /> Run again</> : <><Play className="h-4 w-4" /> Run</>}
        </Button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* 节点调色板 */}
        <div className="w-48 shrink-0 space-y-1.5 overflow-y-auto border-r p-3">
          <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Add Node</p>
          {(nodeTypes?.node_types || []).map((nt) => (
            <button key={nt.type} onClick={() => addNode(nt.type, nt.label)}
              className="flex w-full items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-left text-xs hover:bg-muted/50">
              <Plus className="h-3 w-3 text-muted-foreground" /> {nt.label}
            </button>
          ))}
          {runStatus && (
            <div className="mt-4 rounded-md border p-2 text-xs">
              Run: <span className={runStatus === "completed" ? "text-emerald-600" : runStatus === "failed" ? "text-rose-600" : "text-amber-600"}>{runStatus}</span>
            </div>
          )}
        </div>

        {/* 画布 */}
        <div className="flex-1">
          <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            onConnect={onConnect} fitView proOptions={{ hideAttribution: true }}>
            <Background color="hsl(var(--muted-foreground))" variant={BackgroundVariant.Dots} gap={20} size={1} />
            <Controls className="bg-background border shadow-sm fill-foreground" />
            <MiniMap pannable zoomable className="!bg-muted" />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
