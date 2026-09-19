# Brag Plan: DigiRaksha (Full UI Walkthrough)

## What is this app?
DigiRaksha is an AI-powered real-time cybersecurity platform that intercepts live telephony streams, detects neural voice clone impersonation attacks in under 30 milliseconds, blocks unauthorized wire transfers, and logs tamper-proof cryptographic evidence to a blockchain ledger.

## The angle
Comprehensive, module-by-module walkthrough of the real DigiRaksha UI. Demonstrates how enterprise security teams, banks, and law enforcement monitor threats, intercept live spoofed calls, run deep forensic DSP analyses, freeze multimillion-rupee transactions, and generate court-admissible certificates.

## Duration: 54 seconds
## Format: 1920x1080 (Landscape)

## Storyboard (Real UI Screen by Screen)

### Scene 1 (0.0s – 8.0s) — Problem & System Architecture Overview
- **UI Screen**: Mission Control & Architecture Overview
- **Visuals**:
  - SIH 2026 Problem ID: 26104 header
  - Live Threat Counter: "AI Voice Cloning attacks up 400% in 2026"
  - End-to-End System Architecture: Incoming Call → Dhwani AI + Vocoder DSP → Dynamic Risk Score → Banking Interceptor → Blockchain Ledger.
- **Narration/Text**: "Attackers clone human voices in 3 seconds. DigiRaksha stops them in under 30 milliseconds."

### Scene 2 (8.0s – 17.0s) — Module 1: The Command Dashboard (`DashboardPage`)
- **UI Screen**: Real `DashboardPage` layout
- **Visuals**:
  - 4 Stat Cards: `Cases: 14,820`, `Evidence: 3,412`, `Scans: 89,204`, `Reported Numbers: 1,290`
  - Scam Category Breakdown: `Digital Arrest (42%)`, `CEO Wire Fraud (38%)`, `Family Emergency (20%)`
  - Risk Distribution Donut Chart: `Low: 64%`, `Medium: 22%`, `High: 14%`
  - System Status indicators: Dhwani ONNX (Online), Vocoder DSP (Online), Blockchain Node (Synced).
- **Callout**: "Centralized threat telemetry with real-time risk distribution across VoIP trunks."

### Scene 3 (17.0s – 27.0s) — Module 2: Live Call Sentinel (`LiveCallPage`)
- **UI Screen**: Real `LiveCallPage` Sentinel HUD
- **Visuals**:
  - Active Call: `SIP Trunk #04 // Incoming from +91 99880 12345 (CEO Rajesh Nair)`
  - Real-time Audio Waveform & 24-Band FFT Spectrum Analyzer
  - Live Streaming Transcript: *"Hi, Rajesh here. Urgent meeting with board. Transfer 48 Lakhs via RTGS within 15 minutes..."*
  - Keyword Flags: `urgent meeting`, `RTGS wire transfer`, `48 Lakhs`
  - NLP Scam Classifier: `CEO IMPERSONATION FRAUD (Confidence: 98.8%)`
- **Callout**: "Real-time telephony stream interception with live ASR transcription and scam intent classification."

### Scene 4 (27.0s – 36.0s) — Module 3: Deep Voice Forensics Engine (`AnalyzePage`)
- **UI Screen**: Real `AnalyzePage` Forensic Matrix
- **Visuals**:
  - Audio Spectrum Inspector with 7.5 kHz Cutoff marker
  - Acoustic Artifact telemetry:
    - `Neural Vocoder Cutoff: 7.5 kHz (SYNTHETIC ARTIFACT)`
    - `Phase Incoherence: 0.94 (ANOMALOUS VOCODER PHASING)`
    - `Spectral Flatness: FLAT (NEURAL SYNTHESIS SIGNATURE)`
    - `Dhwani XLS-R 300M AI: SYNTHETIC VOICE (99.2%)`
- **Callout**: "Multi-layer acoustic forensics detecting sub-perceptual vocoder anomalies invisible to the human ear."

### Scene 5 (36.0s – 45.0s) — Module 4: Pre-Action Banking Interceptor (`SdkDocsPage`)
- **UI Screen**: Pre-Action Wire Transfer Interceptor Dialog
- **Visuals**:
  - Dynamic Impersonation Risk Score spikes to `96 / 100` (CRITICAL)
  - Banking Interceptor Dialog slams down:
    - `TRANSACTION ID: #RTGS-904128`
    - `AMOUNT: ₹48,00,000.00`
    - `STATUS: QUARANTINED BEFORE CORE BANKING EXECUTION`
  - Out-of-band biometric challenge initiated.
- **Callout**: "Pre-action banking interceptor freezes high-value wire transfers before money leaves the bank."

### Scene 6 (45.0s – 54.0s) — Module 5: Blockchain Custody & Legal Admissibility (`BlockchainPage`)
- **UI Screen**: `BlockchainPage` Immutable Audit Trail
- **Visuals**:
  - Merkle Tree computation & SHA-256 root: `0x7f8a92b3...e4c19d`
  - Tamper-proof certificate: `DR-VOICE-CERT-2026-904128`
  - Legal compliance stamp: `Section 65B Bharatiya Sakshya Adhiniyam (BSA) 2023 Admissible`
  - Final Grand Brand Outro: `🛡️ DigiRaksha — Terminal Breakers (SIH 2026)`
- **Callout**: "Every millisecond of forensic evidence sealed into an immutable, court-admissible blockchain ledger."
