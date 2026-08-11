import type { ReactNode } from "react";

/** Tone maps to a `.badge-<tone>` class; pass any of the CSS-defined tones. */
export function Badge({ tone = "status", children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
