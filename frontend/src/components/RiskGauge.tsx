import type { RiskLevel } from "../types";

/** Semi-circular SVG gauge (0-100) with a colour per risk band. */
export function RiskGauge({ score, level }: { score: number; level: RiskLevel }) {
  const startAngle = -210; // degrees
  const endAngle = 30;
  const value = Math.max(0, Math.min(100, score));
  const pointerAngle = startAngle + (value / 100) * (endAngle - startAngle);

  const color = level === "high" ? "#e5484d" : level === "medium" ? "#f5a623" : "#2fbf71";
  const R = 80;
  const cx = 100;
  const cy = 100;
  const polar = (deg: number) => {
    const rad = (deg * Math.PI) / 180;
    return [cx + R * Math.cos(rad), cy + R * Math.sin(rad)] as const;
  };

  // Background arc
  const [ax0, ay0] = polar(startAngle);
  const [ax1, ay1] = polar(endAngle);
  const large = endAngle - startAngle > 180 ? 1 : 0;

  // Colored arc up to the score
  const [px0, py0] = polar(startAngle);
  const [px1, py1] = polar(pointerAngle);
  const plarge = pointerAngle - startAngle > 180 ? 1 : 0;

  // Pointer line
  const [q0x, q0y] = polar(pointerAngle);
  const tipX = cx + (R + 12) * Math.cos((pointerAngle * Math.PI) / 180);
  const tipY = cy + (R + 12) * Math.sin((pointerAngle * Math.PI) / 180);

  return (
    <div className="gauge">
      <svg viewBox="0 0 200 120" role="img" aria-label={`risk ${score} of 100`}>
        <path
          d={`M ${ax0} ${ay0} A ${R} ${R} 0 ${large} 1 ${ax1} ${ay1}`}
          fill="none"
          stroke="#e6e9ef"
          strokeWidth="14"
          strokeLinecap="round"
        />
        {value > 0.5 && (
          <path
            d={`M ${px0} ${py0} A ${R} ${R} 0 ${plarge} 1 ${px1} ${py1}`}
            fill="none"
            stroke={color}
            strokeWidth="14"
            strokeLinecap="round"
          />
        )}
        <line x1={q0x} y1={q0y} x2={tipX} y2={tipY} stroke={color} strokeWidth="4" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="6" fill={color} />
      </svg>
      <div className="gauge-value" style={{ color }}>
        {Math.round(value)}
      </div>
    </div>
  );
}
