import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/cn";

/** Glass card primitive, the canvas-on-canvas surface used everywhere. */
export function Card({
  children,
  className,
  hover,
  style,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  style?: CSSProperties;
}) {
  return (
    <div
      style={style}
      className={cn(
        "glass rounded-xl",
        hover && "transition-all duration-200 hover:border-[var(--color-border-strong)] hover:bg-white/[0.04]",
        className,
      )}
    >
      {children}
    </div>
  );
}
