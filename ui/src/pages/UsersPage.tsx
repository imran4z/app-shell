/**
 * Users - the app's own account directory. List page with inline
 * management: change a role from a select, activate/disable from the row,
 * invite from the header. No detail page needed; Profiles demonstrates
 * that pattern.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { CheckCircle2, Loader2, MailPlus, ShieldBan, Trash2, UserCheck, UserPlus, Users } from "lucide-react";

import { Badge, userStatusTone } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchInput } from "@/components/SearchInput";
import { StatKpi } from "@/components/StatKpi";
import { useToasts } from "@/components/Toast";
import {
  deleteUser,
  getUserStats,
  inviteUser,
  listUsers,
  setUserStatus,
  updateUser,
  type AppUser,
  type UserRole,
} from "@/lib/api";

const ROLES: UserRole[] = ["admin", "member", "viewer"];

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function UsersPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const { push } = useToasts();
  const qc = useQueryClient();

  const stats = useQuery({
    queryKey: ["user-stats"],
    queryFn: getUserStats,
    refetchInterval: 10_000,
  });
  const users = useQuery({
    queryKey: ["users", q || "all", page, pageSize],
    queryFn: () => listUsers({ q: q || undefined, limit: pageSize, offset: (page - 1) * pageSize }),
    refetchInterval: 10_000,
    placeholderData: (prev) => prev,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["users"] });
    qc.invalidateQueries({ queryKey: ["user-stats"] });
  };
  const onError = (e: unknown) => push({ tone: "danger", title: "Request failed", body: String(e) });

  const invite = useMutation({
    mutationFn: () => inviteUser({ name: inviteName.trim(), email: inviteEmail.trim() }),
    onSuccess: (user) => {
      setInviteName("");
      setInviteEmail("");
      invalidate();
      push({ tone: "success", title: "User invited", body: user.email });
    },
    onError,
  });

  const setRole = useMutation({
    mutationFn: (input: { id: string; role: UserRole }) => updateUser(input.id, { role: input.role }),
    onSuccess: invalidate,
    onError,
  });

  const setStatus = useMutation({
    mutationFn: (input: { id: string; status: "active" | "disabled" }) =>
      setUserStatus(input.id, input.status),
    onSuccess: invalidate,
    onError,
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => {
      invalidate();
      push({ tone: "info", title: "User removed" });
    },
    onError,
  });

  const counts = stats.data?.counts;
  const canInvite = inviteName.trim() && inviteEmail.trim().includes("@");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="account directory"
        title="Users"
        lede="Everyone who can use this app: role, account status, and invitations. Wire your auth flow to this table when you build the real app."
        actions={
          <form
            className="flex flex-wrap items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (canInvite) invite.mutate();
            }}
          >
            <input
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              placeholder="Name"
              className="h-9 w-36 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-elev1)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
            />
            <input
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="email@company.com"
              type="email"
              className="h-9 w-52 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-elev1)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
            />
            <Button type="submit" variant="primary" size="sm" disabled={invite.isPending || !canInvite}>
              {invite.isPending ? <Loader2 size={12} className="animate-spin" /> : <MailPlus size={12} />}
              Invite
            </Button>
          </form>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 2xl:gap-4">
        <StatKpi label="Active" value={counts?.active ?? "-"} tone="success" icon={UserCheck} />
        <StatKpi label="Invited" value={counts?.invited ?? "-"} tone="info" icon={UserPlus} />
        <StatKpi label="Disabled" value={counts?.disabled ?? "-"} tone="muted" icon={ShieldBan} />
        <StatKpi label="Total" value={stats.data?.total ?? "-"} tone="accent" icon={Users} />
      </div>

      <SearchInput
        value={q}
        onChange={(v) => {
          setQ(v);
          setPage(1);
        }}
        placeholder="Filter by name or email..."
        className="max-w-sm"
      />

      <section>
        <Card className="p-0 overflow-hidden">
          {users.isLoading ? (
            <div className="p-8 text-center text-[var(--color-text-faint)]">Loading...</div>
          ) : users.isError ? (
            <div className="p-8 text-center text-sm text-[var(--color-danger)]">
              {String(users.error)}
            </div>
          ) : users.data && users.data.entries.length === 0 ? (
            <div className="p-12 text-center">
              <Users size={24} className="mx-auto text-[var(--color-text-faint)]" />
              <p className="mt-3 text-sm font-medium">No users yet</p>
              <p className="mx-auto mt-1 max-w-sm text-xs text-[var(--color-text-muted)]">
                Invite one above, or run <code className="font-mono">just seed</code> to load demo
                accounts.
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-[var(--color-border)] font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-faint)]">
                    <tr>
                      <th className="px-4 py-2.5 text-left font-medium">User</th>
                      <th className="hidden px-4 py-2.5 text-left font-medium sm:table-cell">Email</th>
                      <th className="px-4 py-2.5 text-left font-medium">Role</th>
                      <th className="px-4 py-2.5 text-left font-medium">Status</th>
                      <th className="hidden px-4 py-2.5 text-right font-medium md:table-cell">
                        Last seen
                      </th>
                      <th className="px-4 py-2.5 text-right font-medium" aria-label="Actions" />
                    </tr>
                  </thead>
                  <tbody>
                    {users.data?.entries.map((user) => (
                      <UserRow
                        key={user.id}
                        user={user}
                        onRole={(role) => setRole.mutate({ id: user.id, role })}
                        onStatus={(status) => setStatus.mutate({ id: user.id, status })}
                        onDelete={() => remove.mutate(user.id)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={users.data?.total ?? 0}
                onPageChange={setPage}
                onPageSizeChange={(n) => {
                  setPageSize(n);
                  setPage(1);
                }}
              />
            </>
          )}
        </Card>
      </section>
    </div>
  );
}

function UserRow({
  user,
  onRole,
  onStatus,
  onDelete,
}: {
  user: AppUser;
  onRole: (role: UserRole) => void;
  onStatus: (status: "active" | "disabled") => void;
  onDelete: () => void;
}) {
  return (
    <tr className="border-b border-[var(--color-border)] transition-colors last:border-0 hover:bg-white/[0.02]">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[var(--color-accent-border)] bg-[var(--color-accent-bg)] font-mono text-[10px] text-[var(--color-accent)]">
            {initials(user.name)}
          </span>
          <span className="font-medium">{user.name}</span>
        </div>
      </td>
      <td className="hidden px-4 py-3 font-mono text-xs text-[var(--color-text-muted)] sm:table-cell">
        {user.email}
      </td>
      <td className="px-4 py-3">
        <select
          value={user.role}
          onChange={(e) => onRole(e.target.value as UserRole)}
          aria-label={`Role for ${user.name}`}
          className="h-7 rounded-md border border-[var(--color-border)] bg-[var(--color-canvas)] px-1.5 font-mono text-xs outline-none transition-colors focus:border-[var(--color-accent)]"
        >
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </td>
      <td className="px-4 py-3">
        <Badge tone={userStatusTone(user.status)}>{user.status}</Badge>
      </td>
      <td className="hidden px-4 py-3 text-right text-xs text-[var(--color-text-muted)] tabular-nums md:table-cell">
        {user.last_seen_at ? new Date(user.last_seen_at).toLocaleString() : "-"}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1.5">
          {user.status !== "active" && (
            <button
              type="button"
              title="Activate"
              aria-label={`Activate ${user.name}`}
              onClick={() => onStatus("active")}
              className="text-[var(--color-text-faint)] transition-colors hover:text-[var(--color-success)]"
            >
              <CheckCircle2 size={14} />
            </button>
          )}
          {user.status !== "disabled" && (
            <button
              type="button"
              title="Disable"
              aria-label={`Disable ${user.name}`}
              onClick={() => onStatus("disabled")}
              className="text-[var(--color-text-faint)] transition-colors hover:text-[var(--color-warning)]"
            >
              <ShieldBan size={14} />
            </button>
          )}
          <button
            type="button"
            title="Remove"
            aria-label={`Remove ${user.name}`}
            onClick={onDelete}
            className="text-[var(--color-text-faint)] transition-colors hover:text-[var(--color-danger)]"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </td>
    </tr>
  );
}
