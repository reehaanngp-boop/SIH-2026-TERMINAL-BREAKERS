import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { Modal } from "../components/Modal";
import { useToasts } from "../components/Toast";
import { useI18n } from "../i18n";
import type { CaseListItem, CaseStatus, Priority } from "../types";
import { fmtDate } from "../utils";

const PRIORITIES: Priority[] = ["low", "normal", "high", "critical"];
const STATUSES: (CaseStatus | "")[] = ["", "open", "investigating", "closed"];

export function CasesPage({ navigate }: { navigate: (r: string) => void }) {
  const { t } = useI18n();
  const { push } = useToasts();
  const [items, setItems] = useState<CaseListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CaseStatus | "">("");
  const [showNew, setShowNew] = useState(false);

  const refresh = useCallback(
    async (q: string, st: string) => {
      setLoading(true);
      try {
        setItems(await api.listCases({ search: q || undefined, status: st || undefined }));
        setErr(null);
      } catch (e) {
        setErr(e instanceof Error ? e.message : "error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    const id = setTimeout(() => refresh(search, status), 280);
    return () => clearTimeout(id);
  }, [search, status, refresh]);

  return (
    <div className="page">
      <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
        <div>
          <h1>{t("cases.title")}</h1>
          <p>{t("cases.sub")}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowNew(true)}>
          + {t("cases.new")}
        </button>
      </div>

      <div className="filters">
        <input
          className="input"
          placeholder={t("cases.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="select" value={status} onChange={(e) => setStatus(e.target.value as CaseStatus | "")}>
          {STATUSES.map((s) => (
            <option key={s || "all"} value={s}>
              {s ? t(`case.status.${s}`) : `${t("field.status")}: all`}
            </option>
          ))}
        </select>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {loading ? (
        <div className="center">
          <div className="spinner" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty">
          <div className="empty-ico">▤</div>
          {t("cases.empty")}
        </div>
      ) : (
        <div className="card table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>#</th>
                <th>{t("cases.title")}</th>
                <th>{t("field.status")}</th>
                <th>{t("case.priority")}</th>
                <th>{t("case.officer")}</th>
                <th>{t("case.victim")}</th>
                <th className="text-right">{t("dash.stat.evidence")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="row-click" onClick={() => navigate(`/cases/${c.id}`)}>
                  <td className="mono-xs">{c.case_number}</td>
                  <td>
                    <b>{c.title}</b>
                    <div className="faint small">{fmtDate(c.created_at)}</div>
                  </td>
                  <td>
                    <Badge tone={c.status}>{t(`case.status.${c.status}`)}</Badge>
                  </td>
                  <td>
                    <Badge tone={c.priority === "critical" ? "critical" : "priority"}>{t(`case.priority.${c.priority}`)}</Badge>
                  </td>
                  <td className="small">{c.officer_name ?? "—"}</td>
                  <td className="small">{c.victim_name ?? "—"}</td>
                  <td className="text-right tnum">{c.evidence_count}</td>
                  <td className="text-right">
                    <button className="link">→</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <NewCaseModal
          onClose={() => setShowNew(false)}
          onCreated={(c) => {
            setShowNew(false);
            push(`Case ${c.case_number} opened`, "success");
            navigate(`/cases/${c.id}`);
          }}
        />
      )}
    </div>
  );
}

function NewCaseModal({ onClose, onCreated }: { onClose: () => void; onCreated: (c: CaseListItem) => void }) {
  const { t } = useI18n();
  const [form, setForm] = useState({
    title: "",
    description: "",
    priority: "high" as Priority,
    victim_name: "",
    victim_phone: "",
    suspect_name: "",
    suspect_phone: "",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    if (!form.title.trim() || busy) return;
    setBusy(true);
    setErr(null);
    try {
      const created = await api.createCase({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        priority: form.priority,
        victim_name: form.victim_name.trim() || undefined,
        victim_phone: form.victim_phone.trim() || undefined,
        suspect_name: form.suspect_name.trim() || undefined,
        suspect_phone: form.suspect_phone.trim() || undefined,
      });
      onCreated(created);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={t("cases.new")} onClose={onClose}>
      {err && <div className="error-banner">{err}</div>}
      <label className="field-label">* {t("cases.title")}</label>
      <input className="input" value={form.title} onChange={set("title")} autoFocus />
      <label className="field-label">{t("field.description")}</label>
      <textarea className="textarea" value={form.description} onChange={set("description")} rows={3} />
      <div className="form-grid">
        <div>
          <label className="field-label">{t("case.priority")}</label>
          <select className="select" value={form.priority} onChange={set("priority")}>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t(`case.priority.${p}`)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <label className="field-label">{t("case.victim")}</label>
      <div className="form-grid">
        <input className="input" placeholder={t("field.name")} value={form.victim_name} onChange={set("victim_name")} />
        <input className="input" placeholder={t("field.phone")} value={form.victim_phone} onChange={set("victim_phone")} />
      </div>
      <label className="field-label">{t("case.suspect")}</label>
      <div className="form-grid">
        <input className="input" placeholder={t("field.name")} value={form.suspect_name} onChange={set("suspect_name")} />
        <input className="input" placeholder={t("field.phone")} value={form.suspect_phone} onChange={set("suspect_phone")} />
      </div>
      <div className="row" style={{ marginTop: 16, justifyContent: "flex-end" }}>
        <button className="btn btn-ghost" onClick={onClose}>
          {t("btn.cancel")}
        </button>
        <button className="btn btn-primary" onClick={submit} disabled={busy || !form.title.trim()}>
          {busy ? t("status.saving") : t("cases.new")}
        </button>
      </div>
    </Modal>
  );
}
