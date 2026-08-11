/**
 * StatKpi - the gradient metric tile from the design-rework prototype
 * (`Kpi` + `barGrad`). A single number with a faint tonal wash, a small
 * rounded icon tile, an optional sparkline, and the signature 3px
 * tone-driven bottom accent bar.
 *
 * This is the summary-row primitive: the stat row that tops every list
 * page and sits under every detail-page header. It's deliberately
 * distinct from the richer per-entity cards (ProfileKpiCard / PlanKpiCard)
 * which carry their own status pill + reveal CTA.
 */
import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/cn";

export type StatTone =
  | "accent"
  | "info"
  | "signal"
  | "live"
  | "warning"
  | "partner"
  | "danger"
  | "success"
  | "muted";

/** css color value + tint background per tone. */
const TONE: Record<StatTone, { c: string; bg: string }> = {
  accent:  { c: "var(--color-accent)",     bg: "var(--color-accent-bg)" },
  info:    { c: "var(--color-info)",       bg: "var(--color-info-bg)" },
  signal:  { c: "var(--color-signal)",     bg: "var(--color-signal-bg)" },
  live:    { c: "var(--color-live)",       bg: "var(--color-live-bg)" },
  warning: { c: "var(--color-warning)",    bg: "var(--color-warning-bg)" },
  partner: { c: "var(--color-partner)",    bg: "var(--color-partner-bg)" },
  danger:  { c: "var(--color-danger)",     bg: "var(--color-danger-bg)" },
  success: { c: "var(--color-success)",    bg: "var(--color-success-bg)" },
  muted:   { c: "var(--color-text-faint)", bg: "rgba(180,200,230,0.06)" },
};

/** Bottom accent-bar gradient by tone (matches the shipped card style). */
export function barGrad(tone: StatTone): string {
  switch (tone) {
    case "partner":
    case "warning":
      return "linear-gradient(90deg, var(--color-partner), var(--color-warning))";
    case "danger":
      return "var(--color-danger)";
    case "info":
      return "linear-gradient(90deg, var(--color-info), var(--color-signal))";
    case "muted":
      return "var(--color-border-strong)";
    default:
      return "linear-gradient(90deg, var(--color-accent), var(--color-signal))";
  }
}

export interface StatKpiProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ComponentType<{ size?: number; className?: string }>;
  tone?: StatTone;
  spark?: number[];
  onClick?: () => void;
  selected?: boolean;
  className?: string;
}

export function StatKpi({
  label,
  value,
  hint,
  icon: Icon,
  tone = "accent",
  spark,
  onClick,
  selected,
  className,
}: StatKpiProps) {
  const { c, bg } = TONE[tone];
  const Wrapper = onClick ? "button" : "div";

  return (
    <Wrapper
      {...(onClick ? { type: "button" as const, onClick } : {})}
      className={cn(
        "relative isolate flex w-full flex-col gap-2.5 overflow-hidden rounded-[var(--radius)] border border-[var(--color-border)] px-[18px] pt-4 pb-[18px] text-left transition-colors",
        onClick && "cursor-pointer hover:border-[var(--color-border-strong)]",
        className,
      )}
      style={{
        background: `linear-gradient(150deg, color-mix(in srgb, ${c} 9%, var(--color-canvas-elev1)), var(--color-canvas-elev1) 62%)`,
        outline: selected ? `1px solid ${c}` : undefined,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-[var(--color-text-faint)]">
          {label}
        </span>
        {Icon && (
          <span
            className="grid h-7 w-7 shrink-0 place-items-center rounded-lg"
            style={{
              color: c,
              background: bg,
              border: `1px solid color-mix(in srgb, ${c} 30%, transparent)`,
            }}
          >
            <Icon size={15} />
          </span>
        )}
      </div>
      <div className="flex items-end justify-between gap-2">
        <span className="text-[28px] font-semibold tracking-[-0.02em] tabular-nums leading-none text-[var(--color-text)]">
          {value}
        </span>
        {spark && spark.length > 1 && <Spark data={spark} color={c} />}
      </div>
      {hint && (
        <div className="text-[11px] text-[var(--color-text-faint)]">{hint}</div>
      )}
      <span
        aria-hidden="true"
        className="absolute inset-x-0 bottom-0 h-[3px]"
        style={{ background: barGrad(tone) }}
      />
    </Wrapper>
  );
}

function Spark({
  data,
  color,
  w = 56,
  h = 22,
}: {
  data: number[];
  color: string;
  w?: number;
  h?: number;
}) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const rng = max - min || 1;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / rng) * (h - 3) - 1.5}`)
    .join(" ");
  return (
    <svg
      width={w}
      height={h}
      className="block shrink-0 overflow-visible"
      aria-hidden="true"
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.6"
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity="0.9"
      />
    </svg>
  );
}
