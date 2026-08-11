/**
 * PageHeader - the one canonical way every page opens.
 *
 * Ports the design-rework prototype's `PageHead`: an optional back link,
 * a mono uppercase eyebrow, a 28px display title with an optional
 * accent->signal gradient `em` span, an optional lede, and a right-aligned
 * actions cluster. Adopting this everywhere kills the three ad-hoc header
 * patterns that made the app drift (Dashboard's 32px H1, Plans' 28px H1,
 * Profiles' plain 24px H1).
 */
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { cn } from "@/lib/cn";

export interface PageHeaderProps {
  /** Mono uppercase kicker above the title. May carry an inline id/state. */
  eyebrow?: ReactNode;
  /** The display title (28px / 600 / -0.02em). */
  title: ReactNode;
  /** Optional gradient span appended to the title (the "marquee" word). */
  em?: ReactNode;
  /** Optional supporting copy under the title. Pass a node for italics. */
  lede?: ReactNode;
  /** Right-aligned action cluster (buttons). */
  actions?: ReactNode;
  /** Back link rendered above the eyebrow. */
  back?: { to: string; label: string };
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  em,
  lede,
  actions,
  back,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-end justify-between gap-6 flex-wrap",
        className,
      )}
    >
      <div className="min-w-0">
        {back && (
          <Link
            to={back.to}
            className="inline-flex items-center gap-1 mb-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
          >
            <ArrowLeft size={14} /> {back.label}
          </Link>
        )}
        {eyebrow && (
          <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-[var(--color-text-faint)]">
            {eyebrow}
          </div>
        )}
        <h1
          className={cn(
            "text-[28px] font-semibold tracking-[-0.02em] leading-tight text-[var(--color-text)]",
            eyebrow && "mt-2",
          )}
        >
          {title}
          {em && (
            <>
              {" "}
              <span className="h1-display">{em}</span>
            </>
          )}
        </h1>
        {lede && (
          <p className="mt-2 max-w-[64ch] text-sm leading-relaxed text-[var(--color-text-muted)]">
            {lede}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2.5">
          {actions}
        </div>
      )}
    </div>
  );
}
