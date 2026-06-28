// 财务数值格式化工具

/** 将大额数字压缩为 1.2B / 345.6M / 12.3K 形式 */
export function formatCompact(value: number | null | undefined, currency?: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const prefix = currency ? currencySymbol(currency) : "";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  let out: string;
  if (abs >= 1e12) out = (abs / 1e12).toFixed(2) + "T";
  else if (abs >= 1e9) out = (abs / 1e9).toFixed(2) + "B";
  else if (abs >= 1e6) out = (abs / 1e6).toFixed(2) + "M";
  else if (abs >= 1e3) out = (abs / 1e3).toFixed(1) + "K";
  else out = abs.toFixed(0);
  return `${sign}${prefix}${out}`;
}

/** 百分比，带符号；用于增长率展示 */
export function formatPct(value: number | null | undefined, withSign = false): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = withSign && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function currencySymbol(code?: string): string {
  switch ((code || "USD").toUpperCase()) {
    case "USD": return "$";
    case "EUR": return "€";
    case "GBP": return "£";
    case "CNY":
    case "RMB": return "¥";
    case "JPY": return "¥";
    default: return "";
  }
}

/** 根据增长方向返回 tailwind 颜色类 */
export function growthColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-muted-foreground";
  if (value > 0) return "text-emerald-600";
  if (value < 0) return "text-rose-600";
  return "text-muted-foreground";
}
