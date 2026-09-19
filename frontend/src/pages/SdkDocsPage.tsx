import { useState } from "react";

export function SdkDocsPage() {
  const [activeTab, setActiveTab] = useState<"banking" | "voip" | "websocket" | "curl">("banking");
  const [copied, setCopied] = useState(false);

  const copyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const pythonBankingCode = `from app.sdk.banking_gate import DigiRakshaBankingGate

# Initialize Enterprise Banking Gate with Core Banking System (CBS)
gate = DigiRakshaBankingGate(
    api_base_url="http://127.0.0.1:8000",
    high_risk_threshold=0.45,
    wire_transfer_limit_inr=500000.0, # ₹5,00,000 threshold
)

def process_wire_transfer(transfer_request):
    """Intercept high-value telephonic approvals before releasing funds."""
    caller_phone = transfer_request["caller_phone"]
    claimed_officer = transfer_request["authorizing_officer"] # e.g. "CEO Priya Sharma"
    audio_recording_path = transfer_request["call_recording_path"]
    amount = transfer_request["amount_inr"]

    # Perform multi-layer voice integrity check (Acoustic + Prosody + Biometrics)
    decision = gate.verify_voice_authorization(
        caller_phone=caller_phone,
        claimed_officer_name=claimed_officer,
        audio_path=audio_recording_path,
        transaction_amount_inr=amount,
    )

    if not decision["authorized"]:
        # Log to fraud containment pipeline and halt execution
        print(f"[SECURITY ALERT] Wire transfer BLOCKED: {decision['reason']}")
        print(f"Audit Certificate ID: {decision['certificate_id']}")
        return {
            "status": "REJECTED_VOICE_CLONE_DETECTED",
            "certificate_id": decision["certificate_id"],
            "block_hash": decision["block_hash"],
        }

    # Voice verified authentic against registered executive voiceprint
    print(f"[APPROVED] Voice integrity confirmed for {claimed_officer}.")
    return {"status": "TRANSFER_RELEASED", "certificate_id": decision["certificate_id"]}`;

  const nodeVoipCode = `import WebSocket from "ws";
import fs from "fs";

// Connect PBX / Asterisk / FreeSWITCH audio stream to DigiRaksha Sentinel
const ws = new WebSocket("ws://127.0.0.1:8000/api/v1/stream/live-call");

ws.on("open", () => {
  console.log("Connected to DigiRaksha Telephony Sentinel.");
  // Handshake with caller metadata
  ws.send(JSON.stringify({
    action: "start",
    caller_id: "+91 99880 12345",
    claimed_identity: "CEO Rajesh Nair"
  }));
});

ws.on("message", (raw) => {
  const data = JSON.parse(raw.toString());
  if (data.type === "telemetry") {
    console.log(\`[Live Telemetry] Risk: \${(data.dynamic_risk_score * 100).toFixed(0)}% | Vocoder: \${data.fingerprint}\`);
    if (data.dynamic_risk_score >= 0.50) {
      console.error(\`🚨 ALERT: \${data.alert}\`);
      // Trigger SIP call termination or transfer to Fraud Desk
    }
  } else if (data.type === "session_summary") {
    console.log(\`✅ Session Anchored. Certificate ID: \${data.certificate_id}\`);
  }
});

// Stream 16kHz PCM audio buffer chunks
function streamCallChunk(pcmBuffer) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(pcmBuffer);
  }
}`;

  const websocketSpec = `{
  "endpoint": "ws://127.0.0.1:8000/api/v1/stream/live-call",
  "client_messages": [
    {
      "action": "start",
      "caller_id": "+91 98765 43210",
      "claimed_identity": "CFO Priya Sharma"
    },
    {
      "bytes": "<Raw 16-bit 16kHz Mono PCM Audio Buffer Chunk>"
    },
    {
      "action": "stop"
    }
  ],
  "server_events": [
    {
      "type": "telemetry",
      "timestamp": "2026-09-17T09:45:00Z",
      "dynamic_risk_score": 0.88,
      "liveness_score": 0.12,
      "vocoder_anomaly": 0.75,
      "pitch_stability": 1.1,
      "micro_jitter": 0.003,
      "telephony_mode": "wideband_telephony_or_voip",
      "fingerprint": "neural_vocoder_hifigan_or_xtts",
      "verdict": "CRITICAL_IMPERSONATION",
      "alert": "HIGH RISK: Synthetic Vocoder Signature Detected.",
      "recommended_action": "TERMINATE_AND_CHALLENGE_WITH_OUT_OF_BAND_AUTH"
    },
    {
      "type": "session_summary",
      "certificate_id": "DR-VOICE-CERT-20260916-DB66527D",
      "block_hash": "8a729c4987d3aea20fa2864ee481434151943472ab7abe5225e567b3a31c25fe",
      "compliance": "Section 65B Bharatiya Sakshya Adhiniyam 2023"
    }
  ]
}`;

  const curlCode = `# 1. Simulate an executive impersonation call
curl -X POST "http://127.0.0.1:8000/api/v1/stream/simulate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "scenario": "cloned_ceo",
    "claimed_identity": "CEO Priya Sharma",
    "caller_id": "+91 99880 12345"
  }'

# 2. Verify a Voice Integrity Certificate in the Blockchain
curl -X GET "http://127.0.0.1:8000/api/v1/blockchain/verify/DR-VOICE-CERT-20260916-DB66527D"

# 3. Retrieve complete immutable blockchain ledger
curl -X GET "http://127.0.0.1:8000/api/v1/blockchain/ledger?limit=20"`;

  const getActiveCode = () => {
    switch (activeTab) {
      case "banking":
        return pythonBankingCode;
      case "voip":
        return nodeVoipCode;
      case "websocket":
        return websocketSpec;
      case "curl":
        return curlCode;
    }
  };

  const getFilename = () => {
    switch (activeTab) {
      case "banking":
        return "banking_gate_integration.py";
      case "voip":
        return "voip_stream_sentinel.ts";
      case "websocket":
        return "websocket_protocol.json";
      case "curl":
        return "api_curl_examples.sh";
    }
  };

  return (
    <div className="page">
      {/* Hero Header */}
      <div className="hero-banner">
        <div className="hero-banner-content">
          <div className="hero-badge">
            <span className="pulse-dot" />
            <span>Enterprise Integration SDK & APIs · Problem Statement 26104</span>
          </div>
          <h1 className="hero-title">Developer Portal & Integration Hub</h1>
          <p className="hero-sub">
            Embed real-time voice cloning detection into Core Banking Systems (Finacle, TCS BaNCS), SWIFT/RTGS authorization gates, Asterisk/FreeSWITCH PBX, and enterprise communication pipelines.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="seg" style={{ marginBottom: 0 }}>
        <button
          type="button"
          onClick={() => setActiveTab("banking")}
          className={`seg-btn ${activeTab === "banking" ? "active" : ""}`}
        >
          🏦 Banking Wire Gate (Python)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("voip")}
          className={`seg-btn ${activeTab === "voip" ? "active" : ""}`}
        >
          📞 VoIP / PBX Middleware (Node.js)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("websocket")}
          className={`seg-btn ${activeTab === "websocket" ? "active" : ""}`}
        >
          📡 WebSocket Protocol Spec
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("curl")}
          className={`seg-btn ${activeTab === "curl" ? "active" : ""}`}
        >
          💻 REST / cURL Reference
        </button>
      </div>

      {/* Code Viewer IDE Card */}
      <div className="code-window">
        <div className="code-window-header">
          <div className="code-window-left">
            <div className="window-dots">
              <span className="window-dot dot-red" />
              <span className="window-dot dot-yellow" />
              <span className="window-dot dot-green" />
            </div>
            <span className="code-filename">{getFilename()}</span>
          </div>

          <button
            type="button"
            onClick={() => copyCode(getActiveCode())}
            className="btn btn-sm btn-secondary"
          >
            <span>{copied ? "✓" : "📋"}</span>
            <span>{copied ? "Copied to Clipboard!" : "Copy Snippet"}</span>
          </button>
        </div>

        <pre className="code-pre">{getActiveCode()}</pre>
      </div>

      {/* Key Architectural Guarantees */}
      <div className="grid grid-3" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginTop: 20 }}>
        <div className="card" style={{ margin: 0 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>⚡</div>
          <div className="card-title">Sub-30ms Window Latency</div>
          <p className="card-sub" style={{ margin: 0, lineHeight: 1.5 }}>
            Vectorized FFT autocorrelation, sliding STFT spectral flatness, and G.711 telephony compensation compute instant scores without buffering delay.
          </p>
        </div>

        <div className="card" style={{ margin: 0 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>⛓️</div>
          <div className="card-title">Cryptographic Immutability</div>
          <p className="card-sub" style={{ margin: 0, lineHeight: 1.5 }}>
            Every call verdict anchors an SHA-256 Merkle block with HMAC digital signature, fully compliant with Section 65B Bharatiya Sakshya Adhiniyam 2023.
          </p>
        </div>

        <div className="card" style={{ margin: 0 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>🛡️</div>
          <div className="card-title">Pre-Action Wire Interception</div>
          <p className="card-sub" style={{ margin: 0, lineHeight: 1.5 }}>
            Direct hook for core banking wire transfers (₹5 Lakh+). Quarantines unauthorized fund releases automatically when caller voice risk exceeds threshold.
          </p>
        </div>
      </div>
    </div>
  );
}
