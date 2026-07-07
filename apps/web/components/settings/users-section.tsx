"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, Plus, Trash2, Loader2, Shield } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface U { id: string; username: string; full_name: string | null; is_superuser: boolean; is_active: boolean; }

export function UsersSection() {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  const { data: status } = useQuery<{ auth_required: boolean }>({
    queryKey: ["auth-status"],
    queryFn: () => apiClient.get("/auth/status") as unknown as Promise<{ auth_required: boolean }>,
  });
  const { data: users = [] } = useQuery<U[]>({
    queryKey: ["users"],
    queryFn: () => apiClient.get("/auth/users") as unknown as Promise<U[]>,
    enabled: !!status?.auth_required,
  });

  const inval = () => queryClient.invalidateQueries({ queryKey: ["users"] });
  const create = useMutation({
    mutationFn: () => apiClient.post("/auth/users", { username, password, is_superuser: isAdmin }),
    onSuccess: () => { inval(); setUsername(""); setPassword(""); setIsAdmin(false); },
  });
  const del = useMutation({ mutationFn: (id: string) => apiClient.delete(`/auth/users/${id}`), onSuccess: inval });

  if (!status?.auth_required) return null;  // 未启用登录门时不显示

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg"><Users className="h-5 w-5" /> Users</CardTitle>
        <CardDescription>Manage who can sign in. Username can be an email or any identifier.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.id} className="flex items-center justify-between rounded-lg border p-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{u.username}</span>
                {u.is_superuser && <Badge variant="secondary" className="gap-1 text-[10px]"><Shield className="h-3 w-3" />admin</Badge>}
                {!u.is_active && <Badge variant="outline" className="text-[10px]">disabled</Badge>}
              </div>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { if (confirm(`Delete ${u.username}?`)) del.mutate(u.id); }}>
                <Trash2 className="h-4 w-4 text-rose-500" />
              </Button>
            </div>
          ))}
          {users.length === 0 && <p className="text-sm text-muted-foreground">Only the shared/admin credential is configured.</p>}
        </div>

        <div className="grid gap-3 border-t pt-4 sm:grid-cols-2">
          <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="New username" />
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} className="h-4 w-4 rounded border-input" /> Admin
          </label>
          <div className="flex justify-end">
            <Button className="gap-2" disabled={!username || !password || create.isPending} onClick={() => create.mutate()}>
              {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Add user
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
