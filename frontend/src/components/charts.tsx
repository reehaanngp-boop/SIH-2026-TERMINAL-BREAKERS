import { niceCeil } from "../utils";

/* ---------------------------------------------------------------------------
   Inline-SVG charts (offline-safe, no chart lib). Colours validated with the
   dataviz palette checker against the dark surface — see styles.css tokens.
   - single series use the brand accent; categorical trios use --cat-1/2/3
   - status series (risk) use --low/--medium/--high
   Text wears ink tokens; marks carry identity. Hover = per-mark tooltips.
--------------------------------------------------------------------------- */

export interface BarDatum {
  label: string;
  value: number;
}

/** Vertical single-series bar chart with per-mark hover tooltips. */
export function BarChart({ data, unit }: { data: BarDatum[]; unit?: string }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="chart">
      <div className="bars">
        {data.map((d) => {
          const h = Math.round((d.value / max) * 100);
          return (
            <div className="bar-col" key={d.label}>
              <div className="bar-tip">
                {d.label} · {d.value}
                {unit ? ` ${unit}` : ""}
              </div>
              <div className="bar">
                <div className="bar-fill" style={{ height: `${h}%` }} />
              </div>
              <div className="bar-label" title={d.label}>
                {d.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export interface DonutDatum {
  label: string;
  value: number;
  color: string;
}

/** Donut with legend rows (count + share). Segments carry a surface gap. */
export function DonutChart({ data, centerLabel }: { data: DonutDatum[]; centerLabel: string }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const R = 60;
  const C = 2 * Math.PI * R;
  let acc = 0;
  const segments = data
    .filter((d) => d.value > 0)
    .map((d) => {
      const frac = d.value / total;
      const dash = Math.max(frac * C - 3.5, 0.5); // 2px-ish surface gap between segments
      const off = -acc * C;
      acc += frac;
      return { ...d, frac, dash, off };
    });

  return (
    <div className="donut-wrap">
      <div className="donut">
        <svg viewBox="0 0 150 150" role="img" aria-label={centerLabel}>
          <circle cx={75} cy={75} r={R} fill="none" stroke="#1e2733" strokeWidth="17" />
          {segments.map((s) => (
            <circle
              key={s.label}
              cx={75}
              cy={75}
              r={R}
              fill="none"
              stroke={s.color}
              strokeWidth="15"
              strokeDasharray={`${s.dash} ${C - s.dash}`}
              strokeDashoffset={s.off}
              strokeLinecap="round"
            />
          ))}
        </svg>
        <div className="donut-center">
          <b>{total}</b>
          <span>{centerLabel}</span>
        </div>
      </div>
      <div className="donut-labels">
        {data.map((d) => {
          const pct = total ? Math.round((d.value / total) * 100) : 0;
          return (
            <div className="donut-row" key={d.label}>
              <span className="swatch" style={{ background: d.color }} />
              <span>{d.label}</span>
              <b>
                {d.value} · {pct}%
              </b>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export interface LineDatum {
  label: string;
  value: number;
}

/** Single-series time chart: area + 2px line + hoverable point markers. */
export function LineChart({ data }: { data: LineDatum[] }) {
  const W = 640;
  const H = 180;
  const PL = 34;
  const PR = 10;
  const PT = 10;
  const PB = 26;
  const plotW = W - PL - PR;
  const plotH = H - PT - PB;
  const nice = niceCeil(Math.max(1, ...data.map((d) => d.value)));

  const x = (i: number) =>
    data.length <= 1 ? PL + plotW / 2 : PL + plotW * (i / (data.length - 1));
  const y = (v: number) => PT + plotH * (1 - v / nice);

  const pts = data.map((d, i) => [x(i), y(d.value)] as const);
  const line = pts
    .map(([px, py], i) => `${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`)
    .join(" ");
  const area = `${line} L${x(data.length - 1).toFixed(1)},${(H - PB).toFixed(1)} L${x(0).toFixed(
    1,
  )},${(H - PB).toFixed(1)} Z`;

  const grid = [0.25, 0.5, 0.75, 1].map((f) => {
    const gy = PT + plotH * (1 - f);
    return { gy, label: Math.round(nice * f) };
  });

  // Show every other x label when crowded.
  const step = data.length > 8 ? 2 : 1;

  return (
    <div className="chart line-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Analyses over time">
        <defs>
          <linearGradient id="lgrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
          </linearGradient>
        </defs>
        {grid.map((g) => (
          <g key={g.label}>
            <line x1={PL} y1={g.gy} x2={W - PR} y2={g.gy} stroke="#18202c" strokeWidth="1" />
            <text x={PL - 6} y={g.gy + 3} textAnchor="end" fontSize="10" fill="#5c6a7d">
              {g.label}
            </text>
          </g>
        ))}
        {data.length > 0 && <path d={area} fill="url(#lgrad)" />}
        {data.length > 0 && (
          <path d={line} fill="none" stroke="#2dd4bf" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        )}
        {pts.map(([px, py], i) => (
          <g key={i}>
            <circle className="line-pt" cx={px} cy={py} r="4" fill="#2dd4bf" stroke="#0a0e14" strokeWidth="2">
              <title>
                {data[i].label} · {data[i].value}
              </title>
            </circle>
            {i % step === 0 && (
              <text
                x={px}
                y={H - 8}
                textAnchor="middle"
                fontSize="10"
                fill="#5c6a7d"
              >
                {data[i].label}
              </text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
