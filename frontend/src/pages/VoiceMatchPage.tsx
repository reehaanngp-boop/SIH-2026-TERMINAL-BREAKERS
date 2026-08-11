import { useState } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { FileDropzone } from "../components/FileDropzone";
import { useI18n } from "../i18n";
import type { VoiceMatchResult } from "../types";

export function VoiceMatchPage() {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<VoiceMatchResult | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const match = async () => {
    if (!file || busy) return;
    setBusy(true);
    setErr(null);
    try {
      setResult(await api.voiceMatch(file));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <h1>{t("vm.title")}</h1>
        <p>{t("vm.sub")}</p>
      </div>

      <div className="card">
        <FileDropzone accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac,.amr" onFile={setFile} busy={busy} icon="🎙️" help={t("vm.upload")} />
        <button className="btn btn-primary btn-block" onClick={match} disabled={busy || !file} style={{ marginTop: 12 }}>
          {busy ? t("status.matching") : t("vm.matches")}
        </button>
        {err && <div className="error-banner">{err}</div>}
      </div>

      {result && (
        <div className="card">
          <div className="card-title">
            {t("vm.matches")}
            {result.query_duration_seconds != null && (
              <span className="muted small"> · {Math.round(result.query_duration_seconds)}s clip · {t("vm.threshold")}: {(result.threshold * 100).toFixed(0)}%</span>
            )}
          </div>
          {result.matches.length === 0 ? (
            <div className="empty">{t("vm.none")}</div>
          ) : (
            <div>
              {result.matches.map((m, i) => (
                <div className="vm-row" key={`${m.owner_kind}-${m.owner_id}`}>
                  <span className="vm-rank">#{i + 1}</span>
                  <div className="vm-main">
                    <div className="vm-name">
                      {m.label} <span className="vm-ref">· {m.owner_kind}{m.owner_ref ? ` / ${m.owner_ref}` : ""}</span>
                    </div>
                    <div className="vm-bar">
                      <i
                        style={{
                          width: `${Math.min(100, Math.round(m.similarity * 100))}%`,
                          background: m.match ? "#2dd4bf" : "#5c6a7d",
                        }}
                      />
                    </div>
                  </div>
                  <Badge tone={m.match ? "open" : "status"}>{m.match ? t("vm.match") : t("vm.no_match")}</Badge>
                  <span className="vm-pct">{(m.similarity * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
