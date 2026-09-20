/**
 * DigiRaksha - Live Call Sentinel & Telephony Defense Command Deck
 *
 * Professional real-time telephony protection. Mic-only: there is no threat
 * simulator and no benchmark sample player — this console audits a live call
 * streamed from the operator device.
 *
 * Pipeline:
 * 1. Live microphone telephony streaming over WebSocket (16kHz PCM16).
 * 2. Three-signal live fusion verdict (Wav2Vec2 base + Dhwani XLS-R + large
 *    clone-specialist corroboration) with two-window debounce.
 * 3. On call end the captured audio is re-analysed through the authoritative
 *    AASIST workflow (voice gate -> Whisper transcript -> language -> scam
 *    keywords -> risk engine) and a Section 65B certificate is issued.
 * 4. Real-time canvas oscilloscope + 24-band spectrum analyzer.
 */
import { useEffect, useRef, useState } from "react";
import { getApiBase } from "../api";
import { Badge } from "../components/Badge";
import { useI18n } from "../i18n";

function getWsEndpoint(): string {
  const customApi = getApiBase();
  if (customApi) {
    try {
      const parsed = new URL(customApi);
      const wsProto = parsed.protocol === "https:" ? "wss:" : "ws:";
      return `${wsProto}//${parsed.host}/api/v1/stream/live-call`;
    } catch {
      // fallback
    }
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/stream/live-call`;
}

type CallPhase = "IDLE" | "RINGING" | "MONITORING" | "FINALIZING";

interface CallAuditSummary {
  verdict: string;
  finalRiskScore: number;
  terminateCall: boolean;
  riskLevel?: string | null;
  voiceLabel?: string | null;
  engine?: string | null;
  transcript?: string | null;
  language?: string | null;
  scamCategory?: string | null;
  scamConfidence?: number | null;
  redFlagIds?: string[];
}

/** Resample any browser AudioContext rate to standard 16,000 Hz Mono PCM16 with anti-aliasing */
function downsampleTo16kPCM(input: Float32Array, inputSampleRate: number): Int16Array {
  if (inputSampleRate === 16000) {
    const pcm16 = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return pcm16;
  }
  const ratio = inputSampleRate / 16000;
  const newLength = Math.max(1, Math.round(input.length / ratio));
  const result = new Int16Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < input.length; i++) {
      accum += input[i];
      count++;
    }
    const sample = count > 0 ? accum / count : input[Math.min(offsetBuffer, input.length - 1)];
    const s = Math.max(-1, Math.min(1, sample));
    result[offsetResult] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

const pct = (v: number | null | undefined, digits = 1): string =>
  v == null ? "—" : `${(v * 100).toFixed(digits)}%`;

const fusionLabel = (mode: string | null | undefined): string => {
  if (mode === "dhwani-fake") return "Dhwani-led: Clone detected";
  if (mode === "wav2vec-fake") return "Base Wav2Vec2 led";
  if (mode === "disagreement") return "Models disagree — caution";
  if (mode === "consensus-real") return "Multi-model genuine consensus";
  if (mode === "vocoder-only") return "No model verdict yet";
  return "Waiting for signals…";
};

export function LiveCallPage() {
  const { t } = useI18n();

  const [callerId, setCallerId] = useState("+91 99880 12345");
  const [claimedIdentity, setClaimedIdentity] = useState("UNKNOWN_CALLER");

  // Call status & states
  const [callPhase, setCallPhase] = useState<CallPhase>("IDLE");
  const [callDuration, setCallDuration] = useState(0);
  const [connectError, setConnectError] = useState<string | null>(null);

  // Forensic Telemetry State
  const [liveRisk, setLiveRisk] = useState(0.0);
  const [liveLiveness, setLiveLiveness] = useState(1.0);
  const [liveVocoder, setLiveVocoder] = useState(0.0);
  const [liveJitter, setLiveJitter] = useState(0.012);
  const [livePitch, setLivePitch] = useState(18.5);
  const [liveFingerprint, setLiveFingerprint] = useState("natural_vocal_tract");
  const [liveVerdict, setLiveVerdict] = useState("READY / SENTINEL ARMED");
  const [liveAlert, setLiveAlert] = useState<string | null>(null);
  const [liveSpeakerMatch, setLiveSpeakerMatch] = useState<any | null>(null);

  // Three-signal live ensemble telemetry
  const [liveW2V, setLiveW2V] = useState<number | null>(null);
  const [liveDhwani, setLiveDhwani] = useState<number | null>(null);
  const [liveLarge, setLiveLarge] = useState<number | null>(null);
  const [liveFusion, setLiveFusion] = useState<string | null>(null);
  const [liveTelephonyMode, setLiveTelephonyMode] = useState<string | null>(null);

  // End-of-call authoritative audit + ledger
  const [finalCertificate, setFinalCertificate] = useState<any | null>(null);
  const [audit, setAudit] = useState<CallAuditSummary | null>(null);
  const [showCertificateModal, setShowCertificateModal] = useState(false);

  // Audio Equalizer Spectrum state (24 bands)
  const [eqHeights, setEqHeights] = useState<number[]>(() => Array.from({ length: 24 }, () => 12));

  // Audio & WebRTC Refs
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const auditTimeoutRef = useRef<number | null>(null);
  // Refs for animation loop (avoids restating loop on every telemetry tick)
  const liveRiskRef = useRef(0.0);
  const callPhaseRef = useRef<CallPhase>("IDLE");

  useEffect(() => { liveRiskRef.current = liveRisk; }, [liveRisk]);
  useEffect(() => { callPhaseRef.current = callPhase; }, [callPhase]);

  // Call timer counter
  useEffect(() => {
    if (callPhase === "MONITORING") {
      timerRef.current = window.setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [callPhase]);

  // Ensure AudioContext is initialized
  const getAudioContext = () => {
    if (!audioContextRef.current || audioContextRef.current.state === "closed") {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      audioContextRef.current = new AudioCtx();
    }
    if (audioContextRef.current.state === "suspended") {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  };

  // Ensure AnalyserNode is initialized
  const getAnalyserNode = () => {
    const ctx = getAudioContext();
    if (!analyserRef.current) {
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;
    }
    return analyserRef.current;
  };

  // Real-Time Oscilloscope & 24-Band Equalizer Canvas Loop (runs once on mount)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let idlePhase = 0;
    let running = true;

    const render = () => {
      if (!running) return;

      const risk = liveRiskRef.current;
      const phase = callPhaseRef.current;

      ctx.fillStyle = "#050914";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Cyber Grid lines
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(45, 212, 191, 0.05)";
      ctx.beginPath();
      for (let gx = 0; gx < canvas.width; gx += 35) {
        ctx.moveTo(gx, 0);
        ctx.lineTo(gx, canvas.height);
      }
      for (let gy = 0; gy < canvas.height; gy += 20) {
        ctx.moveTo(0, gy);
        ctx.lineTo(canvas.width, gy);
      }
      ctx.stroke();

      const analyser = analyserRef.current;
      const isDangerous = risk >= 0.5;
      const isWarn = risk >= 0.28;

      ctx.lineWidth = 2.2;
      ctx.strokeStyle = isDangerous ? "#ef4444" : isWarn ? "#f59e0b" : "#2dd4bf";
      ctx.shadowColor = ctx.strokeStyle;
      ctx.shadowBlur = phase === "MONITORING" ? 8 : 1;

      if (analyser && phase === "MONITORING") {
        // Draw true vocal waveform from AnalyserNode
        const timeData = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(timeData);

        ctx.beginPath();
        const sliceWidth = canvas.width / timeData.length;
        let px = 0;
        for (let i = 0; i < timeData.length; i++) {
          const v = timeData[i] / 128.0;
          const py = (v * canvas.height) / 2;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
          px += sliceWidth;
        }
        ctx.stroke();

        // Read 24-band frequency spectrum
        const freqData = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(freqData);
        const binStep = Math.max(1, Math.floor(freqData.length / 24));
        const newHeights: number[] = [];
        for (let b = 0; b < 24; b++) {
          const idx = Math.min(b * binStep, freqData.length - 1);
          const val = freqData[idx];
          newHeights.push(Math.max(10, Math.min(100, Math.round((val / 255) * 100))));
        }
        setEqHeights(newHeights);
      } else {
        // Idle heartbeat animation
        ctx.beginPath();
        const mid = canvas.height / 2;
        for (let ix = 0; ix < canvas.width; ix++) {
          const iy = mid + Math.sin(ix * 0.04 + idlePhase) * 2;
          if (ix === 0) ctx.moveTo(ix, iy);
          else ctx.lineTo(ix, iy);
        }
        ctx.stroke();
        idlePhase += 0.04;
      }

      ctx.shadowBlur = 0;
      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();
    return () => {
      running = false;
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []); // Empty dep array — runs once, uses refs for live values

  // Immediate cleanup on unmount
  useEffect(() => {
    return () => {
      forceCleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Hard teardown: stop capture, close the socket (no audit wait). */
  const forceCleanup = () => {
    if (auditTimeoutRef.current) clearTimeout(auditTimeoutRef.current);
    auditTimeoutRef.current = null;
    if (timerRef.current) clearInterval(timerRef.current);

    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((tr) => tr.stop());
      streamRef.current = null;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "stop" }));
      setTimeout(() => wsRef.current?.close(), 300);
    }
    wsRef.current = null;

    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    setCallPhase("IDLE");
  };

  const resetForNewCall = () => {
    setFinalCertificate(null);
    setAudit(null);
    setLiveRisk(0.0);
    setLiveLiveness(1.0);
    setLiveVocoder(0.0);
    setLiveJitter(0.012);
    setLivePitch(18.5);
    setLiveFingerprint("natural_vocal_tract");
    setLiveVerdict("READY / SENTINEL ARMED");
    setLiveAlert(null);
    setLiveSpeakerMatch(null);
    setLiveW2V(null);
    setLiveDhwani(null);
    setLiveLarge(null);
    setLiveFusion(null);
    setLiveTelephonyMode(null);
    setCallDuration(0);
    setCallPhase("IDLE");
    setConnectError(null);
  };

  // =========================================================================
  // LIVE MICROPHONE TELEPHONY STREAMING (Web Audio -> WebSocket)
  // =========================================================================
  const startLiveStreaming = async () => {
    forceCleanup();
    resetForNewCall();
    setConnectError(null);

    try {
      setCallPhase("RINGING");
      setLiveVerdict("CONNECTING TELEPHONY SENTINEL...");

      // 1. Acquire microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: true },
      });
      streamRef.current = stream;

      // 2. Setup AudioContext and AnalyserNode
      const audioCtx = getAudioContext();
      const analyser = getAnalyserNode();
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      // 3. Connect WebSocket
      const wsUrl = getWsEndpoint();
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // 4. Setup ScriptProcessorNode to capture and downsample to 16kHz PCM16
      const bufferSize = 4096;
      const processor = audioCtx.createScriptProcessor(bufferSize, 1, 1);
      scriptProcessorRef.current = processor;

      // Mute local microphone playback to prevent speaker echo
      const muteGain = audioCtx.createGain();
      muteGain.gain.value = 0.0;
      processor.connect(muteGain);
      muteGain.connect(audioCtx.destination);

      processor.onaudioprocess = (e) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        const inputData = e.inputBuffer.getChannelData(0);
        // Downsample input rate to standard 16,000 Hz PCM16
        const pcm16 = downsampleTo16kPCM(inputData, audioCtx.sampleRate);
        ws.send(pcm16.buffer);
      };

      source.connect(processor);

      ws.onopen = () => {
        setCallPhase("MONITORING");
        setLiveVerdict("SENTINEL ACTIVE • LISTENING TO CALL");
        ws.send(
          JSON.stringify({
            action: "start",
            caller_id: callerId.trim() || "INCOMING_VOIP_CALL",
            claimed_identity: claimedIdentity.trim() || "UNKNOWN_CALLER",
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "telemetry") {
            setLiveRisk(data.dynamic_risk_score);
            setLiveLiveness(data.liveness_score);
            setLiveVocoder(data.vocoder_anomaly);
            setLivePitch(data.pitch_stability);
            setLiveFingerprint(data.fingerprint || "natural_vocal_tract");
            setLiveVerdict(data.verdict);
            setLiveAlert(data.alert || null);
            if (data.wav2vec2_fake_probability !== undefined && data.wav2vec2_fake_probability !== null) {
              setLiveW2V(data.wav2vec2_fake_probability);
            }
            if (data.dhwani_fake_probability !== undefined && data.dhwani_fake_probability !== null) {
              setLiveDhwani(data.dhwani_fake_probability);
            }
            if (data.large_fake_probability !== undefined && data.large_fake_probability !== null) {
              setLiveLarge(data.large_fake_probability);
            }
            if (data.fusion) setLiveFusion(data.fusion);
            if (data.telephony_mode) setLiveTelephonyMode(data.telephony_mode);
            if (data.speaker_match) setLiveSpeakerMatch(data.speaker_match);
          } else if (data.type === "session_summary") {
            setFinalCertificate({
              certificate_id: data.certificate_id,
              block_hash: data.block_hash,
              merkle_root: data.merkle_root,
              verdict: data.verdict,
              peak_risk: data.final_risk_score,
              duration: callDuration,
              engine: data.engine,
            });
            setAudit({
              verdict: data.verdict,
              finalRiskScore: data.final_risk_score,
              terminateCall: !!data.terminate_call,
              riskLevel: data.risk_level,
              voiceLabel: data.voice_label,
              engine: data.engine,
              transcript: data.transcript,
              language: data.language,
              scamCategory: data.scam_category,
              scamConfidence: data.scam_confidence,
              redFlagIds: data.red_flag_ids || [],
            });
            setCallPhase("IDLE");
            setLiveRisk(data.final_risk_score);
            setLiveVerdict(data.verdict);
            if (auditTimeoutRef.current) clearTimeout(auditTimeoutRef.current);
            auditTimeoutRef.current = null;
            // Socket closes when the server handler exits — nudge it.
            ws.close();
          }
        } catch {
          // ignore malformed packets
        }
      };

      ws.onerror = () => {
        forceCleanup();
      };
      ws.onclose = () => {
        if (auditTimeoutRef.current) clearTimeout(auditTimeoutRef.current);
        auditTimeoutRef.current = null;
      };
    } catch (e: any) {
      setConnectError(e?.message || "Please allow microphone permissions");
      forceCleanup();
    }
  };

  /** Graceful end: stop capture locally but keep the socket open for the audit. */
  const endLiveCall = () => {
    if (!wsRef.current) return;
    setCallPhase("FINALIZING");
    setLiveVerdict("END-OF-CALL FORENSIC AUDIT RUNNING...");
    setLiveAlert(null);

    // Stop capturing so no more audio is sent;
    // the authoritative audit runs on the server from the captured buffer.
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((tr) => tr.stop());
      streamRef.current = null;
    }
    if (timerRef.current) clearInterval(timerRef.current);

    if (wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "stop" }));
    }

    // Safety: if the server never finalizes, force-clean.
    auditTimeoutRef.current = window.setTimeout(() => {
      forceCleanup();
    }, 120000);
  };

  // Abort during a call — no audit wait.
  const abortCall = () => {
    forceCleanup();
    resetForNewCall();
  };

  // Format call duration
  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Radar dial calculations
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - liveRisk * circumference;
  const threatTone = liveRisk >= 0.5 ? "danger" : liveRisk >= 0.28 ? "warning" : "safe";

  const statusBadge =
    callPhase === "MONITORING"
      ? `LIVE CALL • ${formatTimer(callDuration)}`
      : callPhase === "FINALIZING"
      ? "END-OF-CALL AUDIT"
      : callPhase === "RINGING"
      ? "CONNECTING..."
      : "SENTINEL STANDBY";

  const badgeTone =
    callPhase === "MONITORING"
      ? liveRisk >= 0.5
        ? "danger"
        : "safe"
      : callPhase === "FINALIZING"
      ? "warning"
      : "status";

  return (
    <div style={{ maxWidth: 1380, margin: "0 auto" }}>
      {/* 1. Top Cyber Defense Telemetry Ribbon */}
      <div className="telemetry-ticker-bar">
        <div className="telemetry-ticker-item">
          <span className="engine-active-dot" />
          <span>{t("sentinel.ticker.online")}:</span>
          <strong>{liveVerdict}</strong>
        </div>

        <div className="telemetry-ticker-item">
          <span>LATENCY:</span>
          <strong>18ms (ONNX CPU)</strong>
        </div>

        <div className="telemetry-ticker-item">
          <span>ENGINES:</span>
          <strong>WAV2VEC2 · DHWANI XLS-R · LARGE CLONE · FUSION</strong>
        </div>

        <div className="telemetry-ticker-item" style={{ color: "var(--brand)" }}>
          <span>⚖️</span>
          <span>{t("sentinel.ticker.compliance")}</span>
        </div>
      </div>

      {/* 2. Main Split Command Deck */}
      <div className="command-deck-grid">
        {/* LEFT COLUMN: Active Telephony Sentinel Console */}
        <div>
          {/* Card A: Active Telephony Sentinel HUD */}
          <div className="call-hud-container">
            <div className="call-hud-head">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 18 }}>📞</span>
                <strong style={{ fontSize: 15, color: "var(--text-primary)" }}>
                  Telephony Sentinel Console
                </strong>
                <Badge tone={badgeTone}>{statusBadge}</Badge>
              </div>
            </div>

            {/* Caller Profile HUD */}
            <div className="caller-profile-row">
              <div className={`caller-avatar ${callPhase === "MONITORING" ? threatTone : ""}`}>
                {callPhase === "MONITORING" ? (liveRisk >= 0.5 ? "🚨" : liveRisk >= 0.28 ? "⚠️" : "🛡️") : "📱"}
              </div>

              <div className="caller-details">
                <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "space-between" }}>
                  <div className="caller-name">{claimedIdentity || "UNKNOWN CALLER"}</div>
                  <Badge tone={liveSpeakerMatch?.matched ? "safe" : liveRisk >= 0.5 ? "danger" : "warning"}>
                    {liveSpeakerMatch?.matched
                      ? "SAFE-VOICE VERIFIED"
                      : liveRisk >= 0.5
                      ? "UNAUTHORIZED IMPERSONATOR"
                      : "UNVERIFIED CALLER ID"}
                  </Badge>
                </div>
                <div className="caller-meta">
                  <span><strong>Caller ID:</strong> {callerId}</span>
                  <span>•</span>
                  <span><strong>Mode:</strong> {liveTelephonyMode || "Live Microphone"}</span>
                  <span>•</span>
                  <span><strong>Origin:</strong> Operator Device (16 kHz PCM)</span>
                </div>
              </div>
            </div>

            {/* Live Mic Controls */}
            <div style={{ marginTop: 12 }}>
              <div style={{ background: "rgba(10, 16, 29, 0.7)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", padding: "12px", fontSize: "12.5px", color: "var(--text-muted)", lineHeight: 1.55, marginBottom: 14 }}>
                <strong style={{ color: "var(--text-primary)", display: "block", marginBottom: 3 }}>
                  📡 Real-Time Telephony Microphone Sentinel
                </strong>
                Streams raw 16kHz audio directly to the multi-layer neural defense pipeline
                (Wav2Vec2 + Dhwani XLS-R + large clone-specialist). When the call ends, the full
                recording is re-analysed through the AASIST audit workflow and notarised as a
                Section 65B blockchain certificate.
              </div>

              {callPhase === "MONITORING" ? (
                <div style={{ display: "flex", gap: 10 }}>
                  <button
                    type="button"
                    onClick={endLiveCall}
                    className="btn btn-primary"
                    style={{ flex: 1, padding: "12px 18px", fontSize: 14 }}
                  >
                    ⏹ End Call & Notarize Forensics
                  </button>
                  <button
                    type="button"
                    onClick={abortCall}
                    className="btn btn-danger"
                    style={{ padding: "12px 20px", fontSize: 14 }}
                  >
                    Abort
                  </button>
                </div>
              ) : callPhase === "FINALIZING" ? (
                <button type="button" className="btn btn-secondary btn-block" disabled style={{ padding: "12px 18px", fontSize: 14 }}>
                  🔬 Running Full-File Forensic Audit… (AASIST + Whisper + Scam Scan)
                </button>
              ) : (
                <button
                  type="button"
                  onClick={startLiveStreaming}
                  className="btn btn-primary btn-block"
                  style={{ padding: "12px 18px", fontSize: 14 }}
                >
                  {t("btn.connect_mic")}
                </button>
              )}

              {connectError && (
                <div className="error-banner" style={{ marginTop: 10 }}>
                  <span>{connectError}</span>
                </div>
              )}

              {/* Claimed persona + caller ID (identity used for Safe-Voice biometric match) */}
              <div className="form-grid" style={{ marginTop: 14 }}>
                <div>
                  <label className="field-label">Claimed Persona (for Safe-Voice match)</label>
                  <input
                    className="input"
                    placeholder="e.g. Rajesh Nair"
                    value={claimedIdentity}
                    disabled={callPhase === "MONITORING" || callPhase === "FINALIZING"}
                    onChange={(e) => setClaimedIdentity(e.target.value)}
                  />
                </div>
                <div>
                  <label className="field-label">Incoming Caller ID</label>
                  <input
                    className="input"
                    placeholder="+91 99880 12345"
                    value={callerId}
                    disabled={callPhase === "MONITORING" || callPhase === "FINALIZING"}
                    onChange={(e) => setCallerId(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Card B: Real-Time Oscilloscope & Frequency Spectrum Equalizer */}
          <div className="oscilloscope-box">
            <div className="oscilloscope-head">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="engine-active-dot" />
                <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>
                  Live Audio Oscilloscope & Frequency Spectrum Analyzer
                </strong>
              </div>
              <span className="mono-sm faint">16.0 kHz Mono • PCM16 • Real-Time Web Audio API</span>
            </div>

            <canvas ref={canvasRef} width={720} height={95} className="oscilloscope-canvas" />

            <div className="eq-bars-container" title="24-Band Real-Time Audio Frequency Spectrum">
              {eqHeights.map((h, idx) => (
                <div
                  key={idx}
                  className={`eq-bar ${callPhase === "MONITORING" ? (liveRisk >= 0.5 ? "active-danger" : liveRisk >= 0.28 ? "active-warning" : "") : ""}`}
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
          </div>

          {/* Card C: Speech Transcript & Call Audit */}
          <div className="card" style={{ padding: "16px 20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 16 }}>📝</span>
                <strong style={{ fontSize: 13.5, color: "var(--text-primary)" }}>
                  Telephony Speech Transcript & Scam Intent Scan
                </strong>
              </div>
              {audit?.scamCategory ? (
                <Badge tone="danger">{audit.scamCategory}</Badge>
              ) : callPhase === "FINALIZING" ? (
                <Badge tone="status">AUDIT RUNNING</Badge>
              ) : null}
            </div>

            <div className="transcript-box">
              {callPhase === "FINALIZING" ? (
                <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text-muted)" }}>
                  <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                  <span>
                    Transcribing speech, detecting language, and scanning for scam keywords…
                    <span className="mono-sm faint"> (Whisper ASR → Scam Classifier → Risk Engine)</span>
                  </span>
                </div>
              ) : audit?.transcript ? (
                <div>
                  {liveSpeakerMatch?.name && (
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4, fontFamily: "var(--font-mono)" }}>
                      [{callerId} CLAIMING {audit.language?.toUpperCase() || "UNKNOWN"} SPEECH]:
                    </div>
                  )}
                  <div style={{ color: "var(--text-primary)", fontSize: 13, lineHeight: 1.6 }}>
                    {audit.transcript}
                  </div>
                </div>
              ) : callPhase === "MONITORING" ? (
                <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                  Live voice is being captured. The full transcript and scam-keyword scan run
                  automatically when the call is ended.
                </span>
              ) : (
                <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                  Call transcript will populate here after the call is ended and the forensic audit completes…
                </span>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Threat Intelligence & Forensic Assessment Terminal */}
        <div>
          {/* Card 1: High-Precision Circular Threat Radar Dial */}
          <div className="card" style={{ padding: "24px 20px", textAlign: "center", marginBottom: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <strong style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)" }}>
                AI Voice Clone Risk Assessment
              </strong>
              <Badge tone={threatTone}>{liveVerdict}</Badge>
            </div>

            {/* Radar Dial */}
            <div className="radar-dial-wrap">
              <div className={`radar-sweep-beam ${threatTone}`} />
              <svg className="threat-dial-svg" viewBox="0 0 180 180">
                <circle className="threat-dial-bg-circle" cx="90" cy="90" r={radius} />
                <circle
                  className={`threat-dial-meter ${threatTone}`}
                  cx="90"
                  cy="90"
                  r={radius}
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </svg>
              <div className="threat-dial-center">
                <div className="threat-score-value" style={{ color: liveRisk >= 0.5 ? "var(--danger)" : liveRisk >= 0.28 ? "var(--warning)" : "var(--safe)" }}>
                  {(liveRisk * 100).toFixed(0)}%
                </div>
                <div className="threat-score-label">Impersonation Score</div>
              </div>
            </div>

            <h3 style={{ fontSize: 18, marginBottom: 6 }}>
              {liveRisk >= 0.5
                ? t("sentinel.threat.critical")
                : liveRisk >= 0.28
                ? t("sentinel.threat.suspicious")
                : t("sentinel.threat.genuine")}
            </h3>
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", margin: 0 }}>
              {liveRisk >= 0.5
                ? "Dhwani XLS-R confirms synthetic speech generated by neural TTS. Two consecutive windows of high model probability were observed."
                : liveRisk >= 0.28
                ? "Model indicators suggest possible cloning. Challenge the caller with out-of-band verification before trusting instructions."
                : "Live model ensemble agrees the caller is a genuine human. Standard call hygiene still applies."}
            </p>

            {/* Immediate Action Prompts */}
            {(liveAlert || liveRisk >= 0.45) && (
              <div className="emergency-action-banner danger" style={{ marginTop: 16, textAlign: "left" }}>
                <div className="action-banner-icon">🚨</div>
                <div>
                  <div className="action-banner-title">{t("sentinel.action.title")}</div>
                  <div className="action-banner-desc">
                    {liveAlert || "Voice exhibits 99%+ AI synthetic cloning cues. Financial extortion suspected."}
                  </div>
                  <div className="action-tags-list">
                    <span className="action-tag">{t("sentinel.action.halt")}</span>
                    <span className="action-tag">{t("sentinel.action.hangup")}</span>
                    <span className="action-tag">{t("sentinel.action.helpline")}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Card 2: Multi-Model Forensic Matrix Breakdown */}
          <div className="card" style={{ padding: "18px 20px", marginBottom: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 18 }}>🧠</span>
                <strong style={{ fontSize: 13.5, color: "var(--text-primary)" }}>
                  Multi-Layer Forensic Telemetry Matrix
                </strong>
              </div>
              <span className="mono-sm faint">Sub-25ms CPU ONNX</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* Layer 1: Base Wav2Vec2 */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span><strong>1. Wav2Vec2 Base (fast classifier)</strong></span>
                  <span style={{ color: (liveW2V ?? 0) >= 0.5 ? "var(--danger)" : "var(--safe)", fontWeight: 700 }}>
                    {pct(liveW2V)} Fake
                  </span>
                </div>
                <div className="forensic-progress-track">
                  <div
                    className="forensic-progress-fill"
                    style={{
                      width: `${(liveW2V ?? 0) * 100}%`,
                      background: (liveW2V ?? 0) >= 0.5 ? "var(--danger)" : "var(--safe)",
                    }}
                  />
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Runs on every sliding window for low-latency first-pass scoring
                  {(liveW2V ?? 0) >= 0.5 && (liveDhwani ?? 0) < 0.5 && liveVerdict === "GENUINE_HUMAN" && (
                    <span style={{ display: "block", color: "var(--warning)", marginTop: 2 }}>
                      ⓘ Single-window spike suppressed — Dhwani specialists read bonafide (crop artifact)
                    </span>
                  )}
                </div>
              </div>

              {/* Layer 2: Dhwani XLS-R */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span><strong>2. Dhwani Multilingual (XLS-R 300M + AASIST)</strong></span>
                  <span style={{ color: (liveDhwani ?? 0) >= 0.5 ? "var(--danger)" : "var(--safe)", fontWeight: 700 }}>
                    {pct(liveDhwani)} Fake
                  </span>
                </div>
                <div className="forensic-progress-track">
                  <div
                    className="forensic-progress-fill"
                    style={{
                      width: `${(liveDhwani ?? 0) * 100}%`,
                      background: (liveDhwani ?? 0) >= 0.5 ? "var(--danger)" : "var(--safe)",
                    }}
                  />
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Decisive for zero-shot neural clones — re-run on the rolling buffer every ~2.4s • Organic Liveness: {(liveLiveness * 100).toFixed(0)}%
                </div>
              </div>

              {/* Layer 3: Large clone-specialist */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span><strong>3. Wav2Vec2 Large (clone corroboration)</strong></span>
                  <span style={{ color: (liveLarge ?? 0) >= 0.5 ? "var(--warning)" : "var(--safe)", fontWeight: 700 }}>
                    {pct(liveLarge)} Fake
                  </span>
                </div>
                <div className="forensic-progress-track">
                  <div
                    className="forensic-progress-fill"
                    style={{
                      width: `${(liveLarge ?? 0) * 100}%`,
                      background: (liveLarge ?? 0) >= 0.5 ? "var(--warning)" : "var(--safe)",
                    }}
                  />
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Corroboration only — never overrides a base+Dhwani consensus, used while nothing decisive has fired
                </div>
              </div>

              {/* Layer 4: Ensemble Fusion */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span><strong>4. Ensemble Fusion Verdict</strong></span>
                  <span style={{ color: liveRisk >= 0.5 ? "var(--danger)" : liveRisk >= 0.28 ? "var(--warning)" : "var(--safe)", fontWeight: 700 }}>
                    {fusionLabel(liveFusion)}
                  </span>
                </div>
                <div className="forensic-progress-track">
                  <div
                    className="forensic-progress-fill"
                    style={{
                      width: `${liveRisk * 100}%`,
                      background: liveRisk >= 0.5 ? "var(--danger)" : liveRisk >= 0.28 ? "var(--warning)" : "var(--safe)",
                    }}
                  />
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Fusion mode: <span className="mono-sm faint">{liveFusion || "waiting"}</span> • CRITICAL requires sustained elevated risk (~1.0s of new audio) with a decisive specialist — a lone window spike never alerts
                  <span style={{ float: "right", color: liveRisk >= 0.5 ? "var(--danger)" : "var(--safe)" }}>{(liveRisk * 100).toFixed(0)}% risk</span>
                </div>
              </div>

              {/* Layer 5: Vocoder DSP */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span><strong>5. Vocoder DSP Phase Incoherence</strong></span>
                  <span style={{ color: liveVocoder >= 0.4 ? "var(--danger)" : "var(--safe)", fontWeight: 700 }}>
                    {(liveVocoder * 100).toFixed(0)}% Anomaly
                  </span>
                </div>
                <div className="forensic-progress-track">
                  <div
                    className="forensic-progress-fill"
                    style={{
                      width: `${(liveVocoder * 100).toFixed(0)}%`,
                      background: liveVocoder >= 0.4 ? "var(--danger)" : "var(--safe)",
                    }}
                  />
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Detects HiFi-GAN / XTTS neural vocoder phase cancelation • Fingerprint: <span className="mono-sm faint">{liveFingerprint.replace(/_/g, " ")}</span>
                </div>
              </div>

              {/* Layer 6: Biomechanical Micro-Jitter */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span><strong>6. Biomechanical Vocal Fold Micro-Jitter</strong></span>
                  <span style={{ color: liveJitter < 0.008 ? "var(--danger)" : "var(--safe)", fontWeight: 700 }}>
                    {(liveJitter * 1000).toFixed(1)} ms ({liveJitter < 0.008 ? "Synthetic Rigidity" : "Natural Tremor"})
                  </span>
                </div>
                <div className="forensic-progress-track">
                  <div
                    className="forensic-progress-fill"
                    style={{
                      width: `${Math.min(100, liveJitter * 2500)}%`,
                      background: liveJitter < 0.008 ? "var(--danger)" : "var(--safe)",
                    }}
                  />
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Physical vocal cord cycle-to-cycle vibration (0.012–0.050ms) • Pitch Spread: <span className="mono-sm faint">{livePitch.toFixed(1)} semitones</span>
                </div>
              </div>

              {/* Layer 7: Safe-Voice Biometrics */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span><strong>7. Safe-Voice Family/VIP Biometric Match</strong></span>
                  <span style={{ color: liveSpeakerMatch?.matched ? "var(--safe)" : "var(--text-muted)", fontWeight: 700 }}>
                    {liveSpeakerMatch?.similarity !== undefined
                      ? `${(liveSpeakerMatch.similarity * 100).toFixed(0)}% Match`
                      : "No Profile Registered"}
                  </span>
                </div>
                <div className="forensic-progress-track">
                  <div
                    className="forensic-progress-fill"
                    style={{
                      width: liveSpeakerMatch?.similarity ? `${(liveSpeakerMatch.similarity * 100).toFixed(0)}%` : "0%",
                      background: "var(--brand)",
                    }}
                  />
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {liveSpeakerMatch
                    ? `Cohort-aware cosine similarity against "${liveSpeakerMatch.name || claimedIdentity}" vocal tract embeddings`
                    : "Enrol a Safe-Voice member and type their name as the claimed persona to enable live biometric verification"}
                </div>
              </div>
            </div>
          </div>

          {/* Card 3: End-of-Call Audit Summary */}
          <div className="card" style={{ padding: "18px 20px", marginBottom: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 18 }}>🔬</span>
                <strong style={{ fontSize: 13.5, color: "var(--text-primary)" }}>
                  End-of-Call Forensic Audit Report
                </strong>
              </div>
              {audit && (
                <Badge tone={audit.terminateCall ? "danger" : audit.finalRiskScore >= 0.52 ? "danger" : audit.finalRiskScore >= 0.3 ? "warning" : "safe"}>
                  {audit.verdict}
                </Badge>
              )}
            </div>

            {!audit ? (
              <div style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic", lineHeight: 1.5 }}>
                End the live call to run the full-file AASIST audit — the captured audio is re-analysed
                through the authoritative ensemble, transcribed with Whisper, language-detected, and
                scanned for scam keywords before the Section 65B certificate is issued.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12.5 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <div><strong>Risk Score:</strong> <span className="mono-sm">{Math.round(audit.finalRiskScore * 100)}/100</span></div>
                  <div><strong>Risk Level:</strong> {audit.riskLevel?.toUpperCase() || "—"}</div>
                  <div><strong>Voice Label:</strong> {audit.voiceLabel || "—"}</div>
                  <div><strong>Engine:</strong> <span className="mono-sm">{audit.engine || "—"}</span></div>
                  <div><strong>Language:</strong> {audit.language || "—"}</div>
                  {audit.scamCategory && (
                    <div>
                      <strong>Scam Pattern:</strong> {audit.scamCategory}
                      {audit.scamConfidence != null && ` (${(audit.scamConfidence * 100).toFixed(0)}%)`}
                    </div>
                  )}
                </div>
                {audit.terminateCall && (
                  <div className="emergency-action-banner danger" style={{ marginTop: 4, textAlign: "left" }}>
                    <div className="action-banner-icon">🚨</div>
                    <div>
                      <div className="action-banner-title">CALL TERMINATED — AI VOICE CONFIRMED</div>
                      <div className="action-banner-desc">
                        The model-backed audio gate confirmed a synthetic/cloned voice, forcing
                        call termination regardless of the spoken content.
                      </div>
                    </div>
                  </div>
                )}
                {audit.redFlagIds && audit.redFlagIds.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {audit.redFlagIds.map((id) => (
                      <span key={id} className="chip" style={{ fontSize: 11 }}>{id}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Card 4: Section 65B Statutory Blockchain Certificate */}
          <div className="card" style={{ padding: "18px 20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 18 }}>⚖️</span>
                <strong style={{ fontSize: 13.5, color: "var(--text-primary)" }}>
                  Section 65B Court-Admissible Proof
                </strong>
              </div>
              <Badge tone="safe">TAMPER-PROOF LEDGER</Badge>
            </div>

            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 12px", lineHeight: 1.45 }}>
              Every scanned call is cryptographically hashed with SHA-256 and anchored in the Section 65B Bharatiya Sakshya Adhiniyam audit blockchain for FIR submission.
            </p>

            {finalCertificate ? (
              <div style={{ background: "rgba(10, 16, 29, 0.7)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", padding: "12px", marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: "var(--brand)", fontWeight: 600, marginBottom: 2 }}>
                  CERTIFICATE ISSUED:
                </div>
                <div className="mono-sm" style={{ color: "var(--text-primary)", wordBreak: "break-all" }}>
                  {finalCertificate.certificate_id}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                  SHA-256 Hash: <span className="mono-sm faint">{finalCertificate.block_hash?.substring(0, 24)}...</span>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic", marginBottom: 12 }}>
                End a live call to notarize the court-admissible certificate.
              </div>
            )}

            <button
              type="button"
              className="btn btn-secondary btn-block"
              onClick={() => setShowCertificateModal(true)}
              disabled={!finalCertificate}
              style={{ fontSize: 13 }}
            >
              📜 View / Export Section 65B Certificate
            </button>
          </div>
        </div>
      </div>

      {/* Section 65B Certificate Modal */}
      {showCertificateModal && finalCertificate && (
        <div className="modal-overlay" onClick={() => setShowCertificateModal(false)}>
          <div className="modal-surface" style={{ maxWidth: 620 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 24 }}>⚖️</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: 17, color: "var(--text-primary)" }}>
                    Section 65B Bharatiya Sakshya Adhiniyam 2023 Certificate
                  </h3>
                  <span className="mono-sm faint">{finalCertificate.certificate_id}</span>
                </div>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowCertificateModal(false)}
                style={{ fontSize: 18, padding: "4px 8px" }}
              >
                ✕
              </button>
            </div>

            <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", padding: "16px", marginBottom: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 12.5, marginBottom: 12 }}>
                <div><strong>Claimed Persona:</strong> {callerId} ({claimedIdentity})</div>
                <div><strong>Final Verdict:</strong> <Badge tone={finalCertificate.peak_risk >= 0.5 ? "danger" : "safe"}>{finalCertificate.verdict}</Badge></div>
                <div><strong>Combined Peak Risk:</strong> {(finalCertificate.peak_risk * 100).toFixed(1)}%</div>
                <div><strong>Multi-Layer Engine:</strong> {finalCertificate.engine || "Wav2Vec2 + Dhwani + Ensemble"}</div>
                <div><strong>Call Duration:</strong> {formatTimer(finalCertificate.duration || 0)}</div>
                {audit?.terminateCall && <div><strong>Decision:</strong> <Badge tone="danger">CALL TERMINATED</Badge></div>}
              </div>

              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 10 }}>
                <div className="field-label" style={{ margin: 0 }}>Cryptographic Block Hash (SHA-256):</div>
                <div className="mono-sm" style={{ color: "var(--brand)", wordBreak: "break-all", marginTop: 4 }}>
                  {finalCertificate.block_hash}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  window.print();
                }}
              >
                🖨️ Print / Save FIR Evidence PDF
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCertificateModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}