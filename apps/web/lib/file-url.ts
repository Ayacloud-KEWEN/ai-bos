// 生成带鉴权的文件 URL：新标签打开的下载/查看链接无法带 Authorization 头，
// 因此把 token 作为 ?token= 附上（后端登录门同时支持 header 与 query）。
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function fileUrl(path: string): string {
  const base = `${API_BASE}${path}`;
  if (typeof window === "undefined") return base;
  const token = localStorage.getItem("ai_bos_access_token");
  if (!token) return base;
  return base + (base.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(token);
}
