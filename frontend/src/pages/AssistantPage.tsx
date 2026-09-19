import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import type { AssistantChatMessage, QuickCheckResult } from "../types";
import { Modal } from "../components/Modal";

const STARTER_PROMPTS = [
  {
    icon: "🚨",
    title: "Is 'Digital Arrest' real?",
    prompt: "I received a video call from someone claiming to be CBI/Police placing me under Digital Arrest. Is this legitimate under Indian law?",
  },
  {
    icon: "⚡",
    title: "Golden Hour Freeze Protocol",
    prompt: "I accidentally transferred money to a scammer 30 minutes ago. What exact steps should I take right now to freeze the money?",
  },
  {
    icon: "🎙️",
    title: "AI Voice Cloning Defense",
    prompt: "How can I tell if a frantic voice note from my child or relative is real or an AI deepfake clone?",
  },
  {
    icon: "⚖️",
    title: "Legal Sections & FIR",
    prompt: "What BNS and IT Act sections apply to cyber extortion and deepfakes? How do I file a complaint?",
  },
];

const AVAILABLE_MODELS = [
  { id: "poolside/laguna-s-2.1:free", label: "Laguna 2.1 (Free)" },
  { id: "nvidia/nemotron-3.5-lightning:free", label: "NVIDIA Nemotron 3.5 (Free)" },
  { id: "z-ai/glm-5.2:free", label: "GLM 5.2 (Free)" },
  { id: "google/gemini-2.0-flash-exp:free", label: "Gemini 2.0 Flash (Free)" },
];

