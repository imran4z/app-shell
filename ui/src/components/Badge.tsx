import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger" | "accent";
// Internal alias kept so existing call sites that reference `Tone` via
// the module's private surface still compile.
type Tone = BadgeTone;

const TONES: Record<Tone, string> = {
  neutral: "bg-white/[0.06] text-[var(--color-text-muted)] border-[var(--color-border)]",
  info:    "bg-[var(--color-info)]/12 text-[var(--color-info)] border-[var(--color-info)]/30",
  success: "bg-[var(--color-success)]/12 text-[var(--color-success)] border-[var(--color-success)]/30",
  warning: "bg-[var(--color-warning)]/12 text-[var(--color-warning)] border-[var(--color-warning)]/30",
  danger:  "bg-[var(--color-danger)]/12 text-[var(--color-danger)] border-[var(--color-danger)]/30",
  accent:  "bg-[var(--color-accent-bg)] text-[var(--color-accent)] border-[var(--color-accent-border)]",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Map a user account status to a tone. */
export function userStatusTone(status: string): Tone {
  switch (status) {
    case "active":   return "success";
    case "invited":  return "info";
    case "disabled": return "neutral";
    default:         return "neutral";
  }
}

/** Map a profile status to a tone. */
export function profileStatusTone(status: string): Tone {
  switch (status) {
    case "draft":     return "neutral";
    case "published": return "success";
    case "archived":  return "warning";
    default:          return "neutral";
  }
}

/** Map an item state to a tone. Centralize every domain-state -> tone map
 *  in one exported function like this - never inline per-page. */
export function itemStateTone(state: string): Tone {
  switch (state) {
    case "pending": return "neutral";
    case "running": return "info";
    case "done":    return "success";
    case "failed":  return "danger";
    default:        return "neutral";
  }
}
