/**
 * ⌘K palette (cmdk). Groups: Pages, then recent items - nothing fetches
 * until open (`enabled: open`). Solid elev2 panel, NOT glass (§3).
 */
import { useQuery } from "@tanstack/react-query";
import { Command } from "cmdk";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Boxes, Contact, LayoutDashboard, Users } from "lucide-react";

import { listItems } from "@/lib/api";
import { TONE } from "@/components/icons/BrandMark";

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();

  const { data } = useQuery({
    queryKey: ["palette-items"],
    queryFn: () => listItems({ limit: 6 }),
    enabled: open,
    staleTime: 10_000,
  });

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const go = (to: string) => {
    onClose();
    navigate(to);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-center bg-black/50 pt-32 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Command palette">
        <Command
          className="w-[640px] max-w-[92vw] overflow-hidden rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-canvas-elev2)] shadow-2xl"
          label="Command palette"
        >
          <Command.Input
            autoFocus
            placeholder="Jump to..."
            className="w-full border-b border-[var(--color-border)] bg-transparent px-4 py-3 text-sm outline-none placeholder:text-[var(--color-text-faint)]"
          />
          <Command.List className="max-h-[320px] overflow-y-auto p-2">
            <Command.Empty className="px-3 py-6 text-center text-sm text-[var(--color-text-faint)]">
              No results.
            </Command.Empty>

            <Command.Group
              heading="Pages"
              className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-[var(--color-text-faint)]"
            >
              <PaletteItem onSelect={() => go("/")}>
                <LayoutDashboard size={14} /> Dashboard
              </PaletteItem>
              <PaletteItem onSelect={() => go("/items")}>
                <Boxes size={14} /> Items
              </PaletteItem>
              <PaletteItem onSelect={() => go("/profiles")}>
                <Contact size={14} /> Profiles
              </PaletteItem>
              <PaletteItem onSelect={() => go("/users")}>
                <Users size={14} /> Users
              </PaletteItem>
            </Command.Group>

            {data && data.entries.length > 0 && (
              <Command.Group
                heading="Recent items"
                className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-[var(--color-text-faint)]"
              >
                {data.entries.map((item) => (
                  <PaletteItem key={item.id} onSelect={() => go("/items")}>
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ background: TONE[item.state] ?? "var(--color-text-faint)" }}
                    />
                    <span className="truncate">{item.title}</span>
                    <span className="ml-auto font-mono text-xs text-[var(--color-text-faint)]">
                      {item.state}
                    </span>
                  </PaletteItem>
                ))}
              </Command.Group>
            )}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}

function PaletteItem({
  children,
  onSelect,
}: {
  children: React.ReactNode;
  onSelect: () => void;
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-sm text-[var(--color-text-muted)] data-[selected=true]:bg-[var(--color-accent-bg)] data-[selected=true]:text-[var(--color-accent)] data-[selected=true]:ring-1 data-[selected=true]:ring-[var(--color-accent-border)]"
    >
      {children}
    </Command.Item>
  );
}
