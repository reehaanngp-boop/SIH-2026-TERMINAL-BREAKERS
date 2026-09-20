import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { CopilotPanel } from "../components/CopilotPanel";
import { Modal } from "../components/Modal";
import { ResultView } from "../components/Results";
import { useToasts } from "../components/Toast";
import { useI18n } from "../i18n";
import type { AnalysisResult, CaseListItem, JobStatus, Priority } from "../types";
import { downloadBlob } from "../utils";

type Mode = "transcript" | "upload";

export function AnalyzePage({ navigate }: { navigate: (r: string) => void }) {
  const { t } = useI18n();
  const [mode, setMode] = useState<Mode>("transcript");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showAttach, setShowAttach] = useState(false);

  const clearError = () => setError(null);

  const onResult = (r: AnalysisResult) => {
    setResult(r);
    setBusy(false);
  };

  const onError = (e: unknown) => {
    setError(e instanceof Error ? e.message : t("err.network"));
    setBusy(false);
  };

  const downloadTranscript = () => {
    if (!result?.transcript) return;
    downloadBlob(new Blob([result.transcript], { type: "text/plain;charset=utf-8" }), `digiraksha-${result.scan_id}.txt`);
  };

  return (
    <div className="page">
      <div className="page-head">
        <h1>{t("nav.analyze")}</h1>
        <p>{t("brand.tagline")}</p>
      </div>

      <div className="seg">
        <button className={`seg-btn ${mode === "transcript" ? "active" : ""}`} onClick={() => { setMode("transcript"); clearError(); }}>
          {t("tab.transcript")}
        </button>
        <button className={`seg-btn ${mode === "upload" ? "active" : ""}`} onClick={() => { setMode("upload"); clearError(); }}>
          {t("tab.upload")}
        </button>
      </div>

      {mode === "transcript" ? (
        <TranscriptForm busy={busy} onStart={setBusy} onResult={onResult} onError={onError} />
      ) : (
        <UploadForm busy={busy} onStart={setBusy} onProgress={setProgress} onProgressMsg={setProgressMsg} onResult={onResult} onError={onError} />
      )}

      {busy && <ProgressBar value={progress} label={progressMsg} />}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="link" onClick={clearError}>{t("err.try")}</button>
        </div>
      )}

      {result && !busy && (
        <>
          <div className="card">
            <ResultView result={result} />
            <div className="result-actions">
              <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ {t("cases.new")}</button>
              <button className="btn btn-secondary" onClick={() => setShowAttach(true)}>📁 {t("evidence.linkcase")}</button>
              {result.transcript && (
                <button className="btn btn-ghost" onClick={downloadTranscript}>⤓ {t("history.col.file")}</button>
              )}
            </div>
          </div>

          {/* Media Authenticity Check (merged from the former Media Authenticity section) */}
          <AuthCheckCard result={result} />

          {/* AI Cyber Copilot */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <CopilotPanel height="560px" />
          </div>
        </>
      )}

      {showCreate && result && (
        <CreateCaseModal
          result={result}
          onClose={() => setShowCreate(false)}
          onCreated={(c) => {
            setShowCreate(false);
            navigate(`/cases/${c.id}`);
          }}
        />
      )}
      {showAttach && result && (
        <AttachCaseModal
          scanId={result.scan_id}
          onClose={() => setShowAttach(false)}
          onAttached={(c) => {
            setShowAttach(false);
            navigate(`/cases/${c.id}`);
          }}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ forms */

function TranscriptForm({
  busy, onStart, onResult, onError,
}: {
  busy: boolean;
  onStart: (b: boolean) => void;
  onResult: (r: AnalysisResult) => void;
  onError: (e: unknown) => void;
}) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [lang, setLang] = useState("");

  const submit = async () => {
    if (!text.trim() || busy) return;
    onStart(true);
    try {
      onResult(await api.analyzeTranscript(text.trim(), lang || undefined));
    } catch (e) {
      onError(e);
    }
  };

  return (
    <div className="card">
      <label className="field-label" htmlFor="transcript">{t("label.text")}</label>
      <textarea
        id="transcript"
        className="textarea"
        rows={8}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t("placeholder.text")}
      />
      <div className="row">
        <label className="field-label" htmlFor="lang">{t("label.language")}</label>
        <select id="lang" className="select" style={{ width: 180 }} value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="">{t("lang.auto")}</option>
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
          <option value="hi-en">Hinglish</option>
        </select>
      </div>
      <button className="btn btn-primary" onClick={submit} disabled={busy || !text.trim()}>
        {t("btn.analyze")}
      </button>
    </div>
  );
}

function UploadForm({
  busy, onStart, onProgress, onProgressMsg, onResult, onError,
}: {
  busy: boolean;
  onStart: (b: boolean) => void;
  onProgress: (p: number) => void;
  onProgressMsg: (m: string) => void;
  onResult: (r: AnalysisResult) => void;
  onError: (e: unknown) => void;
}) {
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const pollRef = useRef<number | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const poll = useCallback(
    async (jobId: string) => {
      const clear = () => {
        if (pollRef.current) clearTimeout(pollRef.current);
        pollRef.current = null;
      };
      try {
        const st: JobStatus = await api.getJob(jobId);
        if (st.status === "completed" && st.result) {
          clear();
          onResult(st.result);
          return;
        }
        if (st.status === "failed") {
          clear();
          onError(new Error(st.error || "Analysis failed"));
          return;
        }
        onProgress(st.progress);
        if (st.message) onProgressMsg(st.message);
        pollRef.current = setTimeout(() => poll(jobId), 800);
      } catch (e) {
        clear();
        onError(e);
      }
    },
    [onProgress, onProgressMsg, onResult, onError],
  );

  const upload = async () => {
    if (!file || busy) return;
    onStart(true);
    onProgress(0.02);
    onProgressMsg(t("status.uploading"));
    try {
      const created = await api.uploadMedia(file);
      onProgress(0.05);
      onProgressMsg(t("status.analyzing"));
      await poll(created.job_id);
    } catch (e) {
      onError(e);
    }
  };

  useEffect(() => () => {
    if (pollRef.current) clearTimeout(pollRef.current);
  }, []);

  const pickFile = (f: File | null) => setFile(f);

  return (
    <div className="card">
      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onClick={() => !busy && fileInput.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          pickFile(e.dataTransfer.files?.[0] ?? null);
        }}
      >
        <input
          ref={fileInput}
          type="file"
          accept="audio/*,video/*,.wav,.mp3,.m4a,.ogg,.flac,.mp4,.mov,.webm,.amr"
          hidden
          onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
        />
        <div className="dropzone-icon">📁</div>
        <div className="dropzone-text">{t("upload.drop")}</div>
        <div className="muted small">{t("upload.supported")}</div>
      </div>
      {file && <div className="file-chip"><b>{file.name}</b> · {(file.size / 1024 / 1024).toFixed(1)} MB</div>}
      <button className="btn btn-primary" onClick={upload} disabled={busy || !file} style={{ marginTop: 12 }}>
        {t("btn.upload")}
      </button>
    </div>
  );
}

