import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AssistantChatMessage } from "../types";

export function AiAssistantWidget(): React.ReactElement {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<AssistantChatMessage[]>([
    {
      role: "assistant",
      content: "Hi! I'm your DigiRaksha AI Copilot. Ask me anything about cyber crime, scam detection, or legal procedures.",
      suggestions: ["Is Digital Arrest real?", "How do I call 1930?", "What to do if money was debited?"],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [open, messages]);

  const send = async (override?: string) => {
    const text = (override ?? input).trim();
    if (!text || loading) return;

    const userMsg: AssistantChatMessage = {
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setLoading(true);

    try {
      const res = await api.assistantChat(history.map((m) => ({ role: m.role, content: m.content })));
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
          suggestions: res.suggestions || [],
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Call 1930 or visit cybercrime.gov.in for emergency help." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* FAB */}
      <button
        className="ai-fab"
        onClick={() => setOpen((v) => !v)}
        title="AI Copilot"
        aria-label="Toggle AI assistant"
      >
        ✦
      </button>

      {/* Panel */}
      {open && (
        <div className="ai-panel">
          <div className="ai-panel-header">
            <span>AI Copilot</span>
            <button
              className="btn btn-ghost btn-icon btn-sm"
              onClick={() => setOpen(false)}
              aria-label="Close"
              style={{ fontSize: 18 }}
            >
              ×
            </button>
          </div>

          <div className="ai-messages">
            {messages.map((m, i) => (
              <div key={i}>
                <div className={`ai-bubble ${m.role === "user" ? "user" : "ai"}`}>
                  {m.content}
                </div>
                {m.role === "assistant" && m.suggestions && m.suggestions.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6, paddingLeft: 2 }}>
                    {m.suggestions.slice(0, 3).map((s, si) => (
                      <button
                        key={si}
                        className="chip"
                        onClick={() => send(s)}
                        style={{ cursor: "pointer", fontSize: 11.5 }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="ai-bubble ai" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="spinner-sm" style={{ borderColor: "var(--border-md)", borderTopColor: "var(--blue)" }} />
                <span style={{ color: "var(--text-3)", fontSize: 12 }}>Thinking…</span>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="ai-input-row">
            <input
              className="ai-input"
              placeholder="Ask anything…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
            />
            <button
              className="ai-send"
              onClick={() => send()}
              disabled={!input.trim() || loading}
              aria-label="Send"
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  );
}
