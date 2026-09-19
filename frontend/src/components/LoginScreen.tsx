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
      </div>
    </div>
  );
}
