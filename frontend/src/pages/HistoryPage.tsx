import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { ResultView } from "../components/Results";
import { useToasts } from "../components/Toast";
import { useI18n } from "../i18n";
import type { AnalysisResult, ScanListItem } from "../types";
import { downloadBlob, fmtDate } from "../utils";

export function HistoryPage() {
  const { t } = useI18n();
  const { push } = useToasts();
  const [items, setItems] = useState<ScanListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<AnalysisResult | null>(null);
  const [search, setSearch] = useState("");
  const [media, setMedia] = useState("");

  useEffect(() => {
    api
      .getHistory(100)
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : "error"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter(
      (s) =>
        (!q || (s.original_filename ?? s.scan_id).toLowerCase().includes(q)) &&
        (!media || s.media_type === media),
    );
  }, [items, search, media]);

  const exportCsv = async () => {
    try {
      const blob = await api.exportScans();
      downloadBlob(blob, `digiraksha-scans-${new Date().toISOString().slice(0, 10)}.csv`);
      push(t("done"), "success");
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };

  const open = async (scanId: string) => {
    try {
      setDetail(await api.getResult(scanId));
    } catch (e) {
      push(e instanceof Error ? e.message : "error", "error");
    }
  };

  return (
    <div className="page">
      <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
        <div>
          <h1>{t("nav.history")}</h1>
          <p>{t("registry.subtitle")}</p>
        </div>
        <button className="btn btn-secondary" onClick={exportCsv}>⤓ CSV</button>
      </div>

      {detail ? (
        <div>
          <button className="btn btn-ghost" onClick={() => setDetail(null)}>← {t("btn.back")}</button>
          <ResultView result={detail} />
        </div>
      ) : (
        <>
          {error && <div className="error-banner">{error}</div>}
          <div className="filters">
            <input className="input" placeholder={t("evidence.search")} value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="select" value={media} onChange={(e) => setMedia(e.target.value)}>
              <option value="">{t("evidence.filter.type")}: all</option>
              <option value="audio">audio</option>
              <option value="video">video</option>
              <option value="text">text</option>
            </select>
          </div>

          {loading ? (
            <div className="center"><div className="spinner" /></div>
          ) : filtered.length === 0 ? (
            <div className="empty">{t("history.empty")}</div>
          ) : (
            <div className="card table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{t("history.col.time")}</th>
                    <th>{t("history.col.type")}</th>
                    <th>{t("history.col.file")}</th>
                    <th>{t("history.col.risk")}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => (
                    <tr key={s.scan_id} className="row-click" onClick={() => s.status === "completed" && open(s.scan_id)}>
                      <td className="muted small">{fmtDate(s.created_at)}</td>
                      <td><Badge tone="type">{s.media_type}</Badge></td>
                      <td className="small">{s.original_filename ?? s.scan_id.slice(0, 8)}</td>
                      <td>
                        {s.risk_level ? (
                          <Badge tone={s.risk_level}>
                            {s.risk_level}{s.risk_score != null ? ` · ${Math.round(s.risk_score)}` : ""}
                          </Badge>
                        ) : (
                          <Badge tone="status">{s.status}</Badge>
                        )}
                      </td>
                      <td className="text-right">
                        {s.status === "completed" && s.risk_level ? <span className="link">→</span> : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
