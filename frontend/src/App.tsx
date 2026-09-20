import { useEffect, useRef, useState } from "react";
import { api, getApiBase, onAuthError, setApiBase, setAuthToken } from "./api";
import { LoginScreen } from "./components/LoginScreen";
import { Sidebar } from "./components/Sidebar";
import { ToastStack, useToasts } from "./components/Toast";
import { TopBar } from "./components/TopBar";
import { useI18n } from "./i18n";
import { routeSegments, useHashRoute } from "./router";
import { AnalyzePage } from "./pages/AnalyzePage";
import { AssistantPage } from "./pages/AssistantPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { CasesPage } from "./pages/CasesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EvidencePage } from "./pages/EvidencePage";
import { HistoryPage } from "./pages/HistoryPage";
import { PhoneIntelPage } from "./pages/PhoneIntelPage";
import { RegistryPage } from "./pages/RegistryPage";
import { SettingsPage } from "./pages/SettingsPage";
import { VoiceMatchPage } from "./pages/VoiceMatchPage";
import { LiveCallPage } from "./pages/LiveCallPage";
import { BlockchainPage } from "./pages/BlockchainPage";
import { MediaAuthPage } from "./pages/MediaAuthPage";
import { AiAssistantWidget } from "./components/AiAssistantWidget";

type AuthState = "loading" | "offline" | "setup" | "login" | "app";

export default function App() {
  const { t } = useI18n();
  const { toasts, push, dismiss } = useToasts();
  const [auth, setAuth] = useState<AuthState>("loading");
  const [officerName, setOfficerName] = useState<string | null>(null);
  const [route, navigate] = useHashRoute();

  const authRef = useRef(auth);
  authRef.current = auth;

  const isLocalhost = typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
  const [initMsg, setInitMsg] = useState("Initializing DigiRaksha AI engines...");

  useEffect(() => {
    onAuthError(() => {
      // Only force-lock while inside the app — a failed login already 401s.
      if (authRef.current === "app") {
        setAuthToken(null);
        setAuth("login");
        push("Session expired — sign in again", "error");
      }
    });

    let timer: number;
    let attempts = 0;
    const maxAttempts = isLocalhost ? 20 : 6;

    const checkBackend = async () => {
      try {
        const s = await api.authStatus();
        setOfficerName(s.officer_name ?? null);
        if (s.authenticated) setAuth("app");
        else setAuth(s.setup_required ? "setup" : "login");
      } catch {
        attempts++;
        if (attempts < maxAttempts) {
          if (isLocalhost) {
            setInitMsg(`Starting DigiRaksha AI engine... (${attempts}/${maxAttempts})`);
          } else {
            setInitMsg("Connecting to backend...");
          }
          timer = window.setTimeout(checkBackend, 1200);
        } else {
          setAuth("offline");
        }
      }
    };

    checkBackend();

    return () => clearTimeout(timer);
  }, [push, isLocalhost]);

  const onAuthed = (name: string) => {
    setOfficerName(name);
    setAuth("app");
    navigate("/dashboard");
  };

  const lock = async () => {
    try {
      await api.authLogout();
    } catch {
      /* lock locally regardless */
    }
    setAuthToken(null);
    setAuth("login");
    navigate("/dashboard");
  };

  const [offlineBackendUrl, setOfflineBackendUrl] = useState(() => getApiBase() || "");
  const [offlineTesting, setOfflineTesting] = useState(false);

  const handleOfflineConnect = async () => {
    setOfflineTesting(true);
    setApiBase(offlineBackendUrl);
    try {
      const s = await api.authStatus();
      setOfficerName(s.officer_name ?? null);
      if (s.authenticated) setAuth("app");
      else setAuth(s.setup_required ? "setup" : "login");
    } catch {
      push("Could not connect to backend at that URL. Ensure the server or tunnel is running.", "error");
    } finally {
      setOfflineTesting(false);
    }
  };

  if (auth === "loading") {
    return (
      <div className="center" style={{ minHeight: "100vh" }}>
        <div className="spinner" />
        <p style={{ marginTop: 12 }}>{initMsg}</p>
      </div>
    );
  }

  if (auth === "offline") {
    return (
      <div className="auth-wrap">
        <div className="auth-card" style={{ maxWidth: 440 }}>
          <div className="auth-logo">
            <div className="sidebar-logo">🛡️</div>
            <div className="auth-title">DigiRaksha</div>
          </div>
          <div className="error-banner">{t("err.network")}</div>

          {isLocalhost ? (
            <>
              <p className="muted small" style={{ marginTop: 10, marginBottom: 16 }}>
                Backend not detected on localhost:8000. Please make sure <code>DigiRaksha.bat</code> is running on your PC.
              </p>
              <button
                type="button"
                className="btn btn-primary btn-block"
                onClick={() => {
                  setAuth("loading");
                  window.location.reload();
                }}
              >
                Retry Connection
              </button>
            </>
          ) : (
            <>
              <p className="muted small" style={{ marginTop: 10, marginBottom: 12 }}>
                Connect to your active Cloudflare Tunnel URL:
              </p>
              <input
                className="input"
                type="text"
                placeholder="https://xxxx.trycloudflare.com"
                value={offlineBackendUrl}
                onChange={(e) => setOfflineBackendUrl(e.target.value)}
                style={{ marginBottom: 12 }}
              />
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={offlineTesting}
                  onClick={handleOfflineConnect}
                >
                  {offlineTesting ? "Connecting…" : "Connect & Start"}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => window.location.reload()}
                >
                  {t("err.try")}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  if (auth === "setup" || auth === "login") {
    return (
      <>
        <LoginScreen mode={auth} onAuthed={onAuthed} />
        <AiAssistantWidget />
        <ToastStack toasts={toasts} onDismiss={dismiss} />
      </>
    );
  }

  const [head, ...rest] = routeSegments(route);
  let page;
  switch (head) {
    case "live-call":
      page = <LiveCallPage />;
      break;
    case "blockchain":
      page = <BlockchainPage />;
      break;
    case "analyze":
      page = <AnalyzePage navigate={navigate} />;
      break;
    case "assistant":
      page = <AssistantPage />;
      break;
    case "cases":
      page = rest[0] ? <CaseDetailPage id={rest[0]} navigate={navigate} /> : <CasesPage navigate={navigate} />;
      break;
    case "evidence":
      page = <EvidencePage />;
      break;
    case "voice-match":
      page = <VoiceMatchPage />;
      break;
    case "phone":
      page = <PhoneIntelPage />;
      break;
    case "registry":
      page = <RegistryPage />;
      break;
    case "history":
      page = <HistoryPage />;
      break;
    case "settings":
      page = <SettingsPage />;
      break;
    case "media-auth":
      page = <MediaAuthPage />;
      break;
    default:
      page = <DashboardPage />;
  }

  return (
    <div className="shell">
      <Sidebar route={route} onNavigate={navigate} />
      <div className="content">
        <TopBar route={route} officerName={officerName} onLock={lock} />
        <main>{page}</main>
        <footer className="footer">{t("footer.disclaimer")}</footer>
      </div>
      <AiAssistantWidget />
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
