/**
 * Items - the canonical list page (BLUEPRINT.md §4): PageHeader -> StatKpi
 * row -> SearchInput -> table-in-Card with Pagination footer. Polling keeps
 * the list live (5s); mutations invalidate an explicit key fan-out.
 * Copy this composition for every list page you add, then delete Items.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { CheckCircle2, CircleDashed, Loader2, Plus, Trash2, XCircle } from "lucide-react";

import { Badge, itemStateTone } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchInput } from "@/components/SearchInput";
import { StatKpi } from "@/components/StatKpi";
import { useToasts } from "@/components/Toast";
import {
  createItem,
  deleteItem,
  getItemStats,
  listItems,
  setItemState,
  type Item,
  type ItemState,
} from "@/lib/api";

const NEXT_STATE: Record<ItemState, ItemState> = {
  pending: "running",
  running: "done",
  done: "pending",
  failed: "pending",
};

export function ItemsPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [newTitle, setNewTitle] = useState("");
  const { push } = useToasts();
  const qc = useQueryClient();

  const stats = useQuery({ queryKey: ["item-stats"], queryFn: getItemStats, refetchInterval: 5_000 });
  const items = useQuery({
    queryKey: ["items", q || "all", page, pageSize],
    queryFn: () => listItems({ q: q || undefined, limit: pageSize, offset: (page - 1) * pageSize }),
    refetchInterval: 5_000,
    placeholderData: (prev) => prev,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["items"] });
    qc.invalidateQueries({ queryKey: ["item-stats"] });
    qc.invalidateQueries({ queryKey: ["palette-items"] });
  };

  const create = useMutation({
    mutationFn: (title: string) => createItem({ title }),
    onSuccess: (item) => {
      setNewTitle("");
      invalidate();
      push({ tone: "success", title: "Item created", body: item.title });
    },
    onError: (e) => push({ tone: "danger", title: "Create failed", body: String(e) }),
  });

  const advance = useMutation({
    mutationFn: (item: Item) => setItemState(item.id, NEXT_STATE[item.state]),
    onSuccess: invalidate,
    onError: (e) => push({ tone: "danger", title: "Update failed", body: String(e) }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteItem(id),
    onSuccess: () => {
      invalidate();
      push({ tone: "info", title: "Item deleted" });
    },
    onError: (e) => push({ tone: "danger", title: "Delete failed", body: String(e) }),
  });

  const counts = stats.data?.counts;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="example resource"
        title="Items"
        lede="The walking skeleton's end-to-end resource: migration -> repository -> route -> this page. Replace it with your first real entity and keep the composition."
        actions={
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (newTitle.trim()) create.mutate(newTitle.trim());
            }}
          >
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="New item title..."
              className="h-9 w-52 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-elev1)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
            />
            <Button type="submit" variant="primary" size="sm" disabled={create.isPending || !newTitle.trim()}>
              {create.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              Add
            </Button>
          </form>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 2xl:gap-4">
        <StatKpi label="Pending" value={counts?.pending ?? "-"} tone="muted" icon={CircleDashed} />
        <StatKpi label="Running" value={counts?.running ?? "-"} tone="info" icon={Loader2} />
        <StatKpi label="Done" value={counts?.done ?? "-"} tone="success" icon={CheckCircle2} />
        <StatKpi label="Failed" value={counts?.failed ?? "-"} tone="danger" icon={XCircle} />
      </div>

      <SearchInput
        value={q}
        onChange={(v) => {
          setQ(v);
          setPage(1);
        }}
        placeholder="Filter by title..."
        className="max-w-sm"
      />

      <section>
        <Card className="p-0 overflow-hidden">
          {items.isLoading ? (
            <div className="p-8 text-center text-[var(--color-text-faint)]">Loading...</div>
          ) : items.isError ? (
            <div className="p-8 text-center text-sm text-[var(--color-danger)]">
              {String(items.error)}
            </div>
          ) : items.data && items.data.entries.length === 0 ? (
            <div className="p-12 text-center">
              <CircleDashed size={24} className="mx-auto text-[var(--color-text-faint)]" />
              <p className="mt-3 text-sm font-medium">No items yet</p>
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
                    <th className="px-4 py-2.5 text-left font-medium">Item</th>
                    <th className="hidden px-4 py-2.5 text-left font-medium md:table-cell">ID</th>
                    <th className="px-4 py-2.5 text-left font-medium">State</th>
                    <th className="hidden px-4 py-2.5 text-right font-medium sm:table-cell">Updated</th>
                    <th className="px-4 py-2.5 text-right font-medium" aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {items.data?.entries.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-[var(--color-border)] transition-colors last:border-0 hover:bg-white/[0.02]"
                    >
                      <td className="px-4 py-3">{item.title}</td>
                      <td className="hidden px-4 py-3 font-mono text-xs text-[var(--color-text-muted)] md:table-cell">
                        {item.id}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => advance.mutate(item)}
                          title={`Advance to ${NEXT_STATE[item.state]}`}
                          className="cursor-pointer"
                        >
                          <Badge tone={itemStateTone(item.state)}>
                            {item.state === "running" && (
                              <Loader2 size={11} className="animate-spin" />
                            )}
                            {item.state}
                          </Badge>
                        </button>
                      </td>
                      <td className="hidden px-4 py-3 text-right text-xs text-[var(--color-text-muted)] tabular-nums sm:table-cell">
                        {item.updated_at ? new Date(item.updated_at).toLocaleString() : "-"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          aria-label={`Delete ${item.title}`}
                          onClick={() => remove.mutate(item.id)}
                          className="text-[var(--color-text-faint)] transition-colors hover:text-[var(--color-danger)]"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={items.data?.total ?? 0}
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
