import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { FileDropzone } from "../components/FileDropzone";
import { Modal } from "../components/Modal";
import { useToasts } from "../components/Toast";
import { useI18n } from "../i18n";
import type { CaseListItem, Evidence } from "../types";
import { downloadBlob, fmtBytes, fmtDate, shortHash } from "../utils";

export function EvidencePage() {
  const { t } = useI18n();
  const { push } = useToasts();
  const [items, setItems] = useState<Evidence[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [media, setMedia] = useState("");
  const [risk, setRisk] = useState("");
  const [showUpload, setShowUpload] = useState(false);

  const refresh = useCallback(async (q: string, m: string, r: string) => {
    setLoading(true);
    try {
      const res = await api.listEvidence({ search: q || undefined, media_type: m || undefined, risk_level: r || undefined });
      setItems(res.items);
      setTotal(res.total);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const id = setTimeout(() => refresh(search, media, risk), 280);
    return () => clearTimeout(id);
  }, [search, media, risk, refresh]);

  return (
    <div className="page">
      <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
        <div>
          <h1>{t("evidence.title")}</h1>
          <p>{t("evidence.sub")}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
          + {t("evidence.upload")}
        </button>
      </div>

      <div className="filters">
        <input className="input" placeholder={t("evidence.search")} value={search} onChange={(e) => setSearch(e.target.value)} />
        <select className="select" value={media} onChange={(e) => setMedia(e.target.value)}>
          <option value="">{t("evidence.filter.type")}: all</option>
          <option value="audio">audio</option>
          <option value="video">video</option>
          <option value="text">text</option>
        </select>
        <select className="select" value={risk} onChange={(e) => setRisk(e.target.value)}>
          <option value="">{t("evidence.filter.risk")}: all</option>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </select>
      </div>

      {err && <div className="error-banner">{err}</div>}
      {loading ? (
        <div className="center"><div className="spinner" /></div>
      ) : items.length === 0 ? (
        <div className="empty"><div className="empty-ico">⬡</div>{t("evidence.empty")}</div>
      ) : (
        <div className="card card-flush">
          <div className="faint small" style={{ padding: "8px 12px 2px" }}>{total} {t("dash.stat.evidence")}</div>
          {items.map((e) => (
            <EvidenceRowFull key={e.id} e={e} push={push} onRefresh={() => refresh(search, media, risk)} />
          ))}
        </div>
      )}

      {showUpload && <UploadEvidenceModal onClose={() => setShowUpload(false)} onDone={() => refresh(search, media, risk)} />}
    </div>
  );
}

function EvidenceRowFull({ e, push, onRefresh }: { e: Evidence; push: (m: string, tone?: "info" | "success" | "error") => void; onRefresh?: () => void }) {
  const { t } = useI18n();
  const [verifyResult, setVerifyResult] = useState<string | null>(null);
  const [showLink, setShowLink] = useState(false);

  const verify = async () => {
    try {
      const r = await api.verifyEvidence(e.id);
      setVerifyResult(r.matches ? t("evidence.verified") : t("evidence.mismatch"));
      push(r.matches ? "SHA-256 ✓" : "SHA-256 MISMATCH", r.matches ? "success" : "error");
    } catch (err) {
      push(err instanceof Error ? err.message : "error", "error");
    }
  };

  const download = async () => {
    try {
      const blob = await api.downloadEvidence(e.id);
      downloadBlob(blob, e.original_filename || e.filename);
    } catch (err) {
      push(err instanceof Error ? err.message : "error", "error");
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete evidence "${e.original_filename}"?`)) return;
    try {
      await api.deleteEvidence(e.id);
      push("Deleted", "success");
    } catch (err) {
      push(err instanceof Error ? err.message : "error", "error");
    }
  };

  return (
    <div className="ev-row">
      <div className="ev-ico">{e.media_type === "audio" ? "🎙️" : e.media_type === "video" ? "🎞️" : "📄"}</div>
      <div className="ev-main">
        <div className="ev-name">{e.original_filename}</div>
        <div className="ev-meta">
          {shortHash(e.sha256)} · {fmtBytes(e.size_bytes)} · {fmtDate(e.uploaded_at)}
          {e.case_number ? ` · 📁 ${e.case_number}` : ""}
        </div>
        <div className="row" style={{ gap: 6, margin: "4px 0 0" }}>
          <Badge tone={e.media_type || "type"}>{e.media_type ?? "—"}</Badge>
          {e.risk_level && <Badge tone={e.risk_level}>{e.risk_level}{e.risk_score != null ? ` · ${Math.round(e.risk_score)}` : ""}</Badge>}
          {verifyResult && <span className={`small ${verifyResult.includes("✓") ? "" : "warn"}`}>{verifyResult}</span>}
        </div>
      </div>
      <div className="ev-actions">
        <button className="btn btn-secondary btn-sm" onClick={verify}>✓ {t("evidence.verify")}</button>
        <button className="btn btn-secondary btn-sm" onClick={() => setShowLink(true)}>📁</button>
        <button className="btn btn-secondary btn-sm" onClick={download}>⤓</button>
        <button className="btn btn-danger btn-sm" onClick={remove}>🗑</button>
      </div>
      {showLink && <LinkCaseModal evidenceId={e.id} onClose={() => setShowLink(false)} onLinked={onRefresh} />}
    </div>
  );
}

function LinkCaseModal({ evidenceId, onClose, onLinked }: { evidenceId: string; onClose: () => void; onLinked?: () => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listCases().then(setCases).catch(() => {});
  }, []);

  const link = async (c: CaseListItem) => {
    setBusy(true);
    try {
      await api.linkEvidence(evidenceId, c.id);
      push(`Linked to ${c.case_number}`, "success");
      onLinked?.();
      onClose();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={t("evidence.linkcase")} onClose={onClose}>
      {busy ? (
        <div className="center"><div className="spinner" /></div>
      ) : cases.length === 0 ? (
        <div className="empty">{t("cases.empty")}</div>
      ) : (
        <div>
          {cases.map((c) => (
            <div className="ev-row" key={c.id} style={{ padding: "9px 0" }}>
              <div className="ev-main">
                <div className="ev-name">{c.case_number} · {c.title}</div>
                <div className="ev-meta">{t(`case.status.${c.status}`)} · {c.evidence_count} {t("dash.stat.evidence")}</div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => link(c)}>+</button>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

function UploadEvidenceModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const upload = async () => {
    if (!file || busy) return;
    setBusy(true);
    try {
      await api.uploadEvidence(file, undefined, note.trim() || undefined);
      push(t("done"), "success");
      onDone();
      onClose();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={t("evidence.upload")} onClose={onClose}>
      <FileDropzone accept="audio/*,video/*,.wav,.mp3,.m4a,.ogg,.flac,.mp4,.mov,.webm,.amr,.txt,.jpg,.png" onFile={setFile} busy={busy} icon="📎" />
      <label className="field-label">{t("phone.notes")}</label>
      <input className="input" value={note} onChange={(e) => setNote(e.target.value)} />
      <p className="small warn-banner" style={{ marginTop: 12 }}>{t("evidence.tamper.note")}</p>
      <div className="row" style={{ marginTop: 12, justifyContent: "flex-end" }}>
        <button className="btn btn-ghost" onClick={onClose}>{t("btn.cancel")}</button>
        <button className="btn btn-primary" onClick={upload} disabled={busy || !file}>
          {busy ? t("status.uploading") : t("evidence.upload")}
        </button>
      </div>
    </Modal>
  );
}
