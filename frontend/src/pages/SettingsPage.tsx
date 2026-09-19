import { useEffect, useState } from "react";
import { api, getApiBase, setApiBase, getOpenRouterKey, setOpenRouterKey } from "../api";
import { useToasts } from "../components/Toast";
import { useI18n } from "../i18n";
import type { MetaInfo } from "../types";

export function SettingsPage() {
  const { t } = useI18n();
  const { push } = useToasts();
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Backend URL connection state
  const [backendUrl, setBackendUrl] = useState<string>(() => getApiBase() || "");
  const [testingBackend, setTestingBackend] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"ok" | "err" | null>(null);

  // OpenRouter state
  const [orKey, setOrKey] = useState<string>(() => getOpenRouterKey() || "");
  const [orTesting, setOrTesting] = useState(false);
  const [orStatus, setOrStatus] = useState<string | null>(null);

  useEffect(() => {
    api.getMeta().then(setMeta).catch(() => {});
  }, []);

  const changePin = async () => {
    if (next.length < 4 || next !== confirm) {
      setErr(t("field.pin"));
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await api.authChangePin(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      push(t("done"), "success");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const handleSaveOrKey = () => {
    setOpenRouterKey(orKey);
    push("OpenRouter API key updated", "success");
  };

  const handleTestOrKey = async () => {
    setOrTesting(true);
    setOrStatus(null);
    setOpenRouterKey(orKey);
    try {
      const res = await api.assistantStatus();
      if (res.available) {
        setOrStatus("success");
        push(t("settings.key_valid"), "success");
      } else {
        setOrStatus("error");
        push(res.reason || t("settings.key_invalid"), "error");
      }
    } catch {
      setOrStatus("error");
      push(t("settings.key_invalid"), "error");
    } finally {
      setOrTesting(false);
    }
  };

  const handleSaveBackendUrl = () => {
    setApiBase(backendUrl);
    push("Backend URL saved! Reloading...", "success");
    setTimeout(() => window.location.reload(), 500);
  };

  const handleTestBackendUrl = async () => {
    setTestingBackend(true);
    setBackendStatus(null);
    setApiBase(backendUrl);
    try {
      const res = await api.getMeta();
      if (res && res.name) {
        setBackendStatus("ok");
        push(`Connected to ${res.name} v${res.version} successfully!`, "success");
      } else {
        setBackendStatus("err");
        push("Connected, but unexpected payload returned.", "error");
      }
    } catch {
      setBackendStatus("err");
      push("Failed to connect to backend URL. Please ensure your tunnel is running.", "error");
    } finally {
      setTestingBackend(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <h1>{t("settings.title")}</h1>
        <p>{t("nav.dashboard")} · DigiRaksha</p>
      </div>

      <div className="grid grid-2">
        {/* Cloudflare Tunnel / Backend Connection */}
        <div className="card">
          <div className="card-title">🌐 Cloudflare Backend Tunnel Endpoint</div>
          <p className="muted small" style={{ marginBottom: 12 }}>
            Configure your active FastAPI backend URL. Allows seamless team collaboration with Cloudflare Tunnels (e.g. <code>https://your-tunnel.trycloudflare.com</code>).
          </p>

          <label className="field-label">Backend API URL</label>
          <input
            className="input"
            type="text"
            placeholder="https://your-tunnel.trycloudflare.com or http://127.0.0.1:8000"
            value={backendUrl}
            onChange={(e) => setBackendUrl(e.target.value)}
          />

          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ flex: 1 }}
              onClick={handleSaveBackendUrl}
            >
              Save Endpoint
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1 }}
              disabled={testingBackend}
              onClick={handleTestBackendUrl}
            >
              {testingBackend ? "Testing…" : "Test Connection"}
            </button>
            {backendUrl && (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  setBackendUrl("");
                  setApiBase(null);
                  push("Reset to default backend URL.", "info");
                  setTimeout(() => window.location.reload(), 500);
                }}
              >
                Reset
              </button>
            )}
          </div>
          {backendStatus === "ok" && (
            <div className="alert-box alert-success" style={{ marginTop: 10 }}>
              ✓ Backend active and reachable
            </div>
          )}
          {backendStatus === "err" && (
            <div className="error-banner" style={{ marginTop: 10 }}>
              ✕ Backend unreachable. Verify your cloudflared tunnel is running.
            </div>
          )}
        </div>

        {/* OpenRouter AI Config */}
        <div className="card">
          <div className="card-title">🤖 {t("settings.openrouter_title")}</div>
          <p className="muted small" style={{ marginBottom: 12 }}>
            {t("settings.openrouter_desc")}
          </p>

          <label className="field-label">{t("settings.openrouter_key")}</label>
          <input
            className="input"
            type="password"
            placeholder="sk-or-v1-..."
            value={orKey}
            onChange={(e) => setOrKey(e.target.value)}
          />

          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ flex: 1 }}
              onClick={handleSaveOrKey}
            >
              Save Key
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1 }}
              disabled={orTesting}
              onClick={handleTestOrKey}
            >
              {orTesting ? "Testing…" : t("settings.test_key")}
            </button>
          </div>

          {orStatus === "success" && (
            <div className="alert-box alert-success" style={{ marginTop: 10 }}>
              ✓ {t("settings.key_valid")}
            </div>
          )}
          {orStatus === "error" && (
            <div className="error-banner" style={{ marginTop: 10 }}>
              ✕ {t("settings.key_invalid")}
            </div>
          )}
        </div>

        {/* PIN Security */}
        <div className="card">
          <div className="card-title">{t("settings.pin.title")}</div>
          {err && <div className="error-banner">{err}</div>}
          <label className="field-label">{t("field.currentpin")}</label>
          <input
            className="input pin-input"
            type="password"
            inputMode="numeric"
            value={current}
            onChange={(e) => setCurrent(e.target.value.replace(/\D/g, ""))}
          />
          <label className="field-label">{t("field.newpin")}</label>
          <input
            className="input pin-input"
            type="password"
            inputMode="numeric"
            value={next}
            onChange={(e) => setNext(e.target.value.replace(/\D/g, ""))}
          />
          <label className="field-label">
            {t("field.newpin")} · {t("ok")}
          </label>
          <input
            className="input pin-input"
            type="password"
            inputMode="numeric"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value.replace(/\D/g, ""))}
          />
          <button
            className="btn btn-primary btn-block"
            onClick={changePin}
            disabled={busy}
            style={{ marginTop: 14 }}
          >
            {busy ? t("status.saving") : t("settings.changepin")}
          </button>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        {/* Detectors Status */}
        <div className="card">
          <div className="card-title">{t("settings.detectors")}</div>
          {!meta ? (
            <div className="center">
              <div className="spinner" />
            </div>
          ) : (
            <div>
              <div className="chips" style={{ marginTop: 4 }}>
                <span className={`chip ${meta.detectors.asr.available ? "chip-on" : "chip-off"}`}>
                  Whisper ASR
                </span>
                <span className={`chip ${meta.detectors.voice.available ? "chip-on" : "chip-off"}`}>
                  AASIST anti-spoof
                  {meta.detectors.voice.engine ? ` (${meta.detectors.voice.engine})` : ""}
                </span>
                <span className={`chip ${meta.detectors.video.available ? "chip-on" : "chip-off"}`}>
                  Deepfake frame scan
                </span>
                <span className={`chip ${meta.detectors.text.available ? "chip-on" : "chip-off"}`}>
                  Scam-script patterns
                </span>
                <span className="chip chip-on">OpenRouter AI Shield</span>
              </div>
              <div className="muted small" style={{ marginTop: 14 }}>
                {t("settings.about")}: DigiRaksha v{meta.version}
                <br />
                <span className="faint">{t("brand.tagline")}</span>
              </div>
            </div>
          )}
        </div>

        {/* Helpline */}
        <div className="card">
          <div className="card-title">Helpline & Escalation</div>
          <div className="result-report">
            <a className="btn btn-primary" href="tel:1930">
              1930
            </a>
            <a
              className="btn btn-secondary"
              href="https://cybercrime.gov.in"
              target="_blank"
              rel="noreferrer"
            >
              cybercrime.gov.in
            </a>
          </div>
          <p className="muted small" style={{ marginTop: 12 }}>
            National Cyber Crime Reporting Portal & Helpline (I4C, Ministry of Home Affairs).
          </p>
        </div>
      </div>
    </div>
  );
}
