import { CopilotPanel } from "../components/CopilotPanel";

export function AssistantPage() {
  return (
    <div style={{ height: "calc(100vh - var(--topbar-h) - 41px)" }}>
      <CopilotPanel height="100%" />
    </div>
  );
}