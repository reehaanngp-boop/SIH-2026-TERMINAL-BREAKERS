export function StatCard({
  label,
  value,
  accent,
  sub,
  hint: _hint,
  alert: _alert,
}: {
  label: string;
  value: number | string;
  accent?: boolean;
  sub?: string;
  hint?: string;
  alert?: boolean;
}) {
  return (
    <div className={`stat-card${accent ? " accent" : ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="text-sm text-muted" style={{ marginTop: 4 }}>{sub}</div>}
    </div>
  );
}
