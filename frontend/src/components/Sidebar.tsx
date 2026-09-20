import { useI18n } from "../i18n";
import { routeSegments } from "../router";
import type { NavKey } from "../types";

interface NavItem {
  key: NavKey;
  icon: string;
  label: string;
}

export function Sidebar({ route, onNavigate }: { route: string; onNavigate: (r: string) => void }) {
  const { t } = useI18n();
  const head = routeSegments(route)[0] || "dashboard";

  const primary: NavItem[] = [
    { key: "dashboard",   icon: "⊞",  label: t("nav.dashboard") },
    { key: "live-call",   icon: "⬤",  label: t("nav.live-call") },
    { key: "analyze",     icon: "⌕",  label: t("nav.analyze") },
    { key: "assistant",   icon: "✦",  label: t("nav.assistant") },
    { key: "cases",       icon: "☰",  label: t("nav.cases") },
    { key: "evidence",    icon: "◈",  label: t("nav.evidence") },
    { key: "voice-match", icon: "♪",  label: t("nav.voice-match") },
    { key: "phone",       icon: "◌",  label: t("nav.phone") },
  ];

  const secondary: NavItem[] = [
    { key: "registry",   icon: "◉",  label: t("nav.registry") },
    { key: "blockchain", icon: "⛓",  label: t("nav.blockchain") },
    { key: "history",    icon: "≡",   label: t("nav.history") },
    { key: "settings",   icon: "⚙",  label: t("nav.settings") },
  ];

  const renderItems = (items: NavItem[]) =>
    items.map((n) => (
      <button
        key={n.key}
        className={`nav-item${head === n.key ? " active" : ""}`}
        onClick={() => onNavigate(`/${n.key}`)}
        title={n.label}
      >
        <span className="nav-ico">{n.icon}</span>
        <span>{n.label}</span>
      </button>
    ));

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">🛡️</div>
        <div>
          <div className="sidebar-name">DigiRaksha</div>
          <div className="sidebar-tagline">{t("brand.tagline")}</div>
        </div>
      </div>

      <div className="sidebar-section">Command</div>
      {renderItems(primary)}

      <div className="sidebar-section">Tools</div>
      {renderItems(secondary)}

      <div className="sidebar-foot">
        Cyber Crime Toolkit · v1.0
      </div>
    </aside>
  );
}
