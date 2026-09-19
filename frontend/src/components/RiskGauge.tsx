/** Clean, minimal RiskGauge */
export function RiskGauge({ score, size = 160 }: { score: number; size?: number }) {
  const pct = Math.min(Math.max(score, 0), 100) / 100;
  const r = 54;
  const cx = 80;
  const cy = 80;
  const circ = 2 * Math.PI * r;
  const arc = pct * circ * 0.75; // 270 degree gauge
  const gap = circ - arc;

  const color =
    pct >= 0.7 ? "var(--rose)" :
    pct >= 0.4 ? "var(--amber)" :
    "var(--emerald)";

  const label =
    pct >= 0.7 ? "HIGH RISK" :
    pct >= 0.4 ? "MEDIUM RISK" :
    "LOW RISK";

  return (
    <div
      className="risk-gauge"
      role="meter"
      aria-valuenow={Math.round(score)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Risk score: ${Math.round(score)} out of 100, ${label}`}
    >
      <div style={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} viewBox="0 0 160 160" aria-hidden="true">
          {/* Track */}
          <circle
            r={r} cx={cx} cy={cy}
            fill="none"
            stroke="var(--bg-3)"
            strokeWidth={12}
            strokeDasharray={`${circ * 0.75} ${circ * 0.25}`}
            strokeDashoffset={circ * 0.125}
            transform={`rotate(135 ${cx} ${cy})`}
            strokeLinecap="round"
          />
          {/* Fill */}
          <circle
            r={r} cx={cx} cy={cy}
            fill="none"
            stroke={color}
            strokeWidth={12}
            strokeDasharray={`${arc} ${gap + circ * 0.25}`}
            strokeDashoffset={circ * 0.125}
            transform={`rotate(135 ${cx} ${cy})`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1), stroke 0.4s" }}
          />
        </svg>
        {/* Center text */}
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
        }}>
          <span className="risk-score-big" style={{ color }}>{Math.round(score)}</span>
          <span className="risk-label">{label}</span>
        </div>
      </div>
    </div>
  );
}
