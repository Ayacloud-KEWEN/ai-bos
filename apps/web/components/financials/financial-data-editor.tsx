"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Save, Trash2, X, Loader2 } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// 可编辑列（精选关键字段，避免表格过宽；其余字段保留原值不动）
const COLUMNS: { key: string; label: string; type: "text" | "int" | "num" }[] = [
  { key: "period", label: "Period", type: "text" },
  { key: "year", label: "Year", type: "int" },
  { key: "quarter", label: "Q", type: "int" },
  { key: "revenue", label: "Revenue", type: "num" },
  { key: "gross_profit", label: "Gross Profit", type: "num" },
  { key: "operating_profit", label: "Op. Profit", type: "num" },
  { key: "net_profit", label: "Net Profit", type: "num" },
  { key: "total_debt", label: "Debt", type: "num" },
  { key: "operating_cash_flow", label: "Op. Cash Flow", type: "num" },
];

type Row = Record<string, any>;

export function FinancialDataEditor({
  companyId, periods, currency, onClose,
}: {
  companyId: string; periods: Row[]; currency: string; onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [rows, setRows] = useState<Row[]>(() => periods.map((p) => ({ ...p })));
  const [savingId, setSavingId] = useState<string | null>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["financials", companyId] });
    queryClient.invalidateQueries({ queryKey: ["peers", companyId] });
  };

  const buildBody = (r: Row) => ({
    period: r.period || "N/A",
    year: r.year != null && r.year !== "" ? Number(r.year) : null,
    quarter: r.quarter != null && r.quarter !== "" ? Number(r.quarter) : null,
    currency,
    revenue: num(r.revenue), gross_profit: num(r.gross_profit), operating_profit: num(r.operating_profit),
    net_profit: num(r.net_profit), rnd_spending: num(r.rnd_spending), total_assets: num(r.total_assets),
    total_liabilities: num(r.total_liabilities), total_debt: num(r.total_debt),
    cash_and_equivalents: num(r.cash_and_equivalents), operating_cash_flow: num(r.operating_cash_flow),
    free_cash_flow: num(r.free_cash_flow),
    employee_count: r.employee_count != null && r.employee_count !== "" ? Number(r.employee_count) : null,
  });

  const saveMutation = useMutation({
    mutationFn: async (r: Row) => {
      if (r.id) return apiClient.patch(`/companies/${companyId}/financials/periods/${r.id}`, buildBody(r));
      return apiClient.post(`/companies/${companyId}/financials/periods`, buildBody(r));
    },
    onSuccess: () => invalidate(),
  });

  const deleteMutation = useMutation({
    mutationFn: async (r: Row) => {
      if (r.id) await apiClient.delete(`/companies/${companyId}/financials/periods/${r.id}`);
    },
    onSuccess: () => invalidate(),
  });

  const update = (idx: number, key: string, value: string) =>
    setRows((rs) => rs.map((r, i) => (i === idx ? { ...r, [key]: value } : r)));

  const addRow = () => setRows((rs) => [...rs, { period: "", _new: true }]);

  const saveRow = async (idx: number) => {
    const r = rows[idx];
    setSavingId(r.id || `new-${idx}`);
    try {
      const res: any = await saveMutation.mutateAsync(r);
      if (!r.id && res?.id) setRows((rs) => rs.map((x, i) => (i === idx ? { ...x, id: res.id, _new: false } : x)));
    } finally { setSavingId(null); }
  };

  const deleteRow = async (idx: number) => {
    const r = rows[idx];
    if (r.id && !confirm("Delete this period?")) return;
    await deleteMutation.mutateAsync(r);
    setRows((rs) => rs.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold">Edit Financial Data</h3>
          <p className="text-sm text-muted-foreground">Correct AI-extracted figures. Values are raw {currency} amounts. Save each row individually.</p>
        </div>
        <Button variant="outline" size="sm" onClick={onClose} className="gap-1.5"><X className="h-4 w-4" /> Done</Button>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              {COLUMNS.map((c) => <TableHead key={c.key} className="whitespace-nowrap">{c.label}</TableHead>)}
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r, idx) => (
              <TableRow key={r.id || `new-${idx}`}>
                {COLUMNS.map((c) => (
                  <TableCell key={c.key} className="p-1.5">
                    <Input
                      value={r[c.key] ?? ""}
                      onChange={(e) => update(idx, c.key, e.target.value)}
                      type={c.type === "text" ? "text" : "number"}
                      className="h-8 w-[110px] text-sm"
                    />
                  </TableCell>
                ))}
                <TableCell className="p-1.5 text-right whitespace-nowrap">
                  <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => saveRow(idx)}
                    disabled={savingId === (r.id || `new-${idx}`)} title="Save">
                    {savingId === (r.id || `new-${idx}`) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4 text-emerald-600" />}
                  </Button>
                  <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => deleteRow(idx)} title="Delete">
                    <Trash2 className="h-4 w-4 text-rose-500" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Button variant="outline" size="sm" onClick={addRow} className="gap-1.5"><Plus className="h-4 w-4" /> Add period</Button>
    </div>
  );
}

function num(v: any): number | null {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}
