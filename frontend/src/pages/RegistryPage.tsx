import { useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { FileDropzone } from "../components/FileDropzone";
import { Modal } from "../components/Modal";
import { useToasts } from "../components/Toast";
import { pick, useI18n } from "../i18n";
import type { FamilyMember, Person, VerifyResult } from "../types";

type Tab = "family" | "persons";

export function RegistryPage() {
  const { t } = useI18n();
  const [tab, setTab] = useState<Tab>("family");

  return (
    <div className="page">
      <div className="page-head">
        <h1>{t("nav.registry")}</h1>
        <p>{t("registry.subtitle")}</p>
      </div>

      <div className="seg">
        <button className={`seg-btn ${tab === "family" ? "active" : ""}`} onClick={() => setTab("family")}>
          {t("registry.title")}
        </button>
        <button className={`seg-btn ${tab === "persons" ? "active" : ""}`} onClick={() => setTab("persons")}>
          {t("case.persons")}
        </button>
      </div>

      {tab === "family" ? <FamilyTab /> : <PersonsTab />}
    </div>
  );
}

/* ------------------------------------------------------------ family tab */
function FamilyTab() {
  const { t, lang } = useI18n();
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setMembers(await api.listMembers());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <>
      <AddMemberForm onAdded={refresh} />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="center"><div className="spinner" /></div>
      ) : members.length === 0 ? (
        <div className="empty"><div className="empty-ico">◉</div>{t("registry.empty")}</div>
      ) : (
        <div className="member-grid">
          {members.map((m) => (
            <MemberCard key={m.id} member={m} onDeleted={refresh} lang={lang} />
          ))}
        </div>
      )}
    </>
  );
}

function AddMemberForm({ onAdded }: { onAdded: () => void }) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    setErr(null);
    try {
      await api.createMember({
        name: name.trim(),
        relationship: relationship.trim() || undefined,
        phone: phone.trim() || undefined,
      });
      setName("");
      setRelationship("");
      setPhone("");
      onAdded();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">{t("registry.add.title")}</div>
      {err && <div className="error-banner">{err}</div>}
      <div className="form-grid">
        <input className="input full" placeholder={t("field.name")} value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input" placeholder={t("field.relationship")} value={relationship} onChange={(e) => setRelationship(e.target.value)} />
        <input className="input" placeholder={t("field.phone")} value={phone} onChange={(e) => setPhone(e.target.value)} />
      </div>
      <button className="btn btn-primary" onClick={submit} disabled={busy || !name.trim()}>
        {t("btn.add")}
      </button>
    </div>
  );
}

