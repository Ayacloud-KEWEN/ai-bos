"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ReactFlow, Background, Controls, BackgroundVariant, MarkerType,
  type Node, type Edge,
} from "@xyflow/react";
import { Network } from "lucide-react";

import { apiClient } from "@/lib/api-client";

interface GNode { id: string; name: string; sector: string; status: string; intelligence_score: number; is_stub: boolean; }
interface GEdge { source: string; target: string; type: string; threat_level: number; }
interface GraphData { nodes: GNode[]; edges: GEdge[]; }

const PALETTE = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#64748b"];
function sectorColor(sector: string, sectors: string[]): string {
  const i = sectors.indexOf(sector);
  return PALETTE[i % PALETTE.length];
}

export default function KnowledgeGraphPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery<GraphData>({
    queryKey: ["graph"],
    queryFn: () => apiClient.get("/graph") as unknown as Promise<GraphData>,
  });

  const sectors = useMemo(
    () => Array.from(new Set((data?.nodes || []).map((n) => n.sector))).sort(),
    [data]
  );

  const { rfNodes, rfEdges } = useMemo(() => {
    if (!data) return { rfNodes: [] as Node[], rfEdges: [] as Edge[] };
    // 按行业分列布局：每个行业一列，列内纵向排列
    const colIndex: Record<string, number> = {};
    const perCol: Record<string, number> = {};
    const rfNodes: Node[] = data.nodes.map((n) => {
      const ci = (colIndex[n.sector] ??= sectors.indexOf(n.sector));
      const row = (perCol[n.sector] = (perCol[n.sector] ?? 0) + 1) - 1;
      const color = sectorColor(n.sector, sectors);
      return {
        id: n.id,
        position: { x: ci * 300, y: row * 96 },
        data: { label: n.name },
        style: {
          border: `2px solid ${color}`,
          borderStyle: n.is_stub ? "dashed" : "solid",
          borderRadius: 10,
          padding: "8px 12px",
          fontSize: 12,
          fontWeight: 600,
          background: n.is_stub ? "hsl(var(--muted))" : "hsl(var(--background))",
          opacity: n.is_stub ? 0.75 : 1,
          width: 170,
          color: "hsl(var(--foreground))",
        },
      };
    });
    const rfEdges: Edge[] = data.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: "competes",
      animated: e.threat_level >= 4,
      style: { stroke: e.threat_level >= 4 ? "#ef4444" : "#94a3b8", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: e.threat_level >= 4 ? "#ef4444" : "#94a3b8" },
      labelStyle: { fontSize: 10, fill: "hsl(var(--muted-foreground))" },
    }));
    return { rfNodes, rfEdges };
  }, [data, sectors]);

  return (
    <div className="flex h-[calc(100vh-1rem)] flex-col gap-4 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
            <Network className="h-7 w-7 text-primary" /> Knowledge Graph
          </h1>
          <p className="mt-1 text-muted-foreground">
            Company relationship network. Columns = sectors, arrows = competitive relationships. Click a node to open it.
          </p>
        </div>
        {/* 行业图例 */}
        <div className="flex flex-wrap gap-2">
          {sectors.map((s) => (
            <span key={s} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: sectorColor(s, sectors) }} />{s}
            </span>
          ))}
        </div>
      </div>

      <div className="flex-1 rounded-xl border bg-muted/10">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground animate-pulse">Building relationship graph…</div>
        ) : !data || data.nodes.length === 0 ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">No companies yet.</div>
        ) : (
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            onNodeClick={(_, node) => router.push(`/company-intelligence/companies/${node.id}`)}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background color="hsl(var(--muted-foreground))" variant={BackgroundVariant.Dots} gap={24} size={1} />
            <Controls className="bg-background border shadow-sm fill-foreground" />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
