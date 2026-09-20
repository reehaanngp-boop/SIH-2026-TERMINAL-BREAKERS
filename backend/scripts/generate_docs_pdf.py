"""Generate a comprehensive, publication-grade PDF documentation & installation guide for DigiRaksha."""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
OUT_PDF = DOCS_DIR / "DigiRaksha_System_and_Installation_Guide.pdf"


class NumberedCanvas(canvas.Canvas):
    """Canvas for adding page numbers and running headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (on pages > 1)
        if self._pageNumber > 1:
            self.drawString(16 * mm, 285 * mm, "DigiRaksha — AI Voice Cloning & Digital Arrest Scam Shield | System & Installation Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(16 * mm, 282 * mm, 194 * mm, 282 * mm)

        # Running footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(194 * mm, 10 * mm, page_text)
        self.drawString(16 * mm, 10 * mm, "CONFIDENTIAL & PROPRIETARY — Smart India Hackathon 2026 (SIH PS 26104)")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(16 * mm, 14 * mm, 194 * mm, 14 * mm)
        self.restoreState()


def generate_pdf():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
        title="DigiRaksha — System & Installation Manual",
        author="DigiRaksha SIH 2026 Team (Terminal Breakers)",
    )

    styles = getSampleStyleSheet()

    # Custom color tokens
    primary_color = colors.HexColor("#0f766e")       # Deep Teal
    dark_teal = colors.HexColor("#115e59")           # Dark Teal
    accent_blue = colors.HexColor("#0284c7")         # Sky Blue
    danger_crimson = colors.HexColor("#b91c1c")      # Red
    warning_amber = colors.HexColor("#d97706")       # Amber
    success_emerald = colors.HexColor("#047857")     # Emerald
    text_dark = colors.HexColor("#0f172a")           # Slate 900
    text_muted = colors.HexColor("#475569")          # Slate 600
    bg_light = colors.HexColor("#f8fafc")            # Slate 50
    bg_subtle = colors.HexColor("#f1f5f9")           # Slate 100
    border_color = colors.HexColor("#cbd5e1")        # Slate 300

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
        alignment=0,
        spaceAfter=2,
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14.5,
        textColor=text_muted,
        spaceAfter=8,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=dark_teal,
        spaceBefore=11,
        spaceAfter=5,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.2,
        textColor=text_dark,
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "BulletDark",
        parent=body_style,
        leftIndent=10,
        bulletIndent=3,
        spaceAfter=2.5,
    )

    code_style = ParagraphStyle(
        "CodeSnippet",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7.8,
        leading=10.8,
        textColor=colors.HexColor("#0f172a"),
    )

    callout_style = ParagraphStyle(
        "CalloutText",
        parent=body_style,
        fontSize=8.2,
        leading=11.5,
        textColor=colors.HexColor("#0c4a6e"),
    )

    story = []

    def make_code_box(code_text: str):
        t = Table([[Paragraph(code_text, code_style)]], colWidths=[182 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("BOX", (0, 0), (-1, -1), 0.8, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    def make_callout(text: str, bg="#f0fdf4", border="#10b981", title="NOTE"):
        content = f"<b>[{title}]</b> {text}"
        p = Paragraph(content, callout_style)
        t = Table([[p]], colWidths=[182 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
            ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor(border)),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # =========================================================================
    # PAGE 1: Title, Metadata, Problem Statement Alignment & Architecture
    # =========================================================================
    story.append(Paragraph("DigiRaksha", title_style))
    story.append(Paragraph(
        "AI-Powered Real-Time Detection & Prevention of Voice Cloning Impersonation Attacks<br/>"
        "<b>Complete System Architecture, Forensic Methodology & Installation Manual</b>",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=0, spaceAfter=8))

    meta_data = [
        [
            Paragraph("<b>Problem Statement ID:</b> SIH 2026 - 26104", body_style),
            Paragraph("<b>Organization:</b> AICTE Cyber Security Cell", body_style)
        ],
        [
            Paragraph("<b>Theme:</b> Blockchain & Cybersecurity", body_style),
            Paragraph("<b>Category:</b> Software / Production Ready", body_style)
        ],
        [
            Paragraph("<b>Team:</b> Terminal Breakers", body_style),
            Paragraph("<b>Core Stack:</b> Python 3.12, FastAPI, React 19, Whisper, AASIST", body_style)
        ],
        [
            Paragraph("<b>Compliance:</b> BSA 2023 / Section 65B Indian Evidence Act", body_style),
            Paragraph("<b>SLA & Latency:</b> Real-time sliding window &lt; 30 ms", body_style)
        ],
    ]
    t_meta = Table(meta_data, colWidths=[91 * mm, 91 * mm])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 4))

    story.append(Paragraph("1. Executive Threat Overview & SIH 2026 Mission", h1_style))
    story.append(Paragraph(
        "With recent advancements in deep learning speech synthesis (XTTS-v2, ElevenLabs, VITS, Bark, OpenVoice), "
        "cybercriminals can clone any human voice using under 3 seconds of reference audio. In India, threat syndicates "
        "weaponize cloned voices across VoIP and cellular networks to orchestrate high-pressure <b>Digital Arrest</b> schemes "
        "(falsely posing as CBI, ED, Police officers, or judges) and unauthorized <b>high-value wire transfers</b> targeting "
        "enterprises and vulnerable citizens.",
        body_style
    ))
    story.append(Paragraph(
        "<b>DigiRaksha</b> is a comprehensive, production-grade cybersecurity platform that intercepts live voice streams, "
        "performs multi-layer acoustic and vocoder forensics, dynamically computes an Impersonation Risk Score, halts "
        "unauthorized wire transfers in real time, and logs forensic proof in an immutable <b>cryptographic blockchain ledger</b> "
        "fully admissible under Bharatiya Sakshya Adhiniyam (BSA) 2023 / Section 65B of the Indian Evidence Act.",
        body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("2. System Architecture & Multi-Layer Pipeline", h1_style))
    story.append(Paragraph(
        "DigiRaksha implements a zero-lag (&lt;30ms) multi-layer forensic inspection matrix designed for telecom carriers, "
        "call centers and personal desktop clients:",
        body_style
    ))

    arch_table_data = [
        [Paragraph("<b>Pipeline Layer</b>", body_style), Paragraph("<b>Technology / Engine</b>", body_style), Paragraph("<b>Forensic Mechanics & Function</b>", body_style)],
        [
            Paragraph("<b>1. Live Call Sentinel</b>", body_style),
            Paragraph("WebSocket Streaming + FFT Buffer", body_style),
            Paragraph("Sliding STFT windows (500ms chunks, 250ms hop); sub-30ms latency; audio normalization and G.711 telephony codec compensation.", body_style)
        ],
        [
            Paragraph("<b>2. Vocoder DSP Forensics</b>", body_style),
            Paragraph("HiFi-GAN / XTTS Spectral DSP", body_style),
            Paragraph("Detects neural vocoder phase incoherence, unnatural high-frequency cutoffs (~7.5 kHz), spectral flatness anomalies, and energy flux.", body_style)
        ],
        [
            Paragraph("<b>3. Biomechanical Jitter & F0</b>", body_style),
            Paragraph("Acoustic DSP + Pitch Tracking", body_style),
            Paragraph("Evaluates human vocal fold vibration irregularity (cycle-to-cycle perturbation). Cloned voices lack physiological micro-tremors.", body_style)
        ],
        [
            Paragraph("<b>4. Anti-Spoofing DL</b>", body_style),
            Paragraph("AASIST (Graph Attention)", body_style),
            Paragraph("Self-supervised spectral graph attention network classifying neural speech synthesis artifacts and recording replay attacks.", body_style)
        ],
        [
            Paragraph("<b>5. Multilingual ASR & NLP</b>", body_style),
            Paragraph("Whisper + TF-IDF Threat Classifier", body_style),
            Paragraph("Transcribes English and Hindi streams; extracts high-risk scam triggers (Digital Arrest, fake courier, narcotics, urgent RTGS transfer).", body_style)
        ],
        [
            Paragraph("<b>6. Dynamic Risk Fusion</b>", body_style),
            Paragraph("Temporal Bayesian Fusion", body_style),
            Paragraph("Fuses physical acoustic, vocoder, and linguistic signals into a continuous 0–100 threat score: Safe (&lt;40), Suspicious (40–65), Critical (&gt;65).", body_style)
        ],
        [
            Paragraph("<b>7. Pre-Action Banking Gate</b>", body_style),
            Paragraph("DigiRakshaBankingGate SDK", body_style),
            Paragraph("Pre-action wire transfer blocker; halts transfers exceeding Rs 5 Lakhs if voice risk is elevated; mandates step-up MFA challenge codes.", body_style)
        ],
        [
            Paragraph("<b>8. Blockchain Audit Ledger</b>", body_style),
            Paragraph("SHA-256 Merkle Chain + Sec 65B", body_style),
            Paragraph("Notarizes every session hash and audio fingerprint; issues court-ready DR-VOICE-CERT certificates with statutory evidence admissibility.", body_style)
        ],
    ]
    t_arch = Table(arch_table_data, colWidths=[38 * mm, 46 * mm, 98 * mm])
    t_arch.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, border_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    story.append(t_arch)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: Deep Dive - How the Tool Works
    # =========================================================================
    story.append(Paragraph("3. In-Depth Operational Mechanics: How DigiRaksha Works", h1_style))

    story.append(Paragraph("A. Real-Time Neural Vocoder & Spectral DSP Forensics", h2_style))
    story.append(Paragraph(
        "Commercial neural speech synthesizers (XTTS-v2, HiFi-GAN, WaveGlow, MelGAN) operate by generating mel-spectrograms "
        "and synthesizing time-domain waveforms via neural vocoders. This process leaves distinct mathematical anomalies:",
        body_style
    ))
    story.append(Paragraph("<b>1. High-Frequency Spectral Cutoff:</b> Neural vocoders are typically trained on audio sampled at 16 kHz or 22 kHz, "
                           "causing harmonic energy to drop sharply or behave unnaturally above 7.5 kHz – 8 kHz. Natural human speech over wideband networks preserves continuous decay.", bullet_style))
    story.append(Paragraph("<b>2. Phase Incoherence:</b> Neural speech generators do not adhere to the physical acoustic laws of the human vocal tract, producing phase discontinuities across successive STFT frames.", bullet_style))
    story.append(Paragraph("<b>3. Spectral Flatness & Flux:</b> Synthetic speech exhibits unnaturally smoothed or artificially noisy frequency bands compared to the rich harmonic resonances (formants F1-F4) of genuine speech.", bullet_style))

    story.append(Paragraph("B. Biomechanical Vocal Fold Micro-Jitter & Prosody Dynamics", h2_style))
    story.append(Paragraph(
        "Biological speech production is governed by the physical vibration of the vocal folds. Even the steadiest human speaker "
        "exhibits cycle-to-cycle frequency perturbations (micro-jitter between 0.012ms and 0.050ms) and amplitude shimmer. "
        "Neural clones either over-smooth these dynamics (resulting in robotic monotony) or inject synthetic Gaussian noise that lacks natural vocal tract correlations. "
        "DigiRaksha evaluates continuous F0 pitch contours, pause regularity (gap CV), and syllable rate dynamics to detect synthesis.",
        body_style
    ))

    story.append(Paragraph("C. Multilingual Scam-Script NLP Engine", h2_style))
    story.append(Paragraph(
        "In tandem with acoustic forensics, DigiRaksha streams audio through an optimized Whisper speech-to-text engine. "
        "The transcript is evaluated in real time by a hybrid TF-IDF + Logistic Regression classifier and specialized regex heuristic rule engine "
        "trained on actual Indian cybercrime call transcripts. The system detects 6 critical threat classes:",
        body_style
    ))
    threat_cats = [
        [Paragraph("<b>Threat Category</b>", body_style), Paragraph("<b>Key Verbal Indicators & Script Patterns</b>", body_style), Paragraph("<b>Risk Tier</b>", body_style)],
        [Paragraph("Digital Arrest", body_style), Paragraph("Fake police/CBI/ED warrants, Skype/WhatsApp video arrest, illegal parcel, narcotics, money laundering.", body_style), Paragraph("<font color='#b91c1c'><b>CRITICAL</b></font>", body_style)],
        [Paragraph("Fake Courier Extortion", body_style), Paragraph("FedEx/Customs parcel seized, banned medicines, Taiwan/Dubai parcel, Aadhaar card misuse.", body_style), Paragraph("<font color='#b91c1c'><b>CRITICAL</b></font>", body_style)],
        [Paragraph("Wire / RTGS Fraud", body_style), Paragraph("Urgent CEO wire transfer, vendor bank update, confidential acquisition, override protocol.", body_style), Paragraph("<font color='#b91c1c'><b>CRITICAL</b></font>", body_style)],
        [Paragraph("Kin in Distress", body_style), Paragraph("Son/daughter arrested in college, serious accident, urgent bail money, kidnap ransom demand.", body_style), Paragraph("<font color='#d97706'><b>HIGH</b></font>", body_style)],
        [Paragraph("OTP / Banking Phishing", body_style), Paragraph("Credit card reward points expiry, electricity disconnection, PAN card KYC update, APK download.", body_style), Paragraph("<font color='#d97706'><b>HIGH</b></font>", body_style)],
        [Paragraph("Benign Conversation", body_style), Paragraph("Routine business briefings, family greetings, verified customer service interactions.", body_style), Paragraph("<font color='#047857'><b>SAFE</b></font>", body_style)],
    ]
    t_threats = Table(threat_cats, colWidths=[40 * mm, 110 * mm, 28 * mm])
    t_threats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, border_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_threats)
    story.append(Spacer(1, 6))

    story.append(Paragraph("D. Dynamic Impersonation Risk Calculator", h2_style))
    story.append(Paragraph(
        "DigiRaksha combines a model-backed voice authenticity score (40%) — from the Wav2Vec2 ASVspoof ensemble and the multilingual Dhwani "
        "detector — with the NLP scam-language semantic threat probability (35%) into a composite 0–100 score. The score is evaluated continuously "
        "over sliding temporal windows. If risk exceeds 65, the system immediately triggers pre-action interceptors, displays red warning banners, "
        "activates audio alerts, and challenges callers with out-of-band verification.",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: Blockchain & Sec 65B Compliance, Enterprise Banking Gate
    # =========================================================================
    story.append(Paragraph("4. Blockchain Audit Trail & Section 65B Statutory Admissibility", h1_style))
    story.append(Paragraph(
        "Under the <b>Bharatiya Sakshya Adhiniyam, 2023 (BSA)</b> and Section 65B of the Indian Evidence Act, digital evidence must maintain an "
        "unbroken, provable chain of custody to be admissible in a court of law. DigiRaksha incorporates a cryptographic blockchain ledger:",
        body_style
    ))
    story.append(Paragraph("<b>1. Merkle Chaining:</b> Each analyzed call session generates an immutable block containing the SHA-256 hash of the audio, "
                           "forensic telemetry metrics, timestamps, caller ID metadata, and the parent block hash. Modifying any historical block invalidates the entire chain.", bullet_style))
    story.append(Paragraph("<b>2. Tamper-Proof Certificate Generation:</b> DigiRaksha issues automated forensic certificates (e.g., <code>DR-VOICE-CERT-202609-8F2A1C</code>) "
                           "containing cryptographic signatures, Merkle root verification, and detector score breakdown ready for immediate submission with police FIRs.", bullet_style))
    story.append(Paragraph("<b>3. Public Verification Endpoint:</b> Any court registrar, police investigator, or bank fraud team can verify a certificate's integrity via "
                           "<code>GET /api/v1/blockchain/verify/{certificate_id}</code>.", bullet_style))

    story.append(Spacer(1, 4))
    story.append(make_callout(
        "All cryptographic blocks and voice signatures are processed 100% on-premise or within your private cloud. "
        "In accordance with the Digital Personal Data Protection Act (DPDP Act 2023), raw biometric voice data is never sent to third-party APIs.",
        bg="#eff6ff", border="#3b82f6", title="LEGAL COMPLIANCE & PRIVACY"
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("5. Family Safe-Voice Vault & 12 Indian Languages", h1_style))
    story.append(Paragraph(
        "<b>A. Safe-Voice Biometric Registry:</b> Users and VIPs can pre-enroll 10-second reference voice notes. "
        "When an incoming ransom or emergency call occurs, DigiRaksha extracts high-dimensional speaker embeddings "
        "(192-D ECAPA-TDNN or 52-D Discriminant MFCCs) and computes cosine similarity. If similarity is below 0.72, an impersonation alert fires.",
        body_style
    ))
    story.append(Paragraph(
        "<b>B. Pan-India Localization (12 Languages):</b> DigiRaksha's command center natively supports 12 Indian languages: "
        "English, Hindi (Hindi), Bengali (Bangla), Telugu (Telugu), Marathi (Marathi), Tamil (Tamil), Gujarati (Gujarati), "
        "Kannada (Kannada), Malayalam (Malayalam), Punjabi (Punjabi), Odia (Odia), and Assamese (Assamese).",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: System Requirements & Prerequisites
    # =========================================================================
    story.append(Paragraph("6. System Requirements & Prerequisites", h1_style))
    story.append(Paragraph(
        "DigiRaksha is designed to run efficiently on standard consumer and workstation hardware without requiring expensive enterprise GPUs:",
        body_style
    ))

    req_table = [
        [Paragraph("<b>Component</b>", body_style), Paragraph("<b>Minimum Specification</b>", body_style), Paragraph("<b>Recommended Specification</b>", body_style)],
        [
            Paragraph("Operating System", body_style),
            Paragraph("Windows 10 / 11 (64-bit), Ubuntu 20.04+, macOS 12+", body_style),
            Paragraph("Windows 11 (64-bit) or Ubuntu 22.04 LTS", body_style)
        ],
        [
            Paragraph("Python Runtime", body_style),
            Paragraph("<b>Python 3.12.x</b> (Mandatory)", body_style),
            Paragraph("Python 3.12.8 (64-bit with pip & virtualenv)", body_style)
        ],
        [
            Paragraph("Node.js Runtime", body_style),
            Paragraph("Node.js 20+ LTS, npm 10+", body_style),
            Paragraph("Node.js 22 LTS with npm 11+", body_style)
        ],
        [
            Paragraph("Processor (CPU)", body_style),
            Paragraph("Intel Core i5 (8th Gen+) or AMD Ryzen 5 (4 cores)", body_style),
            Paragraph("Intel Core i7/i9 or AMD Ryzen 7 (8+ cores, AVX2 enabled)", body_style)
        ],
        [
            Paragraph("System Memory (RAM)", body_style),
            Paragraph("8 GB DDR4", body_style),
            Paragraph("16 GB DDR4/DDR5 (enables faster ASR model caching)", body_style)
        ],
        [
            Paragraph("Storage", body_style),
            Paragraph("3 GB free SSD space", body_style),
            Paragraph("10 GB SSD space (for case reports & audio storage)", body_style)
        ],
        [
            Paragraph("Audio Subsystem", body_style),
            Paragraph("Standard microphone or virtual audio cable", body_style),
            Paragraph("Stereo input / loopback driver for telephony VoIP interception", body_style)
        ],
    ]
    t_rq = Table(req_table, colWidths=[40 * mm, 68 * mm, 70 * mm])
    t_rq.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, border_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_rq)
    story.append(Spacer(1, 8))

    story.append(make_callout(
        "CRITICAL: Do NOT install Python 3.13 or 3.14. High-performance C audio libraries (librosa, soundfile, OpenCV) "
        "do not have pre-built wheels for Python 3.13+. Always use Python 3.12 (specifically 3.12.8).",
        bg="#fef2f2", border="#ef4444", title="CRITICAL PYTHON VERSION REQUIREMENT"
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Pre-Installation Checklist", h2_style))
    story.append(Paragraph("Verify your installed tools in PowerShell or Terminal:", body_style))
    chk_code = (
        "# Check installed tools<br/>"
        "python --version         # MUST return Python 3.12.x<br/>"
        "node --version           # MUST return v20.x or higher<br/>"
        "npm --version            # MUST return 10.x or higher"
    )
    story.append(make_code_box(chk_code))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: Step-by-Step Installation Guide
    # =========================================================================
    story.append(Paragraph("7. Step-by-Step Installation Guide", h1_style))

    story.append(Paragraph("Option A: One-Click Standalone Desktop Run (No Install)", h2_style))
    story.append(Paragraph(
        "For immediate demonstration without configuring Python or Node.js environments, DigiRaksha includes a pre-packaged "
        "executable <code>DigiRaksha.exe</code> located at the root of the distribution bundle.",
        body_style
    ))
    story.append(Paragraph("1. Simply double-click <code>DigiRaksha.exe</code>.", bullet_style))
    story.append(Paragraph("2. The self-bootstrapping runtime unpacks necessary binaries and launches the FastAPI server on port 8000.", bullet_style))
    story.append(Paragraph("3. Your default web browser will automatically open to <code>http://127.0.0.1:8000</code> with the full Command Deck loaded.", bullet_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Option B: Automated Developer Setup (Windows PowerShell)", h2_style))
    story.append(Paragraph(
        "DigiRaksha bundles an automated provisioning script <code>setup_dev.ps1</code> that inspects prerequisites, initializes the virtual environment, "
        "installs PyTorch CPU, installs backend ML packages, and builds the frontend UI.",
        body_style
    ))
    setup_ps1_code = (
        "# Run from PowerShell in project root directory:<br/>"
        "powershell -ExecutionPolicy Bypass -File setup_dev.ps1"
    )
    story.append(make_code_box(setup_ps1_code))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Option C: Complete Manual Installation (Cross-Platform / Linux / Mac / Windows)", h2_style))
    story.append(Paragraph("If you prefer full control over your environment, execute the following steps in sequence:", body_style))

    story.append(Paragraph("<b>Step 1: Create and Activate Python 3.12 Virtual Environment</b>", body_style))
    step1_code = (
        "# Windows (PowerShell)<br/>"
        "py -3.12 -m venv .venv<br/>"
        ".\\.venv\\Scripts\\activate<br/><br/>"
        "# Linux / macOS (Bash / Zsh)<br/>"
        "python3.12 -m venv .venv<br/>"
        "source .venv/bin/activate"
    )
    story.append(make_code_box(step1_code))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Step 2: Install PyTorch CPU & Backend Dependencies</b>", body_style))
    step2_code = (
        "# 1. Install PyTorch CPU first to avoid heavy CUDA wheels (~2GB savings)<br/>"
        "pip install torch --index-url https://download.pytorch.org/whl/cpu<br/><br/>"
        "# 2. Install backend package and all ML dependencies in editable mode<br/>"
        "cd backend<br/>"
        "pip install -e \".[ml]\"<br/>"
        "cd .."
    )
    story.append(make_code_box(step2_code))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Step 3: Install Frontend Dependencies & Compile Production Assets</b>", body_style))
    step3_code = (
        "cd frontend<br/>"
        "npm install --include=dev<br/>"
        "npm run build<br/>"
        "cd .."
    )
    story.append(make_code_box(step3_code))
    story.append(Spacer(1, 4))
    story.append(make_callout(
        "The command 'npm run build' compiles the React 19 application directly into 'backend/app/static/'. "
        "Once built, the backend server will serve both the REST API and the frontend UI concurrently from a single port!",
        bg="#f0fdf4", border="#10b981", title="STANDALONE PRODUCTION READY"
    ))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: How to Run the Tool & Operational Walkthrough
    # =========================================================================
    story.append(Paragraph("8. How to Run & Operate DigiRaksha", h1_style))

    story.append(Paragraph("Method 1: One-Click Windows Batch Launcher (Recommended)", h2_style))
    story.append(Paragraph("Double-click <code>DigiRaksha.bat</code> from the project root directory, or run in terminal:", body_style))
    bat_code = (
        "# In Command Prompt or PowerShell:<br/>"
        "DigiRaksha.bat"
    )
    story.append(make_code_box(bat_code))
    story.append(Paragraph(
        "<i>DigiRaksha.bat automatically checks your virtual environment, executes the FastAPI server, "
        "and launches your default browser at http://127.0.0.1:8000.</i>",
        body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Method 2: Development Mode with Hot-Reload (Two Terminals)", h2_style))
    story.append(Paragraph("For active code development and instant frontend UI hot-reloading:", body_style))

    dev_code = (
        "# TERMINAL 1: Start FastAPI Backend<br/>"
        "cd backend<br/>"
        "..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload<br/><br/>"
        "# TERMINAL 2: Start Vite React Frontend (Hot-Reload)<br/>"
        "cd frontend<br/>"
        "npm run dev"
    )
    story.append(make_code_box(dev_code))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Service Ports & Access Endpoints", h2_style))
    endpoints_data = [
        [Paragraph("<b>Interface / Service</b>", body_style), Paragraph("<b>URL / Protocol</b>", body_style), Paragraph("<b>Function & Description</b>", body_style)],
        [
            Paragraph("<b>Web Command Deck</b>", body_style),
            Paragraph("http://localhost:5173<br/>or http://127.0.0.1:8000", body_style),
            Paragraph("Full cyber defense dashboard: Live Sentinel, Media Scanner, Safe-Voice Vault, Evidence Ledger.", body_style)
        ],
        [
            Paragraph("<b>Interactive API Docs</b>", body_style),
            Paragraph("http://127.0.0.1:8000/docs", body_style),
            Paragraph("FastAPI OpenAPI Swagger UI for testing REST and WebSocket endpoints interactively.", body_style)
        ],
        [
            Paragraph("<b>Real-Time Live Call WS</b>", body_style),
            Paragraph("<font size='7.5'><b>ws://127.0.0.1:8000/api/v1/stream/live-call</b></font>", body_style),
            Paragraph("Bidirectional sliding chunk stream for zero-lag PCM16/WebM telephonic voice analysis.", body_style)
        ],
        [
            Paragraph("<b>Blockchain Explorer</b>", body_style),
            Paragraph("<font size='7.5'>http://127.0.0.1:8000/api/v1/blockchain/ledger</font>", body_style),
            Paragraph("JSON endpoint returning full cryptographic Merkle audit trail and block chain of custody.", body_style)
        ],
        [
            Paragraph("<b>Health Probe</b>", body_style),
            Paragraph("<font size='7.5'>http://127.0.0.1:8000/api/v1/health</font>", body_style),
            Paragraph("System health check reporting status of on-device ML detectors and database connection.", body_style)
        ],
    ]
    t_ep = Table(endpoints_data, colWidths=[38 * mm, 62 * mm, 82 * mm])
    t_ep.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, border_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_ep)
    story.append(Spacer(1, 6))

    story.append(Paragraph("9. Feature-by-Feature Operational Walkthrough", h1_style))
    story.append(Paragraph("<b>1. Live Call Sentinel:</b> Navigate to 'Live Sentinel'. Choose an attack scenario (e.g. <i>Cloned CEO Wire Extortion</i> or <i>Fake Police Digital Arrest</i>) or click 'Start Live Microphone'. Observe the real-time CRT oscilloscope, the 24-band frequency spectrum bars, live transcription, and the animated radar gauge.", body_style))
    story.append(Paragraph("<b>2. Media Scanner:</b> Drag and drop suspicious audio/video recordings into the dropzone. The system extracts multi-modal cues (AASIST spoof probability, MesoNet face flicker, Whisper transcripts, and semantic red flags).", body_style))
    story.append(Paragraph("<b>3. Safe-Voice Vault:</b> Pre-enroll family members or corporate executives. Record or upload genuine voice samples. When verified against subsequent calls, the system outputs biometric similarity scores.", body_style))
    story.append(Paragraph("<b>4. Evidence Ledger & Court Certificate:</b> Every analyzed session creates a verifiable block. Click 'View Court Certificate' to inspect the SHA-256 Merkle proof, certificate ID, and export formal police FIR reports.", body_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: Testing, Troubleshooting & Statutory Helplines
    # =========================================================================
    story.append(Paragraph("10. Automated Testing & Verification Suite", h1_style))
    story.append(Paragraph(
        "DigiRaksha includes an automated test suite verifying vocoder DSP algorithms, Merkle tree blockchain integrity, "
        "and WebSocket streaming chunk analysis:",
        body_style
    ))
    test_code = (
        "# Run automated tests from backend directory:<br/>"
        "cd backend<br/>"
        "..\\.venv\\Scripts\\python.exe -m pytest tests/test_stream_and_blockchain.py -v<br/><br/>"
        "# Run full unit test suite:<br/>"
        "..\\.venv\\Scripts\\python.exe -m pytest -v"
    )
    story.append(make_code_box(test_code))
    story.append(Spacer(1, 6))

    story.append(Paragraph("11. Troubleshooting & Common Pitfalls", h1_style))
    troubleshoot_data = [
        [
            Paragraph("<b>Symptom / Error</b>", body_style),
            Paragraph("<b>Root Cause</b>", body_style),
            Paragraph("<b>Immediate Resolution</b>", body_style),
        ],
        [
            Paragraph("<b>Python 3.13 / 3.14 build error</b>", body_style),
            Paragraph("librosa, soundfile, or OpenCV C-wheels are not yet compiled for Python 3.13+", body_style),
            Paragraph("Install official <b>Python 3.12</b> from python.org. Recreate venv with: <code>py -3.12 -m venv .venv</code>.", body_style),
        ],
        [
            Paragraph("<b>Windows 'Filename too long' error</b>", body_style),
            Paragraph("Path length exceeds Windows default 260-character MAX_PATH limit", body_style),
            Paragraph("Move the project to a shorter folder path, e.g. <code>C:\\sih\\DigiRaksha</code>.", body_style),
        ],
        [
            Paragraph("<b>Port 8000 already in use</b>", body_style),
            Paragraph("A previous uvicorn server is still running in the background", body_style),
            Paragraph("Kill port 8000 via PowerShell:<br/><code>Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force</code>", body_style),
        ],
        [
            Paragraph("<b>Microphone Access Denied</b>", body_style),
            Paragraph("Browser permissions block audio input on non-HTTPS origins", body_style),
            Paragraph("Access via <code>http://localhost:5173</code> or <code>http://127.0.0.1:8000</code> (browsers trust localhost origins).", body_style),
        ],
        [
            Paragraph("<b>Frontend proxy 502 / Connection Refused</b>", body_style),
            Paragraph("Frontend is running but backend server on :8000 is not started", body_style),
            Paragraph("Start the backend server first in Terminal 1 before launching <code>npm run dev</code>.", body_style),
        ],
    ]
    t_trouble = Table(troubleshoot_data, colWidths=[42 * mm, 58 * mm, 78 * mm])
    t_trouble.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, border_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_trouble)
    story.append(Spacer(1, 8))

    story.append(Paragraph("12. Statutory Cyber Crime Helplines & Advisory Notice", h1_style))
    story.append(Paragraph(
        "DigiRaksha is built in strict alignment with guidelines published by the Ministry of Home Affairs (MHA), "
        "the Indian Cyber Crime Coordination Centre (I4C), and the Department of Telecommunications (DoT):",
        body_style
    ))
    story.append(Paragraph("• <b>National Cybercrime Reporting Helpline:</b> Dial <b>1930</b> (Toll-Free, 24x7 Pan-India).", bullet_style))
    story.append(Paragraph("• <b>National Cybercrime Portal:</b> Report incidents online at <b>https://cybercrime.gov.in</b>.", bullet_style))
    story.append(Paragraph("• <b>DoT Sanchar Saathi & Chakshu:</b> Report fraudulent numbers and WhatsApp calls at <b>https://sancharsaathi.gov.in</b>.", bullet_style))
    story.append(Paragraph("• <b>Golden Hour Rule:</b> Reporting financial cyber fraud within the first 2 to 3 hours maximizes the ability of the 1930 network to freeze scammer mule accounts before funds are withdrawn.", bullet_style))
    story.append(Spacer(1, 6))

    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "<div align='center'><b>DigiRaksha Platform • Smart India Hackathon (SIH) 2026 • AICTE Cyber Security Cell</b><br/>"
        "Developed by Team Terminal Breakers • Production Release 1.0</div>",
        ParagraphStyle("FooterNote", parent=body_style, alignment=1, textColor=text_muted)
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated documentation PDF: {OUT_PDF}")


if __name__ == "__main__":
    generate_pdf()
