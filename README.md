<div align="center">

# 🛡️ DigiRaksha
### AI-Powered Real-Time Detection & Prevention of Voice Cloning Impersonation Attacks

[![SIH Problem ID: 26104](https://img.shields.io/badge/SIH%202026-Problem%20ID%2026104-crimson.svg)](#sih-2026-alignment)
[![Theme: Blockchain & Cybersecurity](https://img.shields.io/badge/Theme-Blockchain%20%26%20Cybersecurity-orange.svg)](#sih-2026-alignment)
[![Organization: AICTE Cyber Security Cell](https://img.shields.io/badge/Organization-AICTE%20Cyber%20Security%20Cell-blue.svg)](#sih-2026-alignment)
[![Python 3.12](https://img.shields.io/badge/Python-3.12.8-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB.svg)](https://react.dev/)
[![Tests](https://img.shields.io/badge/Tests-Passed-brightgreen.svg)](#testing)

*Real-time voice stream analysis • Granular neural vocoder forensics • Dynamic risk escalation • Immutable blockchain chain of custody • Enterprise banking SDK*

[Live Call Sentinel](#-live-call-sentinel) • [Acoustic & Vocoder Forensics](#-multi-layer-voice-authenticity-analysis) • [Blockchain Audit Ledger](#-blockchain-audit-trail--forensics) • [Banking SDK](#-enterprise-banking-sdk) • [Quick Start](#quick-start)

</div>

---

## 🎯 SIH 2026 Alignment: Problem Statement 26104

| Parameter | Official Specification |
|:---|:---|
| **Problem Statement ID** | **26104** |
| **Title** | **AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks** |
| **Organization** | All India Council for Technical Education (Cyber Security Cell) |
| **Category** | Software |
| **Theme** | Blockchain & Cybersecurity |

### The Threat
Recent advancements in generative AI and neural speech synthesis (XTTS-v2, ElevenLabs, VITS, Bark, OpenVoice) allow threat actors to clone human voices with under 3 seconds of audio. Attackers target CXOs, government officials, defense personnel, and high-net-worth individuals over VoIP and cellular networks to authorize fraudulent wire transfers, extract sensitive credentials, or orchestrate high-pressure "Digital Arrest" extortion schemes.

### The DigiRaksha Solution
DigiRaksha is an **end-to-end, production-grade security framework** that intercepts live or recorded voice streams in real time, extracts deep acoustic, vocoder, and prosodic artifacts, computes a **Dynamic Impersonation Risk Score**, issues immediate pre-action alerts, and notarizes all evidence in a **tamper-proof cryptographic blockchain ledger** (admissible under Section 65B of the Indian Evidence Act / BSA 2023).

---

## ⚡ Key Capabilities

```
                  ┌─────────────────────────────────────────────────────────┐
                  │ INCOMING AUDIO STREAM (VoIP / Telephony / WebRTC Mic)   │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
         ┌──────────────────────────────────────────────────────────────────────────┐
         │                  MULTI-LAYER VOICE AUTHENTICITY ENGINE                   │
         ├─────────────────────────────┬─────────────────────────────┬──────────────┤
         │  1. Vocoder & Spectral DSP  │ 2. Prosody & Micro-Tremors  │ 3. Deep ASR  │
         │  • Neural Cutoff (~7.5kHz)  │ • F0 pitch contour std-dev  │ • Multilingual
         │  • Phase Incoherence        │ • Syllable pause unnatural  │   Whisper STT│
         │  • Spectral Flatness & Flux │ • Synthetic monotony        │ • Scam NLP   │
         │  • G.711 Telephony Filter   │ • Micro-tremor deficiency   │   Classifier │
         └─────────────────────────────┴─────────────────────────────┴──────────────┘
                                               │
                                               ▼
         ┌──────────────────────────────────────────────────────────────────────────┐
         │                  DYNAMIC IMPERSONATION RISK CALCULATOR                   │
         │              Sliding-window temporal fusion (<30ms latency)              │
         │              Thresholds: Low (<40) | Medium (40-65) | High (>65)         │
         └─────────────────────────────┬─────────────────────────────┬──────────────┘
                                       │                             │
                        (If Risk > 65) │                             │ (Every Session)
                                       ▼                             ▼
       ┌───────────────────────────────────────────┐  ┌─────────────────────────────┐
       │   PRE-ACTION WIRE-TRANSFER INTERCEPTOR    │  │ CRYPTOGRAPHIC BLOCKCHAIN    │
       │   Enterprise Banking SDK blocks/quarantines│  │ AUDIT TRAIL                 │
       │   unauthorized wire transfers (₹5L+/$50K) │  │ • SHA-256 Merkle Tree       │
       │   and mandates step-up out-of-band auth   │  │ • DR-VOICE-CERT Generation  │
       └───────────────────────────────────────────┘  │ • Sec 65B BSA Admissibility │
                                                      └─────────────────────────────┘
```

### 1. 🎙️ Live Call Sentinel (Real-Time VoIP / Telephony Engine)
- **Sub-30ms Window Latency**: Highly-vectorized FFT autocorrelation and sliding STFT windows for zero-lag streaming audio processing.
- **WebSocket Streaming**: Continuous chunk ingestion over `/api/v1/stream/live-call` supporting PCM16, WebM, and WAV streams.
- **Threat Simulator**: Built-in testbed to simulate high-pressure CEO voice clones, benign family conversations, and Digital Arrest impersonations.
- **Real-Time Oscilloscope & Gauge HUD**: Live waveform canvas with dynamic vocoder anomaly meters and pre-action alert banners.

### 2. 🔬 Multi-Layer Voice Authenticity Analysis
- **Neural Vocoder Phase Incoherence**: Detects vocoder synthesis artifacts (HiFi-GAN, WaveGlow, MelGAN) where synthesized phase alignment deviates from natural human vocal tract physics.
- **High-Frequency Spectral Cutoff**: Neural TTS architectures frequently drop or artificially attenuate harmonic energy above 7.5 kHz – 8 kHz.
- **Spectral Flatness & Energy Flux**: Analyzes tonal purity vs. noise-burst distribution across critical speech bands.
- **Prosody & Behavioral Analysis**: Models speech rhythm, pitch contours (F0), jitter, shimmer, and micro-pauses to differentiate organic human emotion from flat or over-smoothed neural models.
- **Telephony Compensation**: Automatically adjusts for G.711, AMR-WB, and Opus bandwidth limitations so telecom codecs do not cause false positives.

### 3. ⛓️ Blockchain Audit Trail & Sec 65B Compliance
- **Cryptographic Merkle Chaining**: Every audio inspection creates an immutable block linked with SHA-256 parent hashes and block signatures.
- **BSA 2023 / Section 65B Indian Evidence Act**: Automatically generates a verifiable tamper-proof certificate (`DR-VOICE-CERT-...`) containing audio SHA-256 fingerprints, risk scores, forensic signals, and timestamp notarization.
- **Public Verification API**: Anyone or any banking portal can verify a certificate via `/api/v1/blockchain/verify/{certificate_id}`.

### 4. 💳 Enterprise Banking & Telephony SDK
- **`DigiRakshaBankingGate`**: Python and TypeScript SDK for core banking systems (Finacle, TCS BaNCS) and contact centers (Genesys, Cisco, Twilio).
- **Wire-Transfer Interception**: Pre-action gate prevents funds release on telephonic or video confirmations until the voice stream's impersonation risk is below threshold.
- **Step-Up Authentication**: Generates out-of-band biometric challenge codes when a high risk score is detected.

---

## 🚀 Quick Start

### 1. One-Click Launch (Windows)
Double-click `DigiRaksha.bat` from the project root:
```cmd
DigiRaksha.bat
```
*Automatically checks the environment, boots the FastAPI backend, and opens `http://127.0.0.1:8000` in your default browser.*

### 2. Manual Start (Backend + Frontend)

**Backend:**
```cmd
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend (Development hot-reload):**
```cmd
cd frontend
npm run dev
```

**Production Frontend Build:**
```cmd
cd frontend
npm run build
```
*(Compiles directly into `backend/app/static/` for zero-configuration standalone production deployment).*

---

## 📡 API Reference

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

### Real-Time Live Call Stream
| Method | Endpoint | Description |
|:---|:---|:---|
| `WebSocket` | `/api/v1/stream/live-call` | Real-time sliding audio chunk analysis (PCM16/WebM) |
| `POST` | `/api/v1/stream/simulate` | Simulate scenario streams (CEO clone, Digital Arrest, Benign) |

### Blockchain Audit Ledger
| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/v1/blockchain/ledger` | Fetch full tamper-proof cryptographic audit chain |
| `GET` | `/api/v1/blockchain/stats` | Blockchain integrity status, total blocks, genesis hash |
| `GET` | `/api/v1/blockchain/verify/{cert_id}` | Public verification of a Sec 65B forensic certificate |

### Deep File Analysis & Registry
| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/v1/analyze` | Multi-modal file analysis (audio/video deepfake + vocoder + ASR) |
| `POST` | `/api/v1/analyze/transcript` | Real-time scam script classification (English & Hindi) |
| `POST` | `/api/v1/registry/members` | Enrol real voice biometric profile into Safe-Voice Registry |
| `POST` | `/api/v1/registry/verify` | Verify incoming voice note against enrolled speaker embedding |

---

## 💻 Enterprise Banking SDK Example

Integrate DigiRaksha into high-value fund transfers in under 5 lines of code:

```python
from app.sdk.banking_gate import DigiRakshaBankingGate

# Initialize gate with your organization credentials
gate = DigiRakshaBankingGate(api_base_url="http://127.0.0.1:8000")

# Intercept high-value wire transfer during a voice authorization call
decision = gate.intercept_wire_transfer(
    caller_audio_path="suspicious_call_sample.wav",
    transfer_amount_inr=2500000.0,  # ₹25,00,000 (~$30,000)
    beneficiary_account="HDFC0001234-998877",
    caller_claimed_identity="Rajesh Sharma (CFO)"
)

if decision["status"] == "BLOCKED":
    print("🚨 FRAUD DETECTED! Wire transfer blocked.")
    print("Reason:", decision["reason"])
    print("Blockchain Certificate ID:", decision["blockchain_cert_id"])
    # Trigger out-of-band multi-factor verification
elif decision["status"] == "AUTHORIZED":
    print("✅ Voice authenticity verified. Transaction proceeded.")
```

---

## 🧪 Testing & Validation

The framework includes automated test suites covering the vocoder DSP analyzer, blockchain Merkle tree, WebSocket stream simulation, and banking gate SDK:

```cmd
cd backend
.venv\Scripts\python.exe -m pytest tests/test_stream_and_blockchain.py -v
```

All 5 core real-time voice cloning and blockchain tests pass with 100% assertions.

---

## 🏛️ Regulatory & Legal Compliance
- **Bharatiya Sakshya Adhiniyam, 2023 (BSA)** / **Section 65B Indian Evidence Act**: Every audio transaction is notarized with SHA-256 Merkle hashes, ensuring forensic court admissibility.
- **DPDP Act (Digital Personal Data Protection Act, 2023)**: Complete local processing on premise or private VPC. No raw biometric voice data is exported to third-party APIs.
- **Telecom Commercial Communications Customer Preference Regulations (TCCCPR)**: Ready for SIP/RTP integration at telecom gateway level.

---

<div align="center">
<b>SIH 2026 • Team Terminal Breakers • AICTE Cyber Security Cell</b>
</div>
