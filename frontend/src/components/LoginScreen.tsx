import { useState } from "react";
import { api, setAuthToken } from "../api";
import { useI18n } from "../i18n";

export function LoginScreen({
  mode,
  onAuthed,
}: {
  mode: "setup" | "login";
  onAuthed: (officerName: string) => void;
}) {
  const { t } = useI18n();
  const [officer, setOfficer] = useState("");
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showVideos, setShowVideos] = useState(false);

  const submit = async () => {
    if (busy) return;
    if (mode === "setup" && !officer.trim()) { setErr(t("field.officer")); return; }
    if (pin.length < 4) { setErr(t("field.pin")); return; }

    setBusy(true);
    setErr(null);
    try {
      const res = mode === "setup"
        ? await api.authSetup(officer.trim(), pin)
        : await api.authLogin(pin);
      setAuthToken(res.token);
      onAuthed(res.officer_name);
    } catch (e) {
      setErr(e instanceof Error ? e.message : t("err.network"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        {/* Logo */}
        <div className="auth-logo">
          <div className="sidebar-logo">🛡️</div>
          <div>
            <div className="auth-title">DigiRaksha</div>
            <div className="auth-sub">
              {mode === "setup" ? t("auth.setup.sub") : t("auth.login.sub")}
            </div>
          </div>
        </div>

        {/* Fields */}
        {mode === "setup" && (
          <div className="field">
            <label className="field-label" htmlFor="officer">{t("field.officer")}</label>
            <input
              id="officer"
              className="input"
              value={officer}
              onChange={(e) => setOfficer(e.target.value)}
              placeholder="e.g. Insp. A. Kumar"
              autoFocus
            />
          </div>
        )}

        <div className="field">
          <label className="field-label" htmlFor="pin">{t("field.pin")}</label>
          <input
            id="pin"
            className="input pin-input"
            type="password"
            inputMode="numeric"
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="••••"
            autoFocus={mode === "login"}
          />
        </div>

        {err && <div className="error-banner">{err}</div>}

        <button
          className="btn btn-primary btn-block btn-lg"
          onClick={submit}
          disabled={busy}
          style={{ marginTop: 8 }}
        >
          {busy ? (
            <span style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center" }}>
              <span className="spinner-sm" style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "#fff" }} />
              {t("status.saving")}
            </span>
          ) : (
            mode === "setup" ? t("btn.setup") : t("btn.unlock")
          )}
        </button>

        <div style={{ marginTop: 16, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <button
            type="button"
            className="btn btn-outline btn-block"
            onClick={() => setShowVideos(!showVideos)}
            style={{ fontSize: "0.85rem", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
          >
            <span>🎬</span>
            <span>{showVideos ? "Hide Platform Videos" : "Watch Platform Walkthrough & Intro"}</span>
          </button>
        </div>

        {showVideos && (
          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ background: "rgba(15, 23, 42, 0.7)", borderRadius: 8, padding: 12, border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <strong style={{ fontSize: "0.85rem", color: "var(--text-1)" }}>⚡ Platform Intro (18s)</strong>
                <span style={{ fontSize: "0.7rem", color: "#38bdf8", background: "rgba(56, 189, 248, 0.15)", padding: "1px 6px", borderRadius: 4 }}>18 SEC</span>
              </div>
              <video
                controls
                poster="/videos/digiraksha_intro.jpg"
                preload="metadata"
                style={{ width: "100%", borderRadius: 6, background: "#050914", aspectRatio: "16/9", objectFit: "cover" }}
              >
                <source src="/videos/digiraksha_intro.mp4" type="video/mp4" />
                Your browser does not support HTML5 video.
              </video>
            </div>

            <div style={{ background: "rgba(15, 23, 42, 0.7)", borderRadius: 8, padding: 12, border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <strong style={{ fontSize: "0.85rem", color: "var(--text-1)" }}>🖥️ Full 6-Screen Tour (60s)</strong>
                <span style={{ fontSize: "0.7rem", color: "#10b981", background: "rgba(16, 185, 129, 0.15)", padding: "1px 6px", borderRadius: 4 }}>60 SEC</span>
              </div>
              <video
                controls
                poster="/videos/digiraksha_walkthrough.jpg"
                preload="metadata"
                style={{ width: "100%", borderRadius: 6, background: "#050914", aspectRatio: "16/9", objectFit: "cover" }}
              >
                <source src="/videos/digiraksha_walkthrough.mp4" type="video/mp4" />
                Your browser does not support HTML5 video.
              </video>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
