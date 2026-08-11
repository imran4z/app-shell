/**
 * App shell: topbar-only, no sidebar (BLUEPRINT.md §3). Sticky blurred
 * TopBar -> <main id="main-content"> -> CommandPalette -> mobile drawer.
 * The theme toggle lives in a small user menu on the right.
 */
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Boxes, Contact, LayoutDashboard, Menu, Monitor, Moon, Search, Sparkles, Sun, Users, X } from "lucide-react";

import { AssistantDrawer } from "@/components/Assistant";
import { CommandPalette } from "@/components/CommandPalette";
import { BrandMark } from "@/components/icons/BrandMark";
import { useAssistant } from "@/lib/AssistantContext";
import { cn } from "@/lib/cn";
import { useTheme, type ThemeMode } from "@/lib/ThemeContext";

export const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/items", label: "Items", icon: Boxes, end: false },
  { to: "/profiles", label: "Profiles", icon: Contact, end: false },
  { to: "/users", label: "Users", icon: Users, end: false },
];

function navItemClass(isActive: boolean) {
  return cn(
    "h-8 px-3 rounded-md text-sm flex items-center gap-2 transition-colors",
    isActive
      ? "bg-white/[0.06] text-[var(--color-text)]"
      : "text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-white/[0.03]",
  );
}

function ThemeMenu() {
  const { mode, setMode } = useTheme();
  const options: { value: ThemeMode; icon: typeof Sun; label: string }[] = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "system", icon: Monitor, label: "System" },
  ];
  return (
    <div
      className="flex items-center gap-0.5 rounded-md border border-[var(--color-border)] p-0.5"
      role="radiogroup"
      aria-label="Theme"
    >
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={mode === value}
          aria-label={`${label} theme`}
          onClick={() => setMode(value)}
          className={cn(
            "grid h-6 w-6 place-items-center rounded transition-colors",
            mode === value
              ? "bg-[var(--color-accent-bg)] text-[var(--color-accent)]"
              : "text-[var(--color-text-faint)] hover:text-[var(--color-text)]",
          )}
        >
          <Icon size={13} />
        </button>
      ))}
    </div>
  );
}

export function Layout() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const { toggleAssistant } = useAssistant();

  // ⌘K palette, ⌘J assistant - from anywhere.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
        e.preventDefault();
        toggleAssistant();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleAssistant]);

  // Drawer closes on route change; body scroll locked while open.
  useEffect(() => setDrawerOpen(false), [location.pathname]);
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [drawerOpen]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 border-b border-[var(--color-border)] backdrop-blur bg-[var(--color-canvas)]/75">
        <div className="flex h-16 w-full items-center gap-4 px-[clamp(1rem,2.5vw,4rem)]">
          <button
            type="button"
            aria-label="Open navigation"
            className="grid h-8 w-8 place-items-center rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text)] md:hidden"
            onClick={() => setDrawerOpen(true)}
          >
            <Menu size={16} />
          </button>

          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-[10px] border border-[var(--color-accent-border)] bg-[var(--color-accent-bg)] text-[var(--color-accent)]">
              <BrandMark size={18} />
            </span>
            <span className="whitespace-nowrap text-[16px] font-semibold tracking-tight">App Shell</span>
          </Link>

          <nav className="hidden md:flex gap-1" aria-label="Primary">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={({ isActive }) => navItemClass(isActive)}>
                <Icon size={14} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              aria-label="Search"
              aria-keyshortcuts="Meta+K"
              className="flex h-8 items-center gap-2 rounded-md border border-[var(--color-border)] px-2.5 text-sm text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)] hover-wash"
            >
              <Search size={13} />
              <span className="hidden sm:inline">Search</span>
              <kbd className="rounded border border-[var(--color-border)] bg-[var(--color-canvas)]/60 px-1.5 py-0.5 font-mono text-[10px]">
                ⌘K
              </kbd>
            </button>
            <button
              type="button"
              onClick={toggleAssistant}
              aria-label="Assistant"
              aria-keyshortcuts="Meta+J"
              className="flex h-8 items-center gap-2 rounded-md border border-[var(--color-border)] px-2.5 text-sm text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)] hover-wash"
            >
              <Sparkles size={13} />
              <span className="hidden sm:inline">Assistant</span>
              <kbd className="rounded border border-[var(--color-border)] bg-[var(--color-canvas)]/60 px-1.5 py-0.5 font-mono text-[10px]">
                ⌘J
              </kbd>
            </button>
            <ThemeMenu />
          </div>
        </div>
      </header>

      <main id="main-content" className="w-full flex-1 px-[clamp(1rem,2.5vw,4rem)] py-6 sm:py-8">
        <Outlet />
      </main>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <AssistantDrawer />

      {drawerOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="relative h-full w-72 max-w-[85vw] border-r border-[var(--color-border)] bg-[var(--color-canvas-elev1)] p-4">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm font-medium">Navigate</span>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setDrawerOpen(false)}
                className="grid h-7 w-7 place-items-center rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              >
                <X size={14} />
              </button>
            </div>
            <nav className="flex flex-col gap-1" aria-label="Mobile">
              {NAV.map(({ to, label, icon: Icon, end }) => (
                <NavLink key={to} to={to} end={end} className={({ isActive }) => navItemClass(isActive)}>
                  <Icon size={14} />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      )}
    </div>
  );
}
