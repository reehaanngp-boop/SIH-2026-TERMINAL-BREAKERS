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

  const items: NavItem[] = [
    { key: "dashboard", icon: "▦", label: t("nav.dashboard") },
    { key: "analyze", icon: "⌕", label: t("nav.analyze") },
    { key: "cases", icon: "▤", label: t("nav.cases") },
    { key: "evidence", icon: "⬡", label: t("nav.evidence") },
    { key: "voice-match", icon: "♪", label: t("nav.voice-match") },
    { key: "phone", icon: "☎", label: t("nav.phone") },
  ];
  const registryItems: NavItem[] = [
    { key: "registry", icon: "◉", label: t("nav.registry") },
    { key: "history", icon: "≡", label: t("nav.history") },
    { key: "settings", icon: "⚙", label: t("nav.settings") },
  ];

  const render = (group: NavItem[]) =>
    group.map((n) => (
      <button
        key={n.key}
        className={`nav-item ${head === n.key ? "active" : ""}`}
        onClick={() => onNavigate(`/${n.key}`)}
      >
        <span className="nav-ico">{n.icon}</span>
        {n.label}
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
      {render(items)}
      <div className="sidebar-section">Tools</div>
      {render(registryItems)}

      <div className="sidebar-foot">Local police case toolkit · EN/HI · v1.0</div>
    </aside>
  );
}
