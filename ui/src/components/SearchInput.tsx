/**
 * SearchInput - a small, reusable filter box for list pages. Controlled
 * (value + onChange), with a leading magnifier and a clear (✕) button.
 * Purely client-side; the page owns the filtering.
 */
import { Search, X } from "lucide-react";

import { cn } from "@/lib/cn";

export function SearchInput({
  value,
  onChange,
  placeholder = "Search...",
  className,
  autoFocus = false,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
}) {
  return (
    <div className={cn("relative", className)}>
      <Search
        size={15}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]"
      />
      <input
        type="text"
        value={value}
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Escape" && value) { e.stopPropagation(); onChange(""); } }}
        placeholder={placeholder}
        className={cn(
          "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-elev1)]",
          "py-2 pl-9 pr-9 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-faint)]",
          "outline-none transition-colors focus:border-[var(--color-accent)]",
        )}
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Clear search"
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)] hover:text-[var(--color-text)]"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
