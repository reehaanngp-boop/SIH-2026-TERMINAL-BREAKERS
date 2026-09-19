/** Clean, simple SVG charts */

interface DataPoint { label: string; value: number; color?: string; }

/* ---- Bar Chart ---- */
export function BarChart({ data }: { data: DataPoint[] }) {
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="bar-chart">
      {data.map((d) => (
        <div className="bar-row" key={d.label}>
          <div className="bar-meta">
            <span className="truncate" style={{ maxWidth: "70%" }}>{d.label}</span>
            <span style={{ color: "var(--text)", fontWeight: 600 }}>{d.value}</span>
          </div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: `${(d.value / max) * 100}%`,
                background: d.color || "var(--blue)",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- Donut Chart ---- */
export function DonutChart({
  data,
  centerLabel,
  size = 120,
}: {
  data: DataPoint[];
  centerLabel?: string;
  size?: number;
}) {
  if (!data.length) return null;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = 42;
  const cx = 60;
  const cy = 60;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#f43f5e", "#8b5cf6", "#06b6d4"];

  const slices = data.map((d, i) => {
    const pct = d.value / total;
    const dash = pct * circ;
    const gap = circ - dash;
    const slice = (
      <circle
        key={d.label}
        r={r}
        cx={cx}
        cy={cy}
        fill="none"
        stroke={d.color || COLORS[i % COLORS.length]}
        strokeWidth={14}
        strokeDasharray={`${dash} ${gap}`}
        strokeDashoffset={-offset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dasharray 0.6s cubic-bezier(0.16,1,0.3,1)" }}
      />
    );
    offset += dash;
    return slice;
  });

  return (
    <div className="donut-wrap">
      <div style={{ position: "relative", flexShrink: 0 }}>
        <svg width={size} height={size} viewBox="0 0 120 120">
          <circle r={r} cx={cx} cy={cy} fill="none" stroke="var(--bg-3)" strokeWidth={14} />
          {slices}
        </svg>
        {centerLabel && (
          <div style={{
            position: "absolute", inset: 0,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            pointerEvents: "none",
          }}>
            <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.03em" }}>{total}</span>
            <span style={{ fontSize: 10, color: "var(--text-3)", marginTop: 1 }}>{centerLabel}</span>
          </div>
        )}
      </div>
      <div className="donut-labels">
        {data.map((d, i) => (
          <div className="donut-row" key={d.label}>
            <span className="swatch" style={{ background: d.color || COLORS[i % COLORS.length] }} />
            <span className="truncate">{d.label}</span>
            <b>{d.value}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Line Chart ---- */
export function LineChart({ data }: { data: DataPoint[] }) {
  if (!data.length) return null;
  const W = 600;
  const H = 120;
  const PAD = { t: 8, r: 8, b: 24, l: 8 };
  const max = Math.max(...data.map((d) => d.value), 1);
  const xStep = (W - PAD.l - PAD.r) / Math.max(data.length - 1, 1);
  const yScale = (v: number) => PAD.t + (1 - v / max) * (H - PAD.t - PAD.b);

  const pts = data.map((d, i) => ({
    x: PAD.l + i * xStep,
    y: yScale(d.value),
    d,
  }));

  const pathD = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const areaD =
    `M${pts[0].x},${H - PAD.b} ` +
    pts.map((p) => `L${p.x},${p.y}`).join(" ") +
    ` L${pts[pts.length - 1].x},${H - PAD.b} Z`;

  // Show every nth label to avoid clutter
  const labelEvery = Math.max(1, Math.floor(data.length / 6));

  return (
    <svg className="line-chart-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ height: 120 }}>
      <defs>
        <linearGradient id="lg-line" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#lg-line)" />
      <path d={pathD} fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3" fill="#3b82f6" />
          {i % labelEvery === 0 && (
            <text
              x={p.x}
              y={H - 4}
              textAnchor="middle"
              fill="var(--text-4)"
              fontSize="9"
              fontFamily="var(--font)"
            >
              {p.d.label.slice(5)}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
