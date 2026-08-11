/**
 * UserMenu - the avatar chip on the far right of the top bar and its
 * dropdown: identity header, theme switcher, quick links, a sign-out
 * extension point, and a model footer. Identity comes from
 * GET /api/users/me (resolved from the Users directory; swap that
 * endpoint's logic for your session lookup when you wire real auth).
 */
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  ChevronDown,
  LogOut,
  Monitor,
  Moon,
  Sun,
  Users,
} from "lucide-react";

import { useToasts } from "@/components/Toast";
import { getMe } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useTheme, type ThemeMode } from "@/lib/ThemeContext";

const REPO_URL = "https://github.com/imran4z/app-shell";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const { push } = useToasts();

  const me = useQuery({ queryKey: ["me"], queryFn: getMe, staleTime: 60_000 });
  const user = me.data?.user ?? null;
  const name = user?.name ?? "Guest";
  const active = user?.status === "active";

  // Click-outside and Escape both close the menu.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(false);
      }
    };
    window.addEventListener("mousedown", onClick);
    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("mousedown", onClick);
      window.removeEventListener("keydown", onKey, true);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="User menu"
        className={cn(
          "flex h-9 items-center gap-2 rounded-full border border-[var(--color-border)] py-1 pl-1 pr-2.5",
          "text-sm transition-colors hover-wash",
          open && "border-[var(--color-border-strong)] bg-white/[0.04]",
        )}
      >
        <span className="relative">
          <span className="grid h-7 w-7 place-items-center rounded-full border border-[var(--color-accent-border)] bg-[var(--color-accent-bg)] font-mono text-[10px] text-[var(--color-accent)]">
            {initials(name)}
          </span>
          {active && (
            <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border border-[var(--color-canvas)] bg-[var(--color-live)]" />
          )}
        </span>
        <span className="hidden max-w-[120px] truncate font-medium sm:inline">
          {name.split(" ")[0]?.toLowerCase()}
        </span>
        <ChevronDown
          size={12}
          className={cn("text-[var(--color-text-faint)] transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-11 z-50 w-72 overflow-hidden rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-canvas-elev2)] shadow-xl"
        >
          {/* Identity */}
          <div className="flex items-center gap-3 border-b border-[var(--color-border)] px-4 py-3.5">
            <span className="relative">
              <span className="grid h-9 w-9 place-items-center rounded-full border border-[var(--color-accent-border)] bg-[var(--color-accent-bg)] font-mono text-[11px] text-[var(--color-accent)]">
                {initials(name)}
              </span>
              {active && (
                <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border border-[var(--color-canvas-elev2)] bg-[var(--color-live)]" />
              )}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{name}</p>
              <p className="truncate text-xs text-[var(--color-text-muted)]">
                {user ? user.email : "no users yet - run `just seed`"}
              </p>
            </div>
          </div>

          {/* Theme */}
          <div className="border-b border-[var(--color-border)] px-4 py-3">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-faint)]">
              Theme
            </p>
            <ThemeSwitch />
          </div>

          {/* Links */}
          <div className="border-b border-[var(--color-border)] py-1.5">
            <MenuLink to="/users" icon={Users} onPick={() => setOpen(false)}>
              Users directory
            </MenuLink>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              role="menuitem"
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-white/[0.04] hover:text-[var(--color-text)]"
            >
              <BookOpen size={14} /> Docs
            </a>
          </div>

          {/* Sign out: an extension point, not a fake. */}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              push({
                tone: "info",
                title: "No auth wired yet",
                body: "This is the sign-out extension point. See the /api/users/me route and CLAUDE.md.",
              });
            }}
            className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm text-[var(--color-danger)] transition-colors hover:bg-[var(--color-danger)]/10"
          >
            <LogOut size={14} />
            <span>
              Sign out
              <span className="block text-[11px] text-[var(--color-text-faint)]">
                wire your auth flow here
              </span>
            </span>
          </button>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-[var(--color-border)] bg-[var(--color-canvas)]/40 px-4 py-2">
            <span className="text-[11px] text-[var(--color-text-faint)]">Model</span>
            <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
              {me.data?.model ?? "..."}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function MenuLink({
  to,
  icon: Icon,
  onPick,
  children,
}: {
  to: string;
  icon: typeof Users;
  onPick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      role="menuitem"
      onClick={onPick}
      className="flex items-center gap-2.5 px-4 py-2 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-white/[0.04] hover:text-[var(--color-text)]"
    >
      <Icon size={14} /> {children}
    </Link>
  );
}

function ThemeSwitch() {
  const { mode, setMode } = useTheme();
  const options: { value: ThemeMode; icon: typeof Sun; label: string }[] = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "system", icon: Monitor, label: "System" },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="grid grid-cols-3 gap-1 rounded-lg border border-[var(--color-border)] p-1"
    >
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={mode === value}
          onClick={() => setMode(value)}
          className={cn(
            "flex h-7 items-center justify-center gap-1.5 rounded-md text-xs transition-colors",
            mode === value
              ? "bg-[var(--color-accent-bg)] font-medium text-[var(--color-accent)]"
              : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]",
          )}
        >
          <Icon size={12} /> {label}
        </button>
      ))}
    </div>
  );
}