function MemberCard({ member, onDeleted, lang }: { member: FamilyMember; onDeleted: () => void; lang: "en" | "hi" }) {
  const { t } = useI18n();
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<null | "enroll" | "verify">(null);

  const enroll = async (f: File | null) => {
    if (!f || busy) return;
    setBusy("enroll");
    setErr(null);
    try {
      await api.enrollMember(member.id, f);
      setMsg(t("enroll.done"));
      onDeleted();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(null);
    }
  };

  const verify = async (f: File | null) => {
    if (!f || busy) return;
    setBusy("verify");
    setErr(null);
    try {
      const r = await api.verifyVoice(member.id, f);
      setVerifyResult(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="card member">
      <div className="member-head">
        <div>
          <div className="member-name">{member.name}</div>
          <div className="muted small">
            {member.relationship ?? "—"}
            {member.phone ? ` · ${member.phone}` : ""}
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={async () => { await api.deleteMember(member.id); onDeleted(); }}>
          {t("btn.delete")}
        </button>
      </div>

      <div className="member-actions">
        <label className="btn btn-secondary btn-sm">
          {busy === "enroll" ? t("status.analyzing") : t("btn.enroll")}
          <input type="file" accept="audio/*,.wav,.mp3,.m4a,.ogg,.amr" hidden onChange={(e) => enroll(e.target.files?.[0] ?? null)} disabled={busy !== null} />
        </label>
        <label className="btn btn-secondary btn-sm">
          {busy === "verify" ? t("status.analyzing") : t("btn.verify")}
          <input type="file" accept="audio/*,.wav,.mp3,.m4a,.ogg,.amr" hidden onChange={(e) => verify(e.target.files?.[0] ?? null)} disabled={busy !== null} />
        </label>
      </div>

      <div className="muted small">{member.enrollments_count} {t("enroll.count")}</div>
      {msg && <div className="ok-banner">{msg}</div>}
      {err && <div className="error-banner">{err}</div>}
      {verifyResult && (
        <div className={`verify ${verifyResult.match ? "verify-ok" : "verify-warn"}`}>
          <strong>{verifyResult.match ? t("verify.match") : t("verify.no_match")} — {verifyResult.member_name}</strong>
          <div className="small">
            {t("verify.similarity")}: {(verifyResult.similarity * 100).toFixed(1)}% · {t("verify.threshold")}: {(verifyResult.threshold * 100).toFixed(0)}%
          </div>
          <div className="muted small">{pick(verifyResult.guidance[verifyResult.match ? "match" : "mismatch"], lang)}</div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------ persons tab */
function PersonsTab() {
  const { t } = useI18n();
  const { push } = useToasts();
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [showVoice, setShowVoice] = useState<Person | null>(null);

  const refresh = async () => {
    try {
      setPeople(await api.listPeople());
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const remove = async (p: Person) => {
    if (!window.confirm(`Delete profile "${p.name}"?`)) return;
    try {
      await api.deletePerson(p.id);
      push("Deleted", "success");
      await refresh();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };

  return (
    <>
      <div className="card">
        <div className="card-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="card-title">{t("case.persons")} ({people.length})</div>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowAdd(true)}>+ {t("case.addperson")}</button>
        </div>
        {loading ? (
          <div className="center"><div className="spinner" /></div>
        ) : people.length === 0 ? (
          <div className="empty">{t("cases.empty")}</div>
        ) : (
          <div>
            {people.map((p) => (
              <div className="ev-row" key={p.id}>
                <div className="ev-ico">👤</div>
                <div className="ev-main">
                  <div className="ev-name">{p.name}</div>
                  <div className="ev-meta">
                    {p.role}{p.phone ? ` · ${p.phone}` : ""}{p.id_number ? ` · ${p.id_number}` : ""}
                    {p.case_ids.length > 0 ? ` · ${p.case_ids.length} ${t("phone.linked.cases")}` : ""}
                  </div>
                </div>
                <Badge tone={roleTone(p.role)}>{t(`role.${p.role}`)}</Badge>
                <div className="ev-actions">
                  <button className="btn btn-secondary btn-sm" onClick={() => setShowVoice(p)}>♪ {t("btn.enroll")}</button>
                  <button className="btn btn-danger btn-sm" onClick={() => remove(p)}>🗑</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showAdd && <AddPersonModal onClose={() => setShowAdd(false)} onDone={refresh} />}
      {showVoice && <EnrollVoiceModal person={showVoice} onClose={() => setShowVoice(null)} onDone={refresh} />}
    </>
  );
}

function roleTone(role: string): string {
  if (role === "victim") return "low";
  if (role === "suspect") return "critical";
  if (role === "witness") return "open";
  if (role === "informant") return "medium";
  return "status";
}

function AddPersonModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [form, setForm] = useState({ name: "", role: "unknown", phone: "", id_type: "", id_number: "", address: "", notes: "" });
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!form.name.trim() || busy) return;
    setBusy(true);
    try {
      await api.createPerson({
        name: form.name.trim(),
        role: form.role,
        phone: form.phone.trim() || undefined,
        id_type: form.id_type.trim() || undefined,
        id_number: form.id_number.trim() || undefined,
        address: form.address.trim() || undefined,
        notes: form.notes.trim() || undefined,
      });
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
      <div className="form-grid">
        <input className="input" placeholder={t("field.name")} value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} autoFocus />
        <select className="select" value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}>
          {["victim", "suspect", "witness", "informant", "unknown"].map((r) => (
            <option key={r} value={r}>{t(`role.${r}`)}</option>
          ))}
        </select>
        <input className="input" placeholder="Phone" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
        <input className="input" placeholder={t("case.officer")} value={form.id_type} onChange={(e) => setForm((f) => ({ ...f, id_type: e.target.value }))} />
      </div>
      <input className="input" placeholder="ID number" value={form.id_number} onChange={(e) => setForm((f) => ({ ...f, id_number: e.target.value }))} style={{ marginTop: 10 }} />
      <input className="input" placeholder="Address" value={form.address} onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))} style={{ marginTop: 10 }} />
      <input className="input" placeholder={t("phone.notes")} value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} style={{ marginTop: 10 }} />
      <button className="btn btn-primary btn-block" onClick={submit} disabled={busy || !form.name.trim()} style={{ marginTop: 14 }}>
        {busy ? t("status.saving") : t("btn.save")}
      </button>
    </Modal>
  );
}

function EnrollVoiceModal({ person, onClose, onDone }: { person: Person; onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const enroll = async () => {
    if (!file || busy) return;
    setBusy(true);
    try {
      await api.enrollPersonVoice(person.id, file);
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
    <Modal title={`♪ ${t("btn.enroll")} — ${person.name}`} onClose={onClose}>
      <FileDropzone accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac,.amr" onFile={setFile} busy={busy} icon="🎙️" />
      <button className="btn btn-primary btn-block" onClick={enroll} disabled={busy || !file} style={{ marginTop: 12 }}>
        {busy ? t("status.matching") : t("btn.enroll")}
      </button>
    </Modal>
  );
}