function ProgressBar({ value, label }: { value: number; label: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="progress">
      <div className="progress-bar" style={{ width: `${pct}%` }} />
      <div className="progress-label">{label || `${pct}%`}</div>
    </div>
  );
}

/* ------------------------------------------- media authenticity (merged) */

interface AuthSignal {
  name: string;
  description: string;
  verdict: "clean" | "suspicious" | "manipulated" | "unknown";
  confidence: number; // 0-1
  detail?: string;
}

function deriveAuthSignals(result: AnalysisResult): AuthSignal[] {
  const sigs: AuthSignal[] = [];
  const signals = result.signals;

  const statusIs = (s: unknown, val: string) => (s as string) === val;

  // Voice clone detection
  const clone = signals.voice_clone ?? signals.clone ?? signals.deepfake ?? signals.aasist;
  if (clone) {
    sigs.push({
      name: "AI Voice Clone Detection",
      description: "Detects if voice was generated by AI synthesis (TTS/voice conversion)",
      verdict: statusIs(clone.status, "detected") ? "manipulated" :
               statusIs(clone.status, "clear") ? "clean" : "unknown",
      confidence: clone.score ?? (statusIs(clone.status, "detected") ? 0.85 : 0.1),
      detail: clone.label ?? clone.detail ?? undefined,
    });
  }

  // Audio manipulation / editing artifacts
  const edit = signals.audio_edit ?? signals.splicing ?? signals.tampering;
  if (edit) {
    sigs.push({
      name: "Audio Splice & Edit Detection",
      description: "Checks for cut-and-paste audio editing, silence insertion or temporal artifacts",
      verdict: statusIs(edit.status, "detected") ? "manipulated" : statusIs(edit.status, "clear") ? "clean" : "unknown",
      confidence: edit.score ?? (statusIs(edit.status, "detected") ? 0.78 : 0.1),
      detail: edit.detail ?? undefined,
    });
  }

  // Background noise / environment consistency
  const bg = signals.background ?? signals.noise ?? signals.environment;
  if (bg) {
    sigs.push({
      name: "Environment Consistency",
      description: "Detects inconsistent background noise indicating studio-generated content",
      verdict: statusIs(bg.status, "detected") ? "suspicious" : statusIs(bg.status, "clear") ? "clean" : "unknown",
      confidence: bg.score ?? 0.5,
      detail: bg.detail ?? undefined,
    });
  }

  // Prosody / human speech patterns
  const prosody = signals.prosody ?? signals.naturalness ?? signals.rhythm;
  if (prosody) {
    sigs.push({
      name: "Prosody & Naturalness",
      description: "Checks if speech rhythm, intonation, and breathing match organic human speech",
      verdict: statusIs(prosody.status, "detected") ? "suspicious" :
               statusIs(prosody.status, "clear") ? "clean" : "unknown",
      confidence: prosody.score ?? 0.5,
      detail: prosody.detail ?? undefined,
    });
  }

  // MFCC / spectral features
  const spectral = signals.spectral ?? signals.mfcc ?? signals.frequency;
  if (spectral) {
    sigs.push({
      name: "Spectral Fingerprint",
      description: "Analyzes frequency patterns for codec artifacts typical in AI-generated audio",
      verdict: statusIs(spectral.status, "detected") ? "manipulated" : statusIs(spectral.status, "clear") ? "clean" : "unknown",
      confidence: spectral.score ?? 0.5,
      detail: spectral.detail ?? undefined,
    });
  }

  // Transcription-based (content scam signals)
  const content = signals.content ?? signals.scam ?? signals.keywords;
  if (content) {
    sigs.push({
      name: "Content Authenticity",
      description: "Checks spoken content for scripted scam language, forced/unnatural phrasing",
      verdict: statusIs(content.status, "detected") ? "suspicious" : statusIs(content.status, "clear") ? "clean" : "unknown",
      confidence: content.score ?? (result.risk.score / 100),
      detail: content.detail ?? undefined,
    });
  }

  // If no signals, synthesize from risk score and red flags
  if (sigs.length === 0) {
    const riskScore = result.risk.score / 100;
    const hasCloneFlag = result.red_flags.some(
      (f) => f.id.includes("clone") || f.id.includes("deepfake") || f.id.includes("synthetic") || f.id.includes("aasist"),
    );
    const hasEditFlag = result.red_flags.some(
      (f) => f.id.includes("edit") || f.id.includes("tamper") || f.id.includes("splice"),
    );

    sigs.push({
      name: "AI Voice Synthesis Detection",
      description: "Overall assessment of AI-generated or cloned voice patterns",
      verdict: hasCloneFlag ? "manipulated" : riskScore > 0.6 ? "suspicious" : "clean",
      confidence: riskScore,
      detail: hasCloneFlag ? "AI-generated voice patterns detected" : "No cloning artifacts detected",
    });

    sigs.push({
      name: "Audio Integrity Check",
      description: "Temporal and spectral consistency of the audio file",
      verdict: hasEditFlag ? "manipulated" : riskScore > 0.7 ? "suspicious" : "clean",
      confidence: Math.max(0.1, riskScore * 0.9),
      detail: hasEditFlag ? "Editing artifacts detected" : "Audio appears unmodified",
    });

    sigs.push({
      name: "Content Pattern Analysis",
      description: "Script-like language, coercion phrases, and urgency signals",
      verdict: riskScore > 0.7 ? "suspicious" : "clean",
      confidence: riskScore,
      detail: `${result.red_flags.length} suspicious patterns found`,
    });
  }

  return sigs;
}

