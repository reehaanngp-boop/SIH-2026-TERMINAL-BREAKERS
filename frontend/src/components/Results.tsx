import { pick, useI18n } from "../i18n";
import type { AiAnalysis, AnalysisResult, RedFlag, NextStep } from "../types";
import { RiskGauge } from "./RiskGauge";
import { Badge } from "./Badge";

const SEV_ORDER: RedFlag["severity"][] = ["critical", "warning", "info"];

export function ResultView({ result }: { result: AnalysisResult }) {
  const { lang, t } = useI18n();
  const flags = [...result.red_flags].sort(
    (a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity),
  );

  const severityTone = (s: RedFlag["severity"]): "rose" | "amber" | "blue" =>
    s === "critical" ? "rose" : s === "warning" ? "amber" : "blue";

  return (
    <div className="result-card">
      {/* Header */}
      <div className="result-header">
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <RiskGauge score={result.risk.score} size={140} />
          <div>
            <Badge tone={result.risk.level as any}>{t(`result.level.${result.risk.level}`)}</Badge>
            <p style={{ marginTop: 8, fontSize: 14, fontWeight: 500, maxWidth: 260 }}>
              {pick(result.risk.label, lang)}
            </p>
            {result.original_filename && (
              <p className="text-muted text-sm" style={{ marginTop: 4 }}>
                {result.original_filename}
                {result.duration_seconds != null && <span> · {Math.round(result.duration_seconds)}s</span>}
                {result.language && <span> · {result.language}</span>}
              </p>
            )}
          </div>
        </div>

        {/* Report actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
          <a className="btn btn-danger" href={`tel:${result.report.helpline}`}>
            📞 {t("result.report.helpline")}
          </a>
          <a className="btn btn-secondary" href={result.report.portal} target="_blank" rel="noreferrer">
            🌐 {t("result.report.portal")}
          </a>
          <a className="btn btn-ghost" href="#/assistant">
            ✦ {t("assistant.consult_scan")}
          </a>
        </div>
      </div>

      {/* Red flags */}
      <div className="result-section">
        <div className="result-section-title">{t("result.redflags")}</div>
        {flags.length === 0 ? (
          <div className="text-muted text-sm">{t("result.redflags.none")}</div>
        ) : (
          <div className="result-findings">
            {flags.map((f) => (
              <div key={f.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                  <span
                    className="status-dot"
                    style={{ background: f.severity === "critical" ? "var(--rose)" : f.severity === "warning" ? "var(--amber)" : "var(--blue)" }}
                  />
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{pick(f.title, lang)}</span>
                  <Badge tone={severityTone(f.severity) as any}>{f.severity}</Badge>
                </div>
                <p className="text-muted text-sm" style={{ paddingLeft: 16 }}>{pick(f.detail, lang)}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI analysis */}
      {result.ai_analysis && <AiCard ai={result.ai_analysis} />}

      {/* Next steps */}
      <div className="result-section">
        <div className="result-section-title">{t("result.nextsteps")}</div>
        <ol style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 8 }}>
          {result.next_steps.map((s) => (
            <NextStepItem key={s.id} step={s} />
          ))}
        </ol>
      </div>

      {/* Signals table */}
      <div className="result-section">
        <div className="result-section-title">{t("result.signals")}</div>
        <div className="table-wrap" style={{ borderRadius: "var(--r-md)" }}>
          <table>
            <thead>
              <tr>
                <th>Signal</th>
                <th>Status</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {Object.values(result.signals).map((sig) => (
                <tr key={sig.name}>
                  <td>
                    <span style={{ fontWeight: 500 }}>{sig.name}</span>
                    {sig.engine && <span className="text-dim text-sm"> · {sig.engine}</span>}
                  </td>
                  <td>
                    <Badge
                      tone={(sig.status as string) === "detected" ? "rose" : (sig.status as string) === "clear" ? "emerald" : "neutral"}
                    >
                      {t(`result.signals.${sig.status}`)}
                    </Badge>
                  </td>
                  <td>
                    {sig.label && (
                      <span style={{ fontWeight: 600, marginRight: 8, fontSize: 12 }}>{sig.label}</span>
                    )}
                    {sig.score != null && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
                        <div className="bar-track" style={{ width: 80 }}>
                          <div
                            className="bar-fill"
                            style={{
                              width: `${Math.round(sig.score * 100)}%`,
                              background: sig.score >= 0.6 ? "var(--rose)" : sig.score >= 0.4 ? "var(--amber)" : "var(--emerald)",
                            }}
                          />
                        </div>
                        <span className="text-sm text-muted">{Math.round(sig.score * 100)}%</span>
                      </div>
                    )}
                    {sig.detail && <div className="text-dim text-sm" style={{ marginTop: 2 }}>{sig.detail}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transcript */}
      {result.transcript && (
        <div className="result-section">
          <div className="result-section-title">{t("result.transcript")}</div>
          <pre style={{ fontSize: 12.5, whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 300, overflowY: "auto" }}>
            {result.transcript}
          </pre>
        </div>
      )}
    </div>
  );
}

function NextStepItem({ step }: { step: NextStep }) {
  const { lang } = useI18n();
  const content = (
    <>
      <span style={{ fontWeight: 500, fontSize: 13 }}>{pick(step.title, lang)}</span>
      {step.detail && <div className="text-muted text-sm" style={{ marginTop: 2 }}>{pick(step.detail, lang)}</div>}
    </>
  );
  return (
    <li>
      {step.href ? (
        <a href={step.href} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
          {content}
        </a>
      ) : content}
    </li>
  );
}

function AiCard({ ai }: { ai: AiAnalysis }) {
  const { lang, t } = useI18n();
  const v = ai.verdict;
  if (!v) {
    return (
      <div className="result-section">
        <div className="result-section-title">{t("result.ai.title")}</div>
        <div className="text-muted text-sm">{t("result.ai.unavailable")}</div>
      </div>
    );
  }
  const pct = Math.round(v.confidence * 100);
  return (
    <div className="result-section">
      <div className="result-section-title">{t("result.ai.title")}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <Badge tone={v.is_scam ? "rose" : "emerald"}>
          {t(v.is_scam ? "result.ai.verdict.scam" : "result.ai.verdict.benign")}
        </Badge>
        {v.scam_category && <span className="chip">{v.scam_category}</span>}
        <span className="text-muted text-sm">{t("result.ai.confidence")}: <strong>{pct}%</strong></span>
        {ai.model && <span className="text-dim text-sm">· {ai.model}</span>}
      </div>
      {v.key_indicators.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div className="text-dim text-xs" style={{ marginBottom: 4, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
            {t("result.ai.indicators")}
          </div>
          <ul style={{ paddingLeft: 16, fontSize: 13, color: "var(--text-2)", lineHeight: 1.7 }}>
            {v.key_indicators.map((k, i) => <li key={i}>{k}</li>)}
          </ul>
        </div>
      )}
      {v.explanation && (
        <p style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.6 }}>
          {pick(v.explanation, lang)}
        </p>
      )}
    </div>
  );
}
