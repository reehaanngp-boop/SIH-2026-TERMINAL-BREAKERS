import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { FileDropzone } from "../components/FileDropzone";
import { Modal } from "../components/Modal";
import { useToasts } from "../components/Toast";
import { useI18n } from "../i18n";
import type { CaseDetail, Evidence, Person } from "../types";
import { downloadBlob, fmtBytes, fmtDate, shortHash } from "../utils";

export function CaseDetailPage({ id, navigate }: { id: string; navigate: (r: string) => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [c, setC] = useState<CaseDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [showAddPerson, setShowAddPerson] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setC(await api.getCase(id));
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (err) {
    return (
      <div className="page">
        <button className="btn btn-ghost" onClick={() => navigate("/cases")}>← {t("btn.back")}</button>
        <div className="error-banner">{err}</div>
      </div>
    );
  }
  if (!c) {
    return (
      <div className="center">
        <div className="spinner" />
        <p>{t("status.loading")}</p>
      </div>
    );
  }

  const exportPdf = async () => {
    try {
      const blob = await api.caseReportPdf(c.id);
      downloadBlob(blob, `${c.case_number}.pdf`);
      push(t("done"), "success");
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };

  const setStatus = async (st: string) => {
    setBusy(true);
    try {
      await api.setCaseStatus(c.id, st);
      await load();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setBusy(false);
    }
  };

  const addNote = async () => {
    if (!note.trim()) return;
    setBusy(true);
    try {
      await api.addCaseNote(c.id, note.trim());
      setNote("");
      await load();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setBusy(false);
    }
  };

  const deleteCase = async () => {
    if (!window.confirm(`Delete ${c.case_number}? This cannot be undone.`)) return;
    try {
      await api.deleteCase(c.id);
      push("Case deleted", "success");
      navigate("/cases");
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };

  return (
    <div className="page">
      <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <button className="link small" onClick={() => navigate("/cases")}>← {t("cases.title")}</button>
          <h1 style={{ marginTop: 6 }}>
            <span className="mono-xs faint">{c.case_number}</span> · {c.title}
          </h1>
          <div className="row" style={{ gap: 8, margin: "6px 0 0" }}>
            <Badge tone={c.status}>{t(`case.status.${c.status}`)}</Badge>
            <Badge tone={c.priority === "critical" ? "critical" : "priority"}>{t(`case.priority.${c.priority}`)}</Badge>
            {c.officer_name && <span className="small muted">👮 {c.officer_name}{c.officer_badge ? ` (${c.officer_badge})` : ""}</span>}
          </div>
        </div>
        <div className="row" style={{ gap: 8, margin: 0 }}>
          <button className="btn btn-secondary" onClick={exportPdf}>⤓ {t("case.pdf")}</button>
          {c.status === "open" && (
            <button className="btn btn-secondary" onClick={() => setStatus("investigating")} disabled={busy}>
              {t("case.setinvestigating")}
            </button>
          )}
          {c.status === "investigating" && (
            <button className="btn btn-secondary" onClick={() => setStatus("closed")} disabled={busy}>
              {t("case.setclosed")}
            </button>
          )}
          {c.status === "closed" && (
            <button className="btn btn-secondary" onClick={() => setStatus("open")} disabled={busy}>
              {t("case.setopen")}
            </button>
          )}
          <button className="btn btn-danger" onClick={deleteCase}>🗑</button>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">{t("case.victim")}</div>
          <div className="muted small">{c.victim_name ?? "—"}{c.victim_phone ? ` · ${c.victim_phone}` : ""}</div>
          <div className="card-title" style={{ marginTop: 14 }}>{t("case.suspect")}</div>
          <div className="muted small">{c.suspect_name ?? "—"}{c.suspect_phone ? ` · ${c.suspect_phone}` : ""}</div>
        </div>
        <div className="card">
          <div className="card-title">Timeline</div>
          <div className="muted small">
            {t("case.officer")}: <b>{c.officer_name ?? "—"}</b>
            <br />Opened: {fmtDate(c.created_at)}
            {c.updated_at ? (
              <>
                <br />Updated: {fmtDate(c.updated_at)}
              </>
            ) : null}
            {c.closed_at ? (
              <>
                <br />Closed: {fmtDate(c.closed_at)}
              </>
            ) : null}
          </div>
        </div>
      </div>

      {c.description && (
        <div className="card">
          <div className="card-title">Description</div>
          <p className="muted small" style={{ margin: 0 }}>{c.description}</p>
        </div>
      )}

      {/* Persons */}
      <div className="card">
        <div className="card-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="card-title">{t("case.persons")} ({c.persons.length})</div>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowAddPerson(true)}>
            + {t("case.addperson")}
          </button>
        </div>
        {c.persons.length === 0 ? (
          <div className="empty" style={{ padding: 16 }}>{t("cases.empty")}</div>
        ) : (
          <div>
            {c.persons.map((p) => (
              <PersonRow key={p.id} p={p} caseId={c.id} onChanged={load} />
            ))}
          </div>
        )}
      </div>

      {/* Evidence */}
      <div className="card">
        <div className="card-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="card-title">{t("case.evidence")} ({c.evidence.length})</div>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowUpload(true)}>
            + {t("case.uploadevidence")}
          </button>
        </div>
        {c.evidence.length === 0 ? (
          <div className="empty" style={{ padding: 16 }}>{t("evidence.empty")}</div>
        ) : (
          <div>
            {c.evidence.map((e) => (
              <EvidenceRow key={e.id} e={e} push={push} />
            ))}
          </div>
        )}
      </div>

      {/* Notes */}
      <div className="card">
        <div className="card-title">{t("case.notes")}</div>
        <div className="row" style={{ margin: "10px 0 0" }}>
          <input
            className="input"
            placeholder={t("case.addnote")}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addNote()}
          />
          <button className="btn btn-secondary" onClick={addNote} disabled={busy || !note.trim()}>
            {t("case.addnote")}
          </button>
        </div>
        {c.notes ? <p className="small muted" style={{ whiteSpace: "pre-wrap" }}>{c.notes}</p> : null}
      </div>

      {/* Audit timeline */}
      <div className="card">
        <div className="card-title">{t("case.timeline")}</div>
        {c.events.length === 0 ? (
          <div className="empty" style={{ padding: 12 }}>{t("cases.empty")}</div>
        ) : (
          <ul className="timeline">
            {c.events.map((ev) => (
              <li key={ev.id} className={`tl-item ${ev.action === "deleted" ? "tl-alt" : ""}`}>
                <div className="tl-time">{fmtDate(ev.created_at)}</div>
                <div className="tl-action">
                  {ev.action} {ev.actor ? <span className="faint small">· {ev.actor}</span> : null}
                </div>
                {ev.detail && <div className="tl-detail">{ev.detail}</div>}
              </li>
            ))}
          </ul>
        )}
      </div>

      {showUpload && <UploadEvidenceModal caseId={c.id} onClose={() => setShowUpload(false)} onDone={load} />}
      {showAddPerson && <AddPersonModal caseId={c.id} onClose={() => setShowAddPerson(false)} onDone={load} />}
    </div>
  );
}

function PersonRow({ p, caseId, onChanged }: { p: Person; caseId: string; onChanged: () => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const unlink = async () => {
    try {
      await api.unlinkPersonFromCase(caseId, p.id);
      onChanged();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };
  return (
    <div className="ev-row">
      <div className="ev-ico">👤</div>
      <div className="ev-main">
        <div className="ev-name">{p.name}</div>
        <div className="ev-meta">
          {p.role} {p.phone ? ` · ${p.phone}` : ""}
          {p.voice_prints.length > 0 ? ` · ♪ ${p.voice_prints.length}` : ""}
        </div>
      </div>
      <button className="btn btn-ghost btn-sm" onClick={unlink}>
        {t("btn.cancel")}
      </button>
    </div>
  );
}

export function EvidenceRow({ e, push }: { e: Evidence; push: (m: string, tone?: "info" | "success" | "error") => void }) {
  const { t } = useI18n();
  const verify = async () => {
    try {
      const r = await api.verifyEvidence(e.id);
      push(r.matches ? `${t("evidence.verified")} ${e.sha256.slice(0, 8)}` : `${t("evidence.mismatch")}`, r.matches ? "success" : "error");
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
  return (
    <div className="ev-row">
      <div className="ev-ico">{e.media_type === "audio" ? "🎙️" : e.media_type === "video" ? "🎞️" : "📄"}</div>
      <div className="ev-main">
        <div className="ev-name">{e.original_filename}</div>
        <div className="ev-meta">
          SHA-256 {shortHash(e.sha256)} · {fmtBytes(e.size_bytes)} · {fmtDate(e.uploaded_at)}
        </div>
        <div className="row" style={{ gap: 6, margin: "4px 0 0" }}>
          {e.risk_level && <Badge tone={e.risk_level}>{e.risk_level}</Badge>}
        </div>
      </div>
      <div className="ev-actions">
        <button className="btn btn-secondary btn-sm" onClick={verify}>✓ {t("evidence.verify")}</button>
        <button className="btn btn-secondary btn-sm" onClick={download}>⤓</button>
      </div>
    </div>
  );
}

function UploadEvidenceModal({ caseId, onClose, onDone }: { caseId: string; onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const upload = async () => {
    if (!file || busy) return;
    setBusy(true);
    try {
      await api.uploadEvidence(file, caseId, note.trim() || undefined);
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
      <div className="row" style={{ marginTop: 14, justifyContent: "flex-end" }}>
        <button className="btn btn-ghost" onClick={onClose}>{t("btn.cancel")}</button>
        <button className="btn btn-primary" onClick={upload} disabled={busy || !file}>
          {busy ? t("status.uploading") : t("evidence.upload")}
        </button>
      </div>
    </Modal>
  );
}

function AddPersonModal({ caseId, onClose, onDone }: { caseId: string; onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [people, setPeople] = useState<Person[]>([]);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", role: "witness", phone: "" });

  useEffect(() => {
    api.listPeople().then(setPeople).catch(() => {});
  }, []);

  const link = async (p: Person) => {
    try {
      await api.linkPersonToCase(caseId, p.id);
      push(t("done"), "success");
      onDone();
      onClose();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };

  const create = async () => {
    if (!form.name.trim() || busy) return;
    setBusy(true);
    try {
      const p = await api.createPerson({ name: form.name.trim(), role: form.role, phone: form.phone.trim() || undefined });
      await api.linkPersonToCase(caseId, p.id);
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
    <Modal title={t("case.addperson")} onClose={onClose}>
      <label className="field-label">{t("case.persons")} — {t("field.officer")}?</label>
      <div className="form-grid">
        <input className="input" placeholder="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
        <select className="select" value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}>
          {["victim", "suspect", "witness", "informant", "unknown"].map((r) => (
            <option key={r} value={r}>{t(`role.${r}`)}</option>
          ))}
        </select>
      </div>
      <input className="input" placeholder="Phone" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} style={{ marginTop: 10 }} />
      <button className="btn btn-primary btn-block" onClick={create} disabled={busy || !form.name.trim()} style={{ marginTop: 12 }}>
        {busy ? t("status.saving") : t("case.addperson")}
      </button>

      <h3>Existing profiles</h3>
      {people.length === 0 ? (
        <div className="empty" style={{ padding: 12 }}>{t("cases.empty")}</div>
      ) : (
        <div>
          {people.map((p) => (
            <div className="ev-row" key={p.id} style={{ padding: "8px 0" }}>
              <div className="ev-ico">👤</div>
              <div className="ev-main">
                <div className="ev-name">{p.name}</div>
                <div className="ev-meta">{p.role}{p.phone ? ` · ${p.phone}` : ""}</div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => link(p)}>+</button>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
