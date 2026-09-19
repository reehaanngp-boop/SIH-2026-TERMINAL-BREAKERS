import { useEffect, useRef, useState } from "react";
import { api, onAuthError, setAuthToken } from "./api";
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
import { SdkDocsPage } from "./pages/SdkDocsPage";
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

  useEffect(() => {
    onAuthError(() => {
      // Only force-lock while inside the app — a failed login already 401s.
      if (authRef.current === "app") {
        setAuthToken(null);
        setAuth("login");
        push("Session expired — sign in again", "error");
      }
    });

    api
      .authStatus()
      .then((s) => {
        setOfficerName(s.officer_name ?? null);
        if (s.authenticated) setAuth("app");
        else setAuth(s.setup_required ? "setup" : "login");
      })
      .catch(() => setAuth("offline"));
  }, [push]);

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

  if (auth === "loading") {
    return (
      <div className="center" style={{ minHeight: "100vh" }}>
        <div className="spinner" />
        <p>{t("status.loading")}</p>
      </div>
    );
  }

  if (auth === "offline") {
    return (
      <div className="auth-wrap">
        <div className="auth-card">
          <div className="auth-logo">
            <div className="sidebar-logo">🛡️</div>
            <div className="auth-title">DigiRaksha</div>
          </div>
          <div className="error-banner">{t("err.network")}</div>
          <button className="btn btn-primary btn-block" onClick={() => window.location.reload()}>
            {t("err.try")}
          </button>
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
    case "sdk":
    case "sdk-docs":
      page = <SdkDocsPage />;
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
