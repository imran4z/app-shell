/**
 * Profiles - the template's list->detail example (BLUEPRINT.md §4: list +
 * detail pages COLOCATED in one file). The list page repeats the Items
 * composition; the detail page demonstrates the enrichment surface:
 * add/remove attributes and tags, edit the summary, move through the
 * draft -> published -> archived lifecycle.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Archive,
  CheckCircle2,
  FileText,
  Loader2,
  Plus,
  Send,
  Trash2,
  Undo2,
  Users,
  X,
} from "lucide-react";

import { Badge, profileStatusTone } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchInput } from "@/components/SearchInput";
import { StatKpi } from "@/components/StatKpi";
import { useToasts } from "@/components/Toast";
import {
  createProfile,
  deleteProfile,
  deleteProfileAttribute,
  getProfile,
  getProfileStats,
  listProfiles,
  putProfileAttribute,
  setProfileStatus,
  updateProfile,
  type Profile,
  type ProfileStatus,
} from "@/lib/api";

// --- List page -----------------------------------------------------------

export function ProfilesListPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [newName, setNewName] = useState("");
  const navigate = useNavigate();
  const { push } = useToasts();
  const qc = useQueryClient();

  const stats = useQuery({
    queryKey: ["profile-stats"],
    queryFn: getProfileStats,
    refetchInterval: 10_000,
  });
  const profiles = useQuery({
    queryKey: ["profiles", q || "all", page, pageSize],
    queryFn: () =>
      listProfiles({ q: q || undefined, limit: pageSize, offset: (page - 1) * pageSize }),
    refetchInterval: 10_000,
    placeholderData: (prev) => prev,
  });

  const create = useMutation({
    mutationFn: (name: string) => createProfile({ name }),
    onSuccess: (profile) => {
      setNewName("");
      qc.invalidateQueries({ queryKey: ["profiles"] });
      qc.invalidateQueries({ queryKey: ["profile-stats"] });
      navigate(`/profiles/${profile.id}`);
    },
    onError: (e) => push({ tone: "danger", title: "Create failed", body: String(e) }),
  });

  const counts = stats.data?.counts;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="example resource, list -> detail"
        title="Profiles"
        lede="A profile is a container you enrich over time - attributes, tags, and a publish lifecycle. Open one to see the detail-page pattern."
        actions={
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (newName.trim()) create.mutate(newName.trim());
            }}
          >
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="New profile name..."
              className="h-9 w-52 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-elev1)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={create.isPending || !newName.trim()}
            >
              {create.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              Add
            </Button>
          </form>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 2xl:gap-4">
        <StatKpi label="Draft" value={counts?.draft ?? "-"} tone="muted" icon={FileText} />
        <StatKpi label="Published" value={counts?.published ?? "-"} tone="success" icon={CheckCircle2} />
        <StatKpi label="Archived" value={counts?.archived ?? "-"} tone="warning" icon={Archive} />
        <StatKpi label="Total" value={stats.data?.total ?? "-"} tone="accent" icon={Users} />
      </div>

      <SearchInput
        value={q}
        onChange={(v) => {
          setQ(v);
          setPage(1);
        }}
        placeholder="Filter by name..."
        className="max-w-sm"
      />

      <section>
        <Card className="p-0 overflow-hidden">
          {profiles.isLoading ? (
            <div className="p-8 text-center text-[var(--color-text-faint)]">Loading...</div>
          ) : profiles.isError ? (
            <div className="p-8 text-center text-sm text-[var(--color-danger)]">
              {String(profiles.error)}
            </div>
          ) : profiles.data && profiles.data.entries.length === 0 ? (
            <div className="p-12 text-center">
              <Users size={24} className="mx-auto text-[var(--color-text-faint)]" />
              <p className="mt-3 text-sm font-medium">No profiles yet</p>
              <p className="mx-auto mt-1 max-w-sm text-xs text-[var(--color-text-muted)]">
                Add one above, or run <code className="font-mono">just seed</code> to load demo
                data.
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-[var(--color-border)] font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-faint)]">
                    <tr>
                      <th className="px-4 py-2.5 text-left font-medium">Profile</th>
                      <th className="px-4 py-2.5 text-left font-medium">Status</th>
                      <th className="hidden px-4 py-2.5 text-left font-medium md:table-cell">Tags</th>
                      <th className="hidden px-4 py-2.5 text-right font-medium sm:table-cell">
                        Facts
                      </th>
                      <th className="hidden px-4 py-2.5 text-right font-medium sm:table-cell">
                        Updated
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {profiles.data?.entries.map((profile) => (
                      <tr
                        key={profile.id}
                        onClick={() => navigate(`/profiles/${profile.id}`)}
                        className="cursor-pointer border-b border-[var(--color-border)] transition-colors last:border-0 hover:bg-white/[0.02]"
                      >
                        <td className="px-4 py-3 font-medium">{profile.name}</td>
                        <td className="px-4 py-3">
                          <Badge tone={profileStatusTone(profile.status)}>{profile.status}</Badge>
                        </td>
                        <td className="hidden px-4 py-3 md:table-cell">
                          <div className="flex flex-wrap gap-1">
                            {profile.tags.slice(0, 4).map((tag) => (
                              <span
                                key={tag}
                                className="rounded-full border border-[var(--color-border)] px-2 py-0.5 font-mono text-[10px] text-[var(--color-text-muted)]"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="hidden px-4 py-3 text-right text-xs text-[var(--color-text-muted)] tabular-nums sm:table-cell">
                          {Object.keys(profile.attributes).length}
                        </td>
                        <td className="hidden px-4 py-3 text-right text-xs text-[var(--color-text-muted)] tabular-nums sm:table-cell">
                          {profile.updated_at ? new Date(profile.updated_at).toLocaleString() : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={profiles.data?.total ?? 0}
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

// --- Detail page ---------------------------------------------------------

const STATUS_ACTIONS: Record<ProfileStatus, { to: ProfileStatus; label: string; icon: typeof Send }[]> = {
  draft: [{ to: "published", label: "Publish", icon: Send }],
  published: [
    { to: "archived", label: "Archive", icon: Archive },
    { to: "draft", label: "Back to draft", icon: Undo2 },
  ],
  archived: [{ to: "draft", label: "Restore to draft", icon: Undo2 }],
};

export function ProfileDetailPage() {
  const { profileId = "" } = useParams();
  const navigate = useNavigate();
  const { push } = useToasts();
  const qc = useQueryClient();

  const profile = useQuery({
    queryKey: ["profile", profileId],
    queryFn: () => getProfile(profileId),
    enabled: !!profileId,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["profile", profileId] });
    qc.invalidateQueries({ queryKey: ["profiles"] });
    qc.invalidateQueries({ queryKey: ["profile-stats"] });
  };
  const onError = (e: unknown) =>
    push({ tone: "danger", title: "Update failed", body: String(e) });

  const setStatus = useMutation({
    mutationFn: (status: ProfileStatus) => setProfileStatus(profileId, status),
    onSuccess: invalidate,
    onError,
  });
  const saveSummary = useMutation({
    mutationFn: (summary: string) => updateProfile(profileId, { summary }),
    onSuccess: () => {
      invalidate();
      push({ tone: "success", title: "Summary saved" });
    },
    onError,
  });
  const saveTags = useMutation({
    mutationFn: (tags: string[]) => updateProfile(profileId, { tags }),
    onSuccess: invalidate,
    onError,
  });
  const putAttr = useMutation({
    mutationFn: (kv: { key: string; value: string }) =>
      putProfileAttribute(profileId, kv.key, kv.value),
    onSuccess: invalidate,
    onError,
  });
  const dropAttr = useMutation({
    mutationFn: (key: string) => deleteProfileAttribute(profileId, key),
    onSuccess: invalidate,
    onError,
  });
  const remove = useMutation({
    mutationFn: () => deleteProfile(profileId),
    onSuccess: () => {
      push({ tone: "info", title: "Profile deleted" });
      navigate("/profiles");
      invalidate();
    },
    onError,
  });

  if (profile.isLoading) {
    return <div className="p-8 text-center text-[var(--color-text-faint)]">Loading...</div>;
  }
  if (profile.isError || !profile.data) {
    return (
      <div className="p-8 text-center text-sm text-[var(--color-danger)]">
        {String(profile.error ?? "Profile not found")}
      </div>
    );
  }
  const p = profile.data;

  return (
    <div className="space-y-6">
      <PageHeader
        back={{ to: "/profiles", label: "Profiles" }}
        eyebrow={
          <span className="flex items-center gap-2">
            <span className="rounded border border-[var(--color-border)] px-1.5 py-0.5 font-mono text-[10px]">
              {p.id}
            </span>
            <Badge tone={profileStatusTone(p.status)}>{p.status}</Badge>
          </span>
        }
        title={p.name}
        lede={`Created ${p.created_at ? new Date(p.created_at).toLocaleString() : "-"}, updated ${
          p.updated_at ? new Date(p.updated_at).toLocaleString() : "-"
        }`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {STATUS_ACTIONS[p.status].map(({ to, label, icon: Icon }) => (
              <Button
                key={to}
                size="sm"
                variant={to === "published" ? "primary" : "secondary"}
                onClick={() => setStatus.mutate(to)}
                disabled={setStatus.isPending}
              >
                <Icon size={12} /> {label}
              </Button>
            ))}
            <Button
              size="sm"
              variant="danger"
              onClick={() => remove.mutate()}
              disabled={remove.isPending}
            >
              <Trash2 size={12} /> Delete
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <SummaryCard profile={p} onSave={(s) => saveSummary.mutate(s)} saving={saveSummary.isPending} />
        <TagsCard profile={p} onSave={(tags) => saveTags.mutate(tags)} />
      </div>

      <AttributesCard
        profile={p}
        onPut={(key, value) => putAttr.mutate({ key, value })}
        onDrop={(key) => dropAttr.mutate(key)}
        busy={putAttr.isPending || dropAttr.isPending}
      />
    </div>
  );
}

// --- Detail sub-cards ----------------------------------------------------

function SummaryCard({
  profile,
  onSave,
  saving,
}: {
  profile: Profile;
  onSave: (summary: string) => void;
  saving: boolean;
}) {
  const [draft, setDraft] = useState(profile.summary);
  useEffect(() => setDraft(profile.summary), [profile.id, profile.summary]);
  const dirty = draft !== profile.summary;

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium">Summary</h2>
        {dirty && (
          <Button size="sm" variant="primary" onClick={() => onSave(draft)} disabled={saving}>
            {saving ? <Loader2 size={12} className="animate-spin" /> : null} Save
          </Button>
        )}
      </div>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={5}
        placeholder="What is this profile about?"
        className="w-full resize-y rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] p-3 text-sm leading-relaxed outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
      />
    </Card>
  );
}

function TagsCard({ profile, onSave }: { profile: Profile; onSave: (tags: string[]) => void }) {
  const [draft, setDraft] = useState("");

  const add = () => {
    const tag = draft.trim();
    if (!tag) return;
    setDraft("");
    onSave([...profile.tags, tag]);
  };

  return (
    <Card className="p-5">
      <h2 className="mb-3 text-sm font-medium">Tags</h2>
      <div className="flex flex-wrap items-center gap-1.5">
        {profile.tags.length === 0 && (
          <span className="text-xs text-[var(--color-text-faint)]">No tags yet.</span>
        )}
        {profile.tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--color-accent-border)] bg-[var(--color-accent-bg)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-accent)]"
          >
            {tag}
            <button
              type="button"
              aria-label={`Remove tag ${tag}`}
              onClick={() => onSave(profile.tags.filter((t) => t !== tag))}
              className="hover:opacity-70"
            >
              <X size={11} />
            </button>
          </span>
        ))}
      </div>
      <form
        className="mt-3 flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          add();
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add a tag..."
          className="h-8 flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
        />
        <Button type="submit" size="sm" disabled={!draft.trim()}>
          <Plus size={12} /> Add
        </Button>
      </form>
    </Card>
  );
}

function AttributesCard({
  profile,
  onPut,
  onDrop,
  busy,
}: {
  profile: Profile;
  onPut: (key: string, value: string) => void;
  onDrop: (key: string) => void;
  busy: boolean;
}) {
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const entries = Object.entries(profile.attributes);

  const add = () => {
    if (!key.trim()) return;
    onPut(key.trim(), value);
    setKey("");
    setValue("");
  };

  return (
    <Card className="p-0 overflow-hidden">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3.5">
        <h2 className="text-sm font-medium">Attributes</h2>
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-faint)]">
          {entries.length} fact{entries.length === 1 ? "" : "s"}
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="px-5 py-6 text-center text-xs text-[var(--color-text-muted)]">
          Nothing added yet - attach the first fact below.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody>
              {entries.map(([k, v]) => (
                <tr
                  key={k}
                  className="border-b border-[var(--color-border)] transition-colors last:border-0 hover:bg-white/[0.02]"
                >
                  <td className="w-[220px] px-5 py-2.5 font-mono text-xs text-[var(--color-text-muted)]">
                    {k}
                  </td>
                  <td className="px-4 py-2.5">{v}</td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      type="button"
                      aria-label={`Remove attribute ${k}`}
                      onClick={() => onDrop(k)}
                      disabled={busy}
                      className="text-[var(--color-text-faint)] transition-colors hover:text-[var(--color-danger)]"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form
        className="flex flex-col gap-2 border-t border-[var(--color-border)] p-4 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          add();
        }}
      >
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="Key (e.g. region)"
          className="h-9 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] px-3 font-mono text-xs outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)] sm:w-[220px]"
        />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Value"
          className="h-9 flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
        />
        <Button type="submit" size="sm" disabled={busy || !key.trim()}>
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />} Add fact
        </Button>
      </form>
    </Card>
  );
}
