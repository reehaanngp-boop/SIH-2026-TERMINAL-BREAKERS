import { useI18n } from "../i18n";
import { routeSegments } from "../router";
import type { NavKey } from "../types";

export function TopBar({
  route,
  officerName,
  onLock,
}: {
  route: string;
  officerName: string | null;
  onLock: () => void;
}) {
  const { t, lang, setLang } = useI18n();
  const head = (routeSegments(route)[0] || "dashboard") as NavKey;
  const title = t(`nav.${head}`);

  return (
    <header className="topbar">
      <div className="topbar-title">{title}</div>
      <div className="topbar-actions">
        <div className="topbar-officer">
          <span className="officer-dot" />
          <span>{officerName || "—"}</span>
        </div>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setLang(lang === "en" ? "hi" : "en")}
          aria-label="Toggle language"
        >
          {lang === "en" ? "हिंदी" : "EN"}
        </button>
        <button className="btn btn-secondary btn-sm" onClick={onLock}>
          {t("btn.lock")}
        </button>
      </div>
    </header>
  );
}
