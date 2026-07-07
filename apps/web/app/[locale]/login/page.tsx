"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, Loader2, Building2 } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(true);

  const doLogin = async (pwd: string) => {
    setLoading(true); setError("");
    try {
      const r = (await apiClient.post("/auth/login", { password: pwd })) as unknown as { access_token: string };
      localStorage.setItem("ai_bos_access_token", r.access_token);
      router.replace("/dashboard");
    } catch {
      setError("密码错误 / Incorrect password");
      setLoading(false);
    }
  };

  // 若后端未启用登录门，自动放行
  useEffect(() => {
    (async () => {
      try {
        const s = (await apiClient.get("/auth/status")) as unknown as { auth_required: boolean };
        if (!s.auth_required) { await doLogin(""); return; }
      } catch { /* ignore */ }
      setChecking(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (checking) return <div className="flex min-h-screen items-center justify-center text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" /></div>;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/20 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10"><Building2 className="h-6 w-6 text-primary" /></div>
          <CardTitle className="text-2xl">AI-BOS</CardTitle>
          <CardDescription>Sign in to continue</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => { e.preventDefault(); if (password) doLogin(password); }} className="space-y-3">
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" className="pl-9" autoFocus />
            </div>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={!password || loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
