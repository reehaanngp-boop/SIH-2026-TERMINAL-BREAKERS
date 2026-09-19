import { useEffect, useState } from "react";
import { api } from "../api";
import { StatCard } from "../components/StatCard";
import { Badge } from "../components/Badge";
import { BarChart, DonutChart, LineChart } from "../components/charts";
import { useI18n } from "../i18n";
import type { AnalyticsStats } from "../types";
import { fmtDate } from "../utils";

const RISK_COLORS: Record<string, string> = {
  low: "#10b981",
  medium: "#f59e0b",
  high: "#f43f5e",
};
const STATUS_COLORS: Record<string, string> = {
  open: "#3b82f6",
  investigating: "#f59e0b",
  closed: "#64748b",
};

export function DashboardPage() {
  const { t } = useI18n();
  const [a, setA] = useState<AnalyticsStats | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.getAnalytics().then(setA).catch((e) => setErr(e instanceof Error ? e.message : "error"));
  }, []);

  if (err) return <div className="page"><div className="error-banner">{err}</div></div>;
  if (!a) return (
    <div className="center" style={{ minHeight: "60vh" }}>
      <div className="spinner" />
      <p className="text-muted">{t("status.loading")}</p>
    </div>
  );

  const riskData = a.risk_levels
    .filter((r) => RISK_COLORS[r.level])
    .map((r) => ({ label: t(`result.level.${r.level}`), value: r.count, color: RISK_COLORS[r.level] }));

  const catData = a.scam_categories.map((c) => ({ label: c.category, value: c.count }));
  const trend = a.scans_last_14d.map((d) => ({ label: d.date, value: d.count }));

  return (
    <div className="page">
      {/* Header */}
      <div className="page-head">
        <h1>{t("dash.title")}</h1>
        <p>{t("dash.sub")}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-4">
        <StatCard label={t("dash.stat.cases")} value={a.stats.cases} accent />
        <StatCard label={t("dash.stat.evidence")} value={a.stats.evidence} />
        <StatCard label={t("dash.stat.scans")} value={a.stats.scans} />
        <StatCard label={t("dash.stat.numbers")} value={a.stats.reported_numbers} />
      </div>

      {/* Video Walkthrough Showcase */}
      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
          <div>
            <div className="chart-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span>🎬</span>
              <span>Platform Video Walkthroughs</span>
              <span style={{ background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", border: "1px solid #38bdf8", fontSize: "0.75rem", padding: "2px 8px", borderRadius: 4, fontWeight: 700 }}>
                Real UI Tour
              </span>
            </div>
            <div className="chart-sub">
              Watch the quick 18s intro overview or explore the complete 60s screen-by-screen walkthrough explaining how DigiRaksha protects against AI voice clones and digital arrest fraud.
            </div>
          </div>
        </div>

        <div className="grid grid-2" style={{ gap: 16 }}>
          {/* Intro Video */}
          <div style={{ background: "rgba(15, 23, 42, 0.6)", borderRadius: 10, padding: 14, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <strong style={{ color: "var(--text-1)", fontSize: "0.95rem" }}>Platform Intro (18s)</strong>
              <span style={{ fontSize: "0.75rem", color: "#38bdf8", background: "rgba(56, 189, 248, 0.15)", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                QUICK OVERVIEW
              </span>
            </div>
            <video
              controls
              poster="/videos/digiraksha_intro.jpg"
              preload="metadata"
              style={{ width: "100%", borderRadius: 8, background: "#050914", aspectRatio: "16/9", objectFit: "cover" }}
            >
              <source src="/videos/digiraksha_intro.mp4" type="video/mp4" />
              Your browser does not support HTML5 video.
            </video>
            <p style={{ fontSize: "0.82rem", color: "var(--text-3)", marginTop: 8, lineHeight: 1.4 }}>
              High-impact overview: &lt;30ms VoIP interception, Dhwani XLS-R foundation model, pre-action wire quarantine, and court-admissible BSA Section 65B certification.
            </p>
          </div>

          {/* Full Walkthrough Video */}
          <div style={{ background: "rgba(15, 23, 42, 0.6)", borderRadius: 10, padding: 14, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <strong style={{ color: "var(--text-1)", fontSize: "0.95rem" }}>Complete Application Walkthrough (60s)</strong>
              <span style={{ fontSize: "0.75rem", color: "#10b981", background: "rgba(16, 185, 129, 0.15)", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                FULL REAL UI TOUR
              </span>
            </div>
            <video
              controls
              poster="/videos/digiraksha_walkthrough.jpg"
              preload="metadata"
              style={{ width: "100%", borderRadius: 8, background: "#050914", aspectRatio: "16/9", objectFit: "cover" }}
            >
              <source src="/videos/digiraksha_walkthrough.mp4" type="video/mp4" />
              Your browser does not support HTML5 video.
            </video>
            <p style={{ fontSize: "0.82rem", color: "var(--text-3)", marginTop: 8, lineHeight: 1.4 }}>
              Screen-by-screen tour of all 6 live modules: Command Dashboard, Live Call Sentinel HUD, Audio Forensics Lab, Media Authenticity, Banking SDK, and Blockchain Ledger.
            </p>
          </div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="chart-title">{t("dash.chart.categories")}</div>
          <div className="chart-sub">Scam type breakdown</div>
          {catData.length === 0
            ? <div className="empty">{t("dash.empty")}</div>
            : <BarChart data={catData} />}
        </div>
        <div className="card">
          <div className="chart-title">{t("dash.chart.risk")}</div>
          <div className="chart-sub">Risk distribution</div>
          {riskData.length === 0
            ? <div className="empty">{t("dash.empty")}</div>
            : <DonutChart data={riskData} centerLabel="scans" />}
        </div>
      </div>

      {/* Trend */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="chart-title">{t("dash.chart.trend")}</div>
        <div className="chart-sub">14-day scan trend</div>
        {trend.every((d) => d.value === 0)
          ? <div className="empty">{t("dash.empty")}</div>
          : <LineChart data={trend} />}
      </div>

      {/* Bottom row */}
      <div className="grid grid-2" style={{ marginTop: 16 }}>
        {/* Cases by status */}
        <div className="card">
          <div className="chart-title">{t("dash.chart.status")}</div>
          <div className="chart-sub">{t("cases.title")}</div>
          {a.cases_by_status.length === 0
            ? <div className="empty">{t("cases.empty")}</div>
            : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
                {a.cases_by_status.map((s) => (
                  <div className="donut-row" key={s.status}>
                    <span className="swatch" style={{ background: STATUS_COLORS[s.status] || "var(--text-4)" }} />
                    <span>{t(`case.status.${s.status}`)}</span>
                    <b>{s.count}</b>
                  </div>
                ))}
              </div>
            )}
        </div>

        {/* Recent high risk */}
        <div className="card">
          <div className="chart-title">{t("dash.recent")}</div>
          <div className="chart-sub">{t("dash.stat.high7")}: <strong>{a.stats.high_risk_7d}</strong></div>
          {a.recent_high_risk.length === 0
            ? <div className="empty">{t("dash.empty")}</div>
            : (
              <div>
                {a.recent_high_risk.map((s) => (
                  <div className="ev-row" key={s.scan_id}>
                    <div className="ev-ico">⚠️</div>
                    <div className="ev-main">
                      <div className="ev-name">{s.original_filename ?? s.scan_id.slice(0, 8)}</div>
                      <div className="ev-meta">{fmtDate(s.created_at)} · {s.media_type}</div>
                    </div>
                    <Badge tone={s.risk_score != null && s.risk_score >= 70 ? "critical" : "high"}>
                      {s.risk_score != null ? Math.round(s.risk_score) : "—"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
