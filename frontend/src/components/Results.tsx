import { pick, useI18n } from "../i18n";
import type { AiAnalysis, AnalysisResult, RedFlag, NextStep } from "../types";
import { RiskGauge } from "./RiskGauge";

const SEVERITY_ORDER: RedFlag["severity"][] = ["critical", "warning", "info"];

export function ResultView({ result }: { result: AnalysisResult }) {
  const { lang, t } = useI18n();
  const flags = [...result.red_flags].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );
  const levelKey = `result.level.${result.risk.level}`;

  return (
    <section className="result">
      <div className="result-head">
        <RiskGauge score={result.risk.score} level={result.risk.level} />
        <div className="result-verdict">
          <div className={`badge badge-${result.risk.level}`}>{t(levelKey)}</div>
          <p className="verdict-label">{pick(result.risk.label, lang)}</p>
          {result.original_filename && (
            <p className="result-meta">
              {result.original_filename}
              {result.duration_seconds != null && (
                <span> · {t("result.duration")}: {Math.round(result.duration_seconds)}s</span>
              )}
              {result.language && <span> · {t("result.lang")}: {result.language}</span>}
            </p>
          )}
        </div>
      </div>

      <div className="result-report">
        <a className="btn btn-primary" href={`tel:${result.report.helpline}`}>
          {t("result.report.helpline")}
        </a>
        <a className="btn btn-secondary" href={result.report.portal} target="_blank" rel="noreferrer">
          {t("result.report.portal")}
        </a>
      </div>

      <h3>{t("result.redflags")}</h3>
      {flags.length === 0 ? (
        <p className="muted">{t("result.redflags.none")}</p>
      ) : (
        <ul className="flags">
          {flags.map((f) => (
            <li key={f.id} className={`flag flag-${f.severity}`}>
              <div className="flag-title">
                <span className={`dot dot-${f.severity}`} />
                {pick(f.title, lang)}
              </div>
              <div className="flag-detail">{pick(f.detail, lang)}</div>
            </li>
          ))}
        </ul>
      )}

      {result.ai_analysis && <AiCard ai={result.ai_analysis} />}

      <h3>{t("result.nextsteps")}</h3>
      <ol className="steps">
        {result.next_steps.map((s) => (
          <NextStepItem key={s.id} step={s} />
        ))}
      </ol>

      <h3>{t("result.signals")}</h3>
      <table className="signals">
        <tbody>
          {Object.values(result.signals).map((sig) => (
            <tr key={sig.name}>
              <td className="sig-name">{sig.name}</td>
              <td className={`sig-status sig-${sig.status}`}>{t(`result.signals.${sig.status}`)}</td>
              <td className="sig-detail">
                {sig.label && <strong>{sig.label}</strong>}
                {sig.detail && <div className="muted small">{sig.detail}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {result.transcript && (
        <>
          <h3>{t("result.transcript")}</h3>
          <blockquote className="transcript">{result.transcript}</blockquote>
        </>
      )}
    </section>
  );
}

function NextStepItem({ step }: { step: NextStep }) {
  const { lang } = useI18n();
  const inner = (
    <>
      <div className="step-title">{pick(step.title, lang)}</div>
      {step.detail && <div className="step-detail muted">{pick(step.detail, lang)}</div>}
    </>
  );
  if (step.href) {
    return (
      <li className="step">
        <a href={step.href} target="_blank" rel="noreferrer" className="step-anchor">
          {inner}
        </a>
      </li>
    );
  }
  return <li className="step">{inner}</li>;
}

function AiCard({ ai }: { ai: AiAnalysis }) {
  const { lang, t } = useI18n();
  const v = ai.verdict;
  if (!v) {
    return (
      <section className="result-ai">
        <h3>{t("result.ai.title")}</h3>
        <p className="muted">{t("result.ai.unavailable")}</p>
      </section>
    );
  }
  const pct = Math.round(v.confidence * 100);
  return (
    <section className="result-ai">
      <h3>{t("result.ai.title")}</h3>
      <div className={`badge ${v.is_scam ? "badge-high" : "badge-low"}`}>
        {t(v.is_scam ? "result.ai.verdict.scam" : "result.ai.verdict.benign")}
      </div>
      {v.scam_category && (
        <p className="muted small">
          {t("result.ai.category")}: {v.scam_category}
        </p>
      )}
      {v.key_indicators.length > 0 && (
        <>
          <div className="muted small">{t("result.ai.indicators")}</div>
          <ul className="ai-indicators">
            {v.key_indicators.map((k, i) => (
              <li key={i}>{k}</li>
            ))}
          </ul>
        </>
      )}
      {v.explanation && (
        <>
          <div className="muted small">{t("result.ai.explanation")}</div>
          <p className="ai-explanation">{pick(v.explanation, lang)}</p>
        </>
      )}
      <p className="muted small">
        {t("result.ai.confidence")}: {pct}%
        {ai.model && <> · {t("result.ai.model")}: {ai.model}</>}
      </p>
    </section>
  );
}