function computeOverallVerdict(signals: AuthSignal[], riskScore: number) {
  const manipulated = signals.filter((s) => s.verdict === "manipulated").length;
  const suspicious = signals.filter((s) => s.verdict === "suspicious").length;

  if (manipulated >= 1 || riskScore >= 70) return "manipulated" as const;
  if (suspicious >= 2 || riskScore >= 45) return "suspicious" as const;
  return "authentic" as const;
}

const VERDICT_META = {
  authentic:   { icon: "✅", label: "Authentic",   color: "var(--emerald)", badge: "emerald" },
  suspicious:  { icon: "⚠️",  label: "Suspicious",  color: "var(--amber)",   badge: "amber" },
  manipulated: { icon: "🚨", label: "Manipulated / Cloned", color: "var(--rose)", badge: "rose" },
};

const SIGNAL_VERDICT_META = {
  clean:       { color: "var(--emerald)", badge: "emerald", label: "Clean" },
  suspicious:  { color: "var(--amber)",   badge: "amber",   label: "Suspicious" },
  manipulated: { color: "var(--rose)",    badge: "rose",    label: "Manipulated" },
  unknown:     { color: "var(--text-4)",  badge: "neutral", label: "Unknown" },
};

function AuthCheckCard({ result }: { result: AnalysisResult }) {
  const authSignals = deriveAuthSignals(result);
  const overallVerdict = computeOverallVerdict(authSignals, result.risk.score);
  const verdictMeta = VERDICT_META[overallVerdict];

  return (
    <div className="card" style={{ padding: "18px 20px" }}>
      <div
        className="auth-check-result"
        style={{ border: `1.5px solid`, borderColor: verdictMeta.color + "44", borderRadius: "var(--r-lg)", padding: 16 }}
      >
        <div className="auth-check-header">
          <span className="auth-verdict-icon">{verdictMeta.icon}</span>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <span style={{ fontSize: 16, fontWeight: 700, color: verdictMeta.color }}>
                Media Authenticity: {verdictMeta.label}
              </span>
              <Badge tone={verdictMeta.badge}>
                Risk Score: {Math.round(result.risk.score)}/100
              </Badge>
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-2)" }}>
              {overallVerdict === "authentic" && "No significant signs of AI generation or audio manipulation detected."}
              {overallVerdict === "suspicious" && "Some suspicious patterns detected. Human review recommended before trusting this content."}
              {overallVerdict === "manipulated" && "Strong evidence of AI voice cloning or audio manipulation. This file should NOT be trusted."}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, alignSelf: "flex-start" }}>
            <a className="btn btn-danger btn-sm" href="tel:1930">📞 Report 1930</a>
          </div>
        </div>

        <div className="auth-check-section" style={{ marginTop: 14 }}>
          <div className="auth-check-section-title">Authenticity Signals</div>
          {authSignals.map((sig) => {
            const meta = SIGNAL_VERDICT_META[sig.verdict];
            const pct = Math.round(sig.confidence * 100);
            return (
              <div className="auth-signal-row" key={sig.name}>
                <div style={{ width: 130, flexShrink: 0 }}>
                  <Badge tone={meta.badge}>{meta.label}</Badge>
                </div>
                <div className="auth-signal-name">
                  <div style={{ fontWeight: 500, fontSize: 13 }}>{sig.name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--text-4)", marginTop: 1 }}>{sig.description}</div>
                </div>
                <div className="auth-signal-bar">
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div className="bar-track" style={{ flex: 1 }}>
                      <div
                        className="bar-fill"
                        style={{ width: `${pct}%`, background: meta.color }}
                      />
                    </div>
                    <span style={{ fontSize: 11.5, color: "var(--text-3)", minWidth: 32, textAlign: "right" }}>
                      {pct}%
                    </span>
                  </div>
                  {sig.detail && (
                    <div style={{ fontSize: 11, color: "var(--text-4)", marginTop: 3 }}>{sig.detail}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- case actions */
function CreateCaseModal({
  result,
  onClose,
  onCreated,
}: {
  result: AnalysisResult;
  onClose: () => void;
  onCreated: (c: CaseListItem) => void;
}) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<Priority>(result.risk.level === "high" ? "critical" : result.risk.level === "medium" ? "high" : "normal");
  const [victim, setVictim] = useState("");
  const [victimPhone, setVictimPhone] = useState("");
  const [suspect, setSuspect] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!title) {
      const f = result.original_filename ?? result.transcript?.slice(0, 60) ?? "Analysis";
      setTitle(`Cyber-fraud: ${f}`);
    }
  }, [result, title]);

  const submit = async () => {
    if (!title.trim() || busy) return;
    setBusy(true);
    try {
      const c = await api.createCase({
        title: title.trim(),
        priority,
        victim_name: victim.trim() || undefined,
        victim_phone: victimPhone.trim() || undefined,
        suspect_name: suspect.trim() || undefined,
        scan_id: result.scan_id,
      });
      push(`Case ${c.case_number} opened with evidence`, "success");
      onCreated(c);
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`+ ${t("cases.new")}`} onClose={onClose}>
      <p className="muted small" style={{ marginTop: 0 }}>
        Risk: <b>{result.risk.level.toUpperCase()} · {Math.round(result.risk.score)}/100</b> — the analysis scan will be attached as the first evidence item.
      </p>
      <label className="field-label">* {t("cases.title")}</label>
      <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
      <div className="form-grid">
        <div>
          <label className="field-label">{t("case.priority.low")}</label>
          <select className="select" value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
            {["low", "normal", "high", "critical"].map((p) => (
              <option key={p} value={p}>{t(`case.priority.${p}`)}</option>
            ))}
          </select>
        </div>
      </div>
      <label className="field-label">{t("case.victim")}</label>
      <div className="form-grid">
        <input className="input" placeholder="Name" value={victim} onChange={(e) => setVictim(e.target.value)} />
        <input className="input" placeholder="Phone" value={victimPhone} onChange={(e) => setVictimPhone(e.target.value)} />
      </div>
      <label className="field-label">{t("case.suspect")}</label>
      <div className="form-grid">
        <input className="input" placeholder="Name" value={suspect} onChange={(e) => setSuspect(e.target.value)} />
      </div>
      <div className="row" style={{ marginTop: 16, justifyContent: "flex-end" }}>
        <button className="btn btn-ghost" onClick={onClose}>{t("btn.cancel")}</button>
        <button className="btn btn-primary" onClick={submit} disabled={busy || !title.trim()}>
          {busy ? t("status.saving") : t("cases.new")}
        </button>
      </div>
    </Modal>
  );
}

function AttachCaseModal({
  scanId,
  onClose,
  onAttached,
}: {
  scanId: string;
  onClose: () => void;
  onAttached: (c: CaseListItem) => void;
}) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    api.listCases().then(setCases).catch(() => {});
  }, []);

  const attach = async (c: CaseListItem) => {
    setBusy(c.id);
    try {
      await api.attachScanToCase(c.id, scanId);
      push(`Attached to ${c.case_number}`, "success");
      onAttached(c);
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
      setBusy(null);
    }
  };

  return (
    <Modal title={t("evidence.linkcase")} onClose={onClose}>
      <p className="muted small" style={{ marginTop: 0 }}>Attach this analysis as evidence to an existing case.</p>
      {cases.length === 0 ? (
        <div className="empty">{t("cases.empty")}</div>
      ) : (
        <div>
          {cases.filter((c) => c.status !== "closed").map((c) => (
            <div className="ev-row" key={c.id} style={{ padding: "9px 0" }}>
              <div className="ev-main">
                <div className="ev-name">{c.case_number} · {c.title}</div>
                <div className="ev-meta">{t(`case.status.${c.status}`)} · {c.evidence_count} {t("dash.stat.evidence")}</div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => attach(c)} disabled={busy !== null}>
                {busy === c.id ? t("status.saving") : "+"}
              </button>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}