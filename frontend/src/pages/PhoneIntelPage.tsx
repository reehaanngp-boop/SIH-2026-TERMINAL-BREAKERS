import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { useToasts } from "../components/Toast";
import { useI18n } from "../i18n";
import type { PhoneLookup, PhoneRecord } from "../types";
import { fmtDate } from "../utils";

export function PhoneIntelPage() {
  const { t } = useI18n();
  const { push } = useToasts();
  const [records, setRecords] = useState<PhoneRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [lookupNum, setLookupNum] = useState("");
  const [lookup, setLookup] = useState<PhoneLookup | null>(null);
  const [lookupBusy, setLookupBusy] = useState(false);
  const [reportNum, setReportNum] = useState("");
  const [reportNotes, setReportNotes] = useState("");
  const [reportBusy, setReportBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setRecords(await api.listReportedNumbers());
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setLoading(false);
    }
  }, [push]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const lookupNumFn = async () => {
    if (!lookupNum.trim() || lookupBusy) return;
    setLookupBusy(true);
    setLookup(null);
    try {
      setLookup(await api.lookupPhone(lookupNum.trim()));
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setLookupBusy(false);
    }
  };

  const report = async () => {
    if (!reportNum.trim() || reportBusy) return;
    setReportBusy(true);
    try {
      await api.reportPhone(reportNum.trim(), reportNotes.trim() || undefined);
      setReportNum("");
      setReportNotes("");
      push(t("done"), "success");
      await refresh();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    } finally {
      setReportBusy(false);
    }
  };

  const setStatus = async (r: PhoneRecord, status: string) => {
    try {
      await api.setPhoneStatus(r.id, status);
      await refresh();
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <h1>{t("phone.title")}</h1>
        <p>{t("phone.sub")}</p>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">{t("phone.lookup")}</div>
          <div className="row" style={{ margin: "10px 0 0" }}>
            <input className="input" placeholder={t("phone.lookup.ph")} value={lookupNum} onChange={(e) => setLookupNum(e.target.value)} onKeyDown={(e) => e.key === "Enter" && lookupNumFn()} />
            <button className="btn btn-secondary" onClick={lookupNumFn} disabled={lookupBusy || !lookupNum.trim()}>
              {t("phone.lookup")}
            </button>
          </div>
          {lookup && (
            <div className={`card-flush verify ${lookup.found ? "verify-ok" : "verify-warn"}`} style={{ marginTop: 12 }}>
              <div className="card-title">
                {lookup.found ? t("phone.found") : t("phone.notfound")}
              </div>
              {lookup.found && lookup.record && (
                <div className="small">
                  <div><b>{lookup.record.phone}</b> · <Badge tone={statusTone(lookup.record.status)}>{t(`phone.status.${lookup.record.status}`)}</Badge></div>
                  <div className="muted">{t("evidence.date")} {fmtDate(lookup.record.first_seen)} · {lookup.record.count}×</div>
                  {lookup.record.notes && <div className="muted">{lookup.record.notes}</div>}
                  {lookup.record.linked_cases.length > 0 && (
                    <div className="muted">{t("phone.linked.cases")}: {lookup.record.linked_cases.join(", ")}</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">{t("phone.report")}</div>
          <div className="row" style={{ margin: "10px 0 0" }}>
            <input className="input" placeholder={t("phone.report.ph")} value={reportNum} onChange={(e) => setReportNum(e.target.value)} />
          </div>
          <input className="input" placeholder={t("phone.notes")} value={reportNotes} onChange={(e) => setReportNotes(e.target.value)} style={{ marginTop: 10 }} />
          <button className="btn btn-primary btn-block" onClick={report} disabled={reportBusy || !reportNum.trim()} style={{ marginTop: 12 }}>
            {reportBusy ? t("status.saving") : t("phone.report")}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-title">{t("phone.reported.list")} ({records.length})</div>
        {loading ? (
          <div className="center"><div className="spinner" /></div>
        ) : records.length === 0 ? (
          <div className="empty">{t("phone.empty")}</div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t("field.phone_num")}</th>
                  <th>{t("field.status")}</th>
                  <th>{t("field.count")}</th>
                  <th>{t("evidence.date")}</th>
                  <th>{t("phone.linked.cases")}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id}>
                    <td className="mono">{r.phone}</td>
                    <td><Badge tone={statusTone(r.status)}>{t(`phone.status.${r.status}`)}</Badge></td>
                    <td className="tnum">{r.count}</td>
                    <td className="small muted">{fmtDate(r.last_seen)}</td>
                    <td className="small muted">{r.linked_cases.join(", ") || "—"}</td>
                    <td>
                      <select
                        className="select"
                        style={{ width: "auto", padding: "4px 26px 4px 8px", fontSize: 12 }}
                        value={r.status}
                        onChange={(e) => setStatus(r, e.target.value)}
                      >
                        {["reported", "verified_fraud", "cleared"].map((s) => (
                          <option key={s} value={s}>{t(`phone.status.${s}`)}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function statusTone(status: string): string {
  if (status === "cleared") return "low";
  if (status === "verified_fraud") return "critical";
  return "medium";
}
