export function StatCard({
  label,
  value,
  hint,
  accent = false,
  alert = false,
}: {
  label: string;
  value: string | number;
  hint?: string;
  accent?: boolean;
  alert?: boolean;
}) {
  const cls = `stat-value ${accent ? "stat-accent" : ""} ${alert ? "stat-alert" : ""}`;
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className={cls}>{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}
