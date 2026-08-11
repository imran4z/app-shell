/**
 * Dashboard - the one page allowed to deviate from the canonical list
 * composition: centered hero with gradient display type, then content
 * bands separated by border-t (BLUEPRINT.md §4).
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Boxes, HeartPulse } from "lucide-react";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { getHealth, getItemStats } from "@/lib/api";

export function Dashboard() {
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 15_000 });
  const stats = useQuery({ queryKey: ["item-stats"], queryFn: getItemStats, refetchInterval: 10_000 });

  return (
    <div>
      {/* Hero band */}
      <section className="py-10 text-center sm:py-16">
        <p className="text-[11px] font-mono uppercase tracking-[0.08em] text-[var(--color-text-faint)]">
          clone, describe, build
        </p>
        <h1 className="mt-3 text-[34px] font-semibold tracking-[-0.02em] sm:text-[46px]">
          Your app, <span className="h1-display">already plumbed</span>
        </h1>
        <p className="mx-auto mt-3 max-w-[64ch] text-sm leading-relaxed text-[var(--color-text-muted)]">
          FastAPI + Postgres + this design system, wired end to end. Describe your app in
          APP_SPEC.md, hand it to an agent with BLUEPRINT.md, and replace the example Items
          resource with your real domain.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link to="/items">
            <Button variant="primary">
              Explore the example resource <ArrowRight size={14} />
            </Button>
          </Link>
        </div>
      </section>

      {/* Status band */}
      <section className="mt-12 border-t border-[var(--color-border)] pt-9">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-lg font-medium">System</h2>
          <span className="text-xs text-[var(--color-text-muted)]">polls every 15s</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 2xl:gap-4">
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-8 w-8 place-items-center rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-accent-bg)] text-[var(--color-accent)]">
                <HeartPulse size={15} />
              </span>
              <div>
                <p className="text-sm font-medium">API &amp; dependencies</p>
                <p className="text-xs text-[var(--color-text-muted)]">/api/health</p>
              </div>
              <div className="ml-auto flex items-center gap-2">
                {health.isLoading && (
                  <span className="text-xs text-[var(--color-text-faint)]">Loading...</span>
                )}
                {health.isError && <Badge tone="danger">unreachable</Badge>}
                {health.data &&
                  Object.entries(health.data.services).map(([name, status]) => (
                    <Badge key={name} tone={status === "up" ? "success" : "danger"}>
                      {name}: {status}
                    </Badge>
                  ))}
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-8 w-8 place-items-center rounded-lg border border-[var(--color-signal)]/30 bg-[var(--color-signal-bg)] text-[var(--color-signal)]">
                <Boxes size={15} />
              </span>
              <div>
                <p className="text-sm font-medium">Items</p>
                <p className="text-xs text-[var(--color-text-muted)]">example domain entity</p>
              </div>
              <div className="ml-auto">
                {stats.data ? (
                  <span className="text-[28px] font-semibold leading-none tracking-[-0.02em] tabular-nums">
                    {stats.data.total}
                  </span>
                ) : (
                  <span className="text-xs text-[var(--color-text-faint)]">
                    {stats.isError ? "-" : "Loading..."}
                  </span>
                )}
              </div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