export function AssistantPage(): React.ReactElement {
  const { t } = useI18n();

  const [messages, setMessages] = useState<AssistantChatMessage[]>(() => {
    const saved = sessionStorage.getItem("digiraksha.chat_history");
    if (saved) { try { return JSON.parse(saved); } catch { /* empty */ } }
    return [{
      role: "assistant",
      content: "👋 **Namaste! I am your DigiRaksha AI Cyber Copilot.**\n\nI am grounded in Indian Cyber Law (IT Act 2000 & BNS 2023) and MHA/I4C procedures. How can I assist you today?",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      suggestions: ["Is Digital Arrest legal in India?", "How to file a complaint on 1930?", "What is the Golden Hour bank freeze?", "Draft a cyber crime FIR complaint"],
    }];
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("poolside/laguna-s-2.1:free");
  const [modelStatus, setModelStatus] = useState("Checking AI status…");
  const [isAiOnline, setIsAiOnline] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [showFirModal, setShowFirModal] = useState(false);
  const [showTriageModal, setShowTriageModal] = useState(false);

  const [firData, setFirData] = useState({
    victim_name: "", suspect_phone: "", suspect_upi: "",
    scam_type: "Digital Arrest / Police Impersonation", amount_lost: "",
    date_time: new Date().toLocaleString(), details: "",
  });
  const [generatedFir, setGeneratedFir] = useState<string | null>(null);
  const [firLoading, setFirLoading] = useState(false);
  const [triageText, setTriageText] = useState("");
  const [triageResult, setTriageResult] = useState<QuickCheckResult | null>(null);
  const [triageLoading, setTriageLoading] = useState(false);

  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    sessionStorage.setItem("digiraksha.chat_history", JSON.stringify(messages));
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    api.assistantStatus()
      .then((s) => {
        setIsAiOnline(s.available);
        setModelStatus(s.available ? `Active: ${s.active_model}` : `Offline: ${s.reason}`);
        if (s.active_model) setSelectedModel(s.active_model);
      })
      .catch(() => { setIsAiOnline(false); setModelStatus("Offline Rulebook Mode"); });
  }, []);

  const handleSend = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || loading) return;

    const userMsg: AssistantChatMessage = {
      role: "user", content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setLoading(true);

    try {
      const res = await api.assistantChat(history.map((m) => ({ role: m.role, content: m.content })), undefined, undefined, selectedModel);
      setMessages((prev) => [...prev, {
        role: "assistant", content: res.reply, model: res.model,
        suggestions: res.suggestions || [], error: res.error,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: "⚠️ Network error. If dealing with a live scammer: **Hang up immediately, dial 1930, and report at cybercrime.gov.in**.",
        error: err instanceof Error ? err.message : "error",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleClear = () => {
    sessionStorage.removeItem("digiraksha.chat_history");
    setMessages([{ role: "assistant", content: "Chat cleared. How can I assist?", timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }]);
  };

  const handleGenerateFir = async () => {
    setFirLoading(true);
    try {
      const res = await api.assistantDraftFir({
        victim_name: firData.victim_name || "Complainant",
        suspect_phone: firData.suspect_phone || "Not specified",
        suspect_upi: firData.suspect_upi || "Not specified",
        scam_type: firData.scam_type,
        amount_lost: firData.amount_lost || "0",
        date_time: firData.date_time,
        transcript: firData.details,
      });
      setGeneratedFir(res.complaint_markdown);
    } catch (err) {
      alert("Failed to generate draft: " + (err instanceof Error ? err.message : String(err)));
    } finally { setFirLoading(false); }
  };

  const handleRunTriage = async () => {
    if (!triageText.trim()) return;
    setTriageLoading(true);
    try {
      const res = await api.assistantQuickCheck(triageText);
      setTriageResult(res.data);
    } catch (err) {
      alert("Triage failed: " + (err instanceof Error ? err.message : String(err)));
    } finally { setTriageLoading(false); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - var(--topbar-h) - 41px)", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ padding: "16px 28px 12px", borderBottom: "1px solid var(--border)", background: "var(--bg-1)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 20 }}>🛡️</span>
              <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.03em" }}>{t("assistant.title")}</h1>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-3)", marginTop: 3 }}>{t("assistant.subtitle")}</p>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
              <span className={`status-dot ${isAiOnline ? "active" : "error"}`} />
              <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>{modelStatus}</span>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <select
              className="select"
              style={{ width: 200, fontSize: 12 }}
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {AVAILABLE_MODELS.map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowTriageModal(true)}>⚡ Quick Triage</button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowFirModal(true)}>📋 Draft FIR</button>
            <button className="btn btn-ghost btn-icon btn-sm" onClick={handleClear} title="Clear chat">🗑️</button>
          </div>
        </div>
      </div>

      {/* Chat feed */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 28px", display: "flex", flexDirection: "column", gap: 16, scrollbarWidth: "thin" }}>
        {/* Starter prompts */}
        {messages.length === 1 && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10, marginBottom: 8 }}>
            {STARTER_PROMPTS.map((sp, i) => (
              <div
                key={i}
                onClick={() => handleSend(sp.prompt)}
                style={{
                  padding: "14px 16px", background: "var(--bg-1)", border: "1px solid var(--border)",
                  borderRadius: "var(--r-lg)", cursor: "pointer", transition: "border-color var(--normal), background var(--normal)",
                  display: "flex", gap: 10, alignItems: "flex-start",
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = "var(--blue)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)"; }}
              >
                <span style={{ fontSize: 20, flexShrink: 0 }}>{sp.icon}</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{sp.title}</div>
                  <div style={{ fontSize: 11.5, color: "var(--text-3)", lineHeight: 1.5 }}>{sp.prompt}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, idx) => {
          const isAi = msg.role === "assistant";
          return (
            <div key={idx} style={{ display: "flex", gap: 10, flexDirection: isAi ? "row" : "row-reverse" }}>
              <div style={{
                width: 30, height: 30, borderRadius: "var(--r-md)", background: "var(--bg-2)",
                border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 14, flexShrink: 0,
              }}>
                {isAi ? "🛡️" : "👤"}
              </div>
              <div style={{ maxWidth: "75%", display: "flex", flexDirection: "column", gap: 6, alignItems: isAi ? "flex-start" : "flex-end" }}>
                <div style={{
                  padding: "10px 14px",
                  background: isAi ? "var(--bg-1)" : "var(--blue)",
                  border: isAi ? "1px solid var(--border)" : "none",
                  borderRadius: isAi ? "4px var(--r-lg) var(--r-lg) var(--r-lg)" : "var(--r-lg) 4px var(--r-lg) var(--r-lg)",
                  fontSize: 13.5, lineHeight: 1.65, color: isAi ? "var(--text)" : "#fff",
                }}>
                  {msg.content.split("\n\n").map((para, pi) =>
                    para.startsWith("#") ? (
                      <h4 key={pi} style={{ fontWeight: 700, margin: "6px 0 4px", fontSize: 14 }}>
                        {para.replace(/^#+\s*/, "")}
                      </h4>
                    ) : (
                      <p key={pi} style={{ margin: pi === 0 ? 0 : "8px 0 0" }}>
                        {para.split("\n").map((line, li) => (
                          <React.Fragment key={li}>{line}{li < para.split("\n").length - 1 && <br />}</React.Fragment>
                        ))}
                      </p>
                    )
                  )}
                </div>
                {/* Footer */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "var(--text-4)" }}>
                  <span>{msg.timestamp}</span>
                  {msg.model && <span className="chip" style={{ fontSize: 10 }}>{msg.model.split("/").pop()}</span>}
                  {isAi && (
                    <button
                      onClick={() => handleCopy(msg.content, idx)}
                      style={{ background: "none", border: "none", color: "var(--text-4)", cursor: "pointer", fontSize: 11, padding: "2px 6px", borderRadius: "var(--r-sm)", transition: "color var(--fast)", }}
                    >
                      {copiedIndex === idx ? "✓ Copied" : "Copy"}
                    </button>
                  )}
                </div>
                {/* Suggestion chips */}
                {isAi && msg.suggestions && msg.suggestions.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {msg.suggestions.map((s, si) => (
                      <button key={si} className="chip" onClick={() => handleSend(s)} style={{ cursor: "pointer", fontSize: 11.5 }}>
                        ↳ {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {loading && (
          <div style={{ display: "flex", gap: 10 }}>
            <div style={{ width: 30, height: 30, borderRadius: "var(--r-md)", background: "var(--bg-2)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>🛡️</div>
            <div style={{ padding: "10px 14px", background: "var(--bg-1)", border: "1px solid var(--border)", borderRadius: "4px var(--r-lg) var(--r-lg) var(--r-lg)", display: "flex", alignItems: "center", gap: 8 }}>
              <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              <span style={{ fontSize: 12.5, color: "var(--text-3)" }}>Analyzing legal provisions…</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input bar */}
      <div style={{ padding: "12px 28px", borderTop: "1px solid var(--border)", background: "var(--bg-1)", display: "flex", gap: 10, alignItems: "flex-end", flexShrink: 0 }}>
        <textarea
          className="textarea"
          rows={2}
          value={input}
          placeholder={t("assistant.placeholder")}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          style={{ flex: 1, resize: "none", minHeight: 60 }}
        />
        <button
          className="btn btn-primary"
          disabled={!input.trim() || loading}
          onClick={() => handleSend()}
          style={{ alignSelf: "flex-end" }}
        >
          {loading ? "…" : `➤ ${t("assistant.send")}`}
        </button>
      </div>

      {/* FIR Modal */}
      {showFirModal && (
        <Modal title="📋 Cyber Crime FIR Drafter (1930 / I4C)" onClose={() => setShowFirModal(false)}>
          {!generatedFir ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[
                { label: "Complainant Name", key: "victim_name" as const, placeholder: "e.g. Ramesh Kumar" },
                { label: "Suspect Phone / WhatsApp", key: "suspect_phone" as const, placeholder: "+91 98765 43210" },
                { label: "Suspect UPI / Account", key: "suspect_upi" as const, placeholder: "fraudster@ybl" },
                { label: "Financial Loss (₹)", key: "amount_lost" as const, placeholder: "50000" },
                { label: "Date & Time", key: "date_time" as const, placeholder: "" },
              ].map(({ label, key, placeholder }) => (
                <div key={key}>
                  <label className="field-label">{label}</label>
                  <input className="input" placeholder={placeholder} value={firData[key]} onChange={(e) => setFirData({ ...firData, [key]: e.target.value })} />
                </div>
              ))}
              <div>
                <label className="field-label">Scam Category</label>
                <select className="select" value={firData.scam_type} onChange={(e) => setFirData({ ...firData, scam_type: e.target.value })}>
                  <option>Digital Arrest / Police Impersonation</option>
                  <option>Fake FedEx / Customs Narcotics Parcel</option>
                  <option>AI Deepfake Voice Cloning Kidnapping</option>
                  <option>Electricity / Power Bill Disconnection Scam</option>
                  <option>Aadhaar / Bank KYC Update Phishing</option>
                </select>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label className="field-label">Incident Transcript / Notes</label>
                <textarea className="textarea" rows={3} placeholder="Paste conversation excerpts or key threats…" value={firData.details} onChange={(e) => setFirData({ ...firData, details: e.target.value })} />
              </div>
            </div>
          ) : (
            <div>
              <div className="success-banner" style={{ marginBottom: 12 }}>✓ Formal Cyber Complaint drafted with applicable BNS & IT Act sections!</div>
              <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", overflowY: "auto", maxHeight: 300 }}>{generatedFir}</pre>
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
            {!generatedFir ? (
              <>
                <button className="btn btn-ghost" onClick={() => setShowFirModal(false)}>Cancel</button>
                <button className="btn btn-primary" disabled={firLoading} onClick={handleGenerateFir}>
                  {firLoading ? "Generating…" : "⚡ Draft Complaint"}
                </button>
              </>
            ) : (
              <>
                <button className="btn btn-ghost" onClick={() => setGeneratedFir(null)}>Edit</button>
                <button className="btn btn-primary" onClick={() => { navigator.clipboard.writeText(generatedFir!); alert("Copied! Paste this at cybercrime.gov.in"); }}>
                  📋 Copy to Clipboard
                </button>
              </>
            )}
          </div>
        </Modal>
      )}

      {/* Triage Modal */}
      {showTriageModal && (
        <Modal title="⚡ Rapid Scam Triage" onClose={() => setShowTriageModal(false)}>
          <p style={{ fontSize: 13, color: "var(--text-3)", marginBottom: 12 }}>
            Paste any suspicious SMS, WhatsApp message, or email to check for scam patterns.
          </p>
          <textarea
            className="textarea"
            rows={4}
            placeholder="e.g. 'Dear Customer, your electricity will be disconnected tonight...'"
            value={triageText}
            onChange={(e) => setTriageText(e.target.value)}
          />
          {triageResult && (
            <div style={{
              marginTop: 14, padding: "14px 16px",
              background: triageResult.is_scam ? "var(--rose-soft)" : "var(--emerald-soft)",
              border: `1px solid ${triageResult.is_scam ? "rgba(244,63,94,0.25)" : "rgba(16,185,129,0.25)"}`,
              borderRadius: "var(--r-lg)",
            }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>
                {triageResult.is_scam ? "🚨 HIGH RISK SCAM" : "🛡️ LIKELY BENIGN"}
                <span className="chip" style={{ marginLeft: 8, fontSize: 11 }}>{triageResult.scam_category}</span>
              </div>
              <p style={{ fontSize: 13, marginBottom: 4 }}><strong>Assessment:</strong> {triageResult.summary_en}</p>
              <p style={{ fontSize: 13, marginBottom: 4 }}><strong>हिंदी:</strong> {triageResult.summary_hi}</p>
              <p style={{ fontSize: 13 }}><strong>Action:</strong> {triageResult.recommended_action}</p>
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={() => setShowTriageModal(false)}>Close</button>
            <button className="btn btn-primary" disabled={!triageText.trim() || triageLoading} onClick={handleRunTriage}>
              {triageLoading ? "Scanning…" : "Scan Message"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
