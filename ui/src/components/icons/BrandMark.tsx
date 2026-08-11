/**
 * Brand icon module (BLUEPRINT.md §3 Icons). One bespoke mark, stroking
 * currentColor, plus the TONE map from domain states to CSS vars - the
 * single source of truth for state -> color across the UI.
 */

export function BrandMark({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {/* Abstract "shell" mark: an open frame with a spark inside. */}
      <path d="M4 8V6a2 2 0 0 1 2-2h2" />
      <path d="M16 4h2a2 2 0 0 1 2 2v2" />
      <path d="M20 16v2a2 2 0 0 1-2 2h-2" />
      <path d="M8 20H6a2 2 0 0 1-2-2v-2" />
      <path d="M12 8v3l2.5 2.5" />
      <circle cx="12" cy="12" r="0.5" fill="currentColor" />
    </svg>
  );
}

/** Domain-state -> CSS color var. Extend when you add states. */
export const TONE: Record<string, string> = {
  pending: "var(--color-text-faint)",
  running: "var(--color-info)",
  done: "var(--color-success)",
  failed: "var(--color-danger)",
};
