/** Small shared helpers (no deps). */

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function shortHash(h: string | null | undefined, n = 12): string {
  return h && h.length > n ? `${h.slice(0, n)}…` : h || "—";
}

export function fmtBytes(size?: number | null): string {
  if (!size) return "—";
  let v = size;
  for (const u of ["B", "KB", "MB", "GB"]) {
    if (v < 1024) return `${v.toFixed(v < 10 && u !== "B" ? 1 : 0)} ${u}`;
    v /= 1024;
  }
  return `${v.toFixed(1)} GB`;
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Nice ceiling for a chart axis (1/2/5 × 10^n). */
export function niceCeil(v: number): number {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 5, 10]) {
    if (v <= m * p) return m * p;
  }
  return 10 * p;
}
