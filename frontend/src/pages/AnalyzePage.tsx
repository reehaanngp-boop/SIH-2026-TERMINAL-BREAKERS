import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
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

/* ------------------------------------------------------------ forms (kept) */
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
