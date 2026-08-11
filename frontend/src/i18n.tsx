/** Minimal EN/HI internationalisation with a React context. */
import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Lang = "en" | "hi";

type Entry = { en: string; hi: string };

const DICT: Record<string, Entry> = {
  "nav.analyze": { en: "Analyse", hi: "जाँच करें" },
  "nav.registry": { en: "Safe-Voice Registry", hi: "सेफ-वॉइस रजिस्ट्री" },
  "nav.history": { en: "History", hi: "इतिहास" },
  "nav.about": { en: "About", hi: "परिचय" },
  "brand.tagline": {
    en: "AI shield against Digital Arrest & deepfake scam calls",
    hi: "डिजिटल अरेस्ट और डीपफेक स्कैम कॉल के खिलाफ AI ढाल",
  },

  "tab.transcript": { en: "Paste transcript", hi: "ट्रांसक्रिप्ट चिपकाएँ" },
  "tab.upload": { en: "Upload recording / video", hi: "रिकॉर्डिंग / वीडियो अपलोड करें" },
  "label.text": { en: "Suspicious call transcript", hi: "संदिग्ध कॉल का ट्रांसक्रिप्ट" },
  "label.language": { en: "Language", hi: "भाषा" },
  "lang.auto": { en: "Auto-detect", hi: "स्वतः पहचानें" },
  "placeholder.text": {
    en: "Paste the text of the suspicious call here… e.g. “this is the CBI, you are under digital arrest, pay the verification fee”",
    hi: "संदिग्ध कॉल का पाठ यहाँ चिपकाएँ… जैसे “यह CBI है, आप डिजिटल अरेस्ट हैं, वेरिफिकेशन शुल्क जमा करें”",
  },
  "btn.analyze": { en: "Analyse", hi: "जाँच करें" },
  "btn.upload": { en: "Upload & analyse", hi: "अपलोड और जाँच करें" },
  "upload.drop": {
    en: "Drop an audio/video file here or click to browse",
    hi: "ऑडियो/वीडियो फ़ाइल यहाँ डालें या चुनने के लिए क्लिक करें",
  },
  "upload.supported": {
    en: "Supports .wav .mp3 .m4a .ogg .flac .mp4 .mov .webm (WhatsApp / Telegram voice notes)",
    hi: ".wav .mp3 .m4a .ogg .flac .mp4 .mov .webm (व्हाट्सऐप / टेलीग्राम वॉइस नोट)",
  },
  "status.analyzing": { en: "Analysing…", hi: "जाँच हो रही है…" },
  "status.uploading": { en: "Uploading…", hi: "अपलोड हो रहा है…" },
  "status.transcribing": { en: "Transcribing audio…", hi: "ऑडियो लिखा जा रहा है…" },
  "status.voice": { en: "Checking voice for AI/deepfake…", hi: "आवाज़ में AI/डीपफेक की जाँच…" },
  "status.video": { en: "Scanning video frames…", hi: "वीडियो फ़्रेम की जाँच…" },
  "status.text": { en: "Matching scam language patterns…", hi: "स्कैम भाषा पैटर्न मिलान…" },

  "result.title": { en: "Analysis result", hi: "जाँच परिणाम" },
  "result.score": { en: "Risk score", hi: "जोखिम स्कोर" },
  "result.level.low": { en: "Low risk", hi: "कम जोखिम" },
  "result.level.medium": { en: "Medium risk", hi: "मध्यम जोखिम" },
  "result.level.high": { en: "High risk", hi: "उच्च जोखिम" },
  "result.redflags": { en: "Why this was flagged", hi: "यह क्यों चिह्नित हुआ" },
  "result.redflags.none": { en: "No red flags raised.", hi: "कोई चेतावनी नहीं मिली।" },
  "result.nextsteps": { en: "What to do next", hi: "आगे क्या करें" },
  "result.signals": { en: "Detector details", hi: "डिटेक्टर विवरण" },
  "result.signals.avail": { en: "available", hi: "उपलब्ध" },
  "result.signals.unavail": { en: "not available", hi: "उपलब्ध नहीं" },
  "result.signals.error": { en: "error", hi: "त्रुटि" },
  "result.transcript": { en: "Transcript", hi: "ट्रांसक्रिप्ट" },
  "result.duration": { en: "Duration", hi: "अवधि" },
  "result.lang": { en: "Language", hi: "भाषा" },
  "result.unknown": { en: "—", hi: "—" },
  "result.report.helpline": { en: "Call 1930 (cyber helpline)", hi: "1930 पर कॉल करें (साइबर हेल्पलाइन)" },
  "result.report.portal": { en: "Report at cybercrime.gov.in", hi: "cybercrime.gov.in पर शिकायत करें" },
  "result.ai.title": { en: "AI analysis", hi: "AI विश्लेषण" },
  "result.ai.unavailable": {
    en: "AI analysis is off — add an OpenRouter API key to enable it.",
    hi: "AI विश्लेषण बंद है — सक्षम करने के लिए OpenRouter API कुंजी जोड़ें।",
  },
  "result.ai.verdict.scam": { en: "AI assesses this as a scam", hi: "AI इसे स्कैम मानता है" },
  "result.ai.verdict.benign": { en: "AI assesses this as not a scam", hi: "AI इसे स्कैम नहीं मानता" },
  "result.ai.confidence": { en: "Confidence", hi: "विश्वास" },
  "result.ai.category": { en: "Category", hi: "प्रकार" },
  "result.ai.indicators": { en: "Key indicators", hi: "मुख्य संकेत" },
  "result.ai.explanation": { en: "AI explanation", hi: "AI व्याख्या" },
  "result.ai.model": { en: "Model", hi: "मॉडल" },

  "registry.title": { en: "Family Safe-Voice Registry", hi: "परिवार सेफ-वॉइस रजिस्ट्री" },
  "registry.subtitle": {
    en: "Pre-enrol the voices of your family members so a “this is your relative in danger” call can be checked instantly.",
    hi: "परिवार के सदस्यों की आवाज़ें पहले से सुरक्षित रखें ताकि “यह आपका रिश्तेदार है” वाली कॉल की तुरंत जाँच हो सके।",
  },
  "registry.empty": { en: "No family members added yet.", hi: "अभी कोई परिवार सदस्य नहीं जोड़ा गया।" },
  "registry.add.title": { en: "Add family member", hi: "परिवार सदस्य जोड़ें" },
  "field.name": { en: "Name", hi: "नाम" },
  "field.relationship": { en: "Relationship", hi: "रिश्ता" },
  "field.phone": { en: "Phone (optional)", hi: "फ़ोन (वैकल्पिक)" },
  "btn.add": { en: "Add member", hi: "सदस्य जोड़ें" },
  "btn.delete": { en: "Remove", hi: "हटाएँ" },
  "btn.enroll": { en: "Enrol voice", hi: "आवाज़ दर्ज करें" },
  "btn.verify": { en: "Verify a call", hi: "कॉल जाँचें" },
  "enroll.done": { en: "Voice enrolled ✓", hi: "आवाज़ दर्ज हो गई ✓" },
  "enroll.count": { en: "voice sample(s)", hi: "आवाज़ नमूने" },
  "verify.title": { en: "Voice check", hi: "आवाज़ जाँच" },
  "verify.match": { en: "Matches", hi: "मेल खाती है" },
  "verify.no_match": { en: "Does NOT match", hi: "मेल नहीं खाती" },
  "verify.similarity": { en: "similarity", hi: "समानता" },
  "verify.threshold": { en: "threshold", hi: "सीमा" },
  "verify.no_enrollment": {
    en: "This member has no enrolled voice sample yet.",
    hi: "इस सदस्य की आवाज़ अभी दर्ज नहीं हुई है।",
  },
  "verify.probe": { en: "Voice note to verify", hi: "जाँचने के लिए वॉइस नोट" },

  "history.title": { en: "Recent analyses", hi: "हाल की जाँचें" },
  "history.empty": { en: "No analyses yet.", hi: "अभी कोई जाँच नहीं हुई।" },
  "history.col.time": { en: "Time", hi: "समय" },
  "history.col.type": { en: "Type", hi: "प्रकार" },
  "history.col.file": { en: "File", hi: "फ़ाइल" },
  "history.col.risk": { en: "Risk", hi: "जोखिम" },
  "history.row.detail": { en: "view detail", hi: "विवरण देखें" },
  "history.failed": { en: "failed", hi: "विफल" },
  "history.queued": { en: "queued", hi: "कतार में" },
  "history.running": { en: "running", hi: "चालू" },
  "history.completed": { en: "completed", hi: "पूर्ण" },

  "about.title": { en: "About DigiRaksha", hi: "डिजीरक्षा परिचय" },
  "about.problem.title": { en: "The problem", hi: "समस्या" },
  "about.problem.body": {
    en: "Scammers now use AI-cloned voices and real-time deepfake video to impersonate police, judges and family members. The “digital arrest” scam has made lakhs of Indians pay fake penalties while believing they were under investigation. Victims cannot tell the synthetic voice from the real one in the heat of the moment.",
    hi: "स्कैमर्स अब AI से नकली आवाज़ और रीयल-टाइम डीपफेक वीडियो का इस्तेमाल कर पुलिस, जज और परिवार के सदस्यों की नकल करते हैं। “डिजिटल अरेस्ट” स्कैम से लाखों भारतीय जाँच के दौरान फर्जी जुर्माना चुका चुके हैं। मौके पर पीड़ित असली और नकली आवाज़ में फर्क नहीं कर पाते।",
  },
  "about.how.title": { en: "How it works", hi: "यह कैसे काम करता है" },
  "about.how.body": {
    en: "Upload the suspicious call or paste its transcript. DigiRaksha transcribes it, analyses the voice for AI-synthesis artifacts (AASIST anti-spoofing model), scans video frames for deepfake tampering, and matches the language against known scam scripts — in English, Hindi and Hinglish. Every result is explainable, with red flags and next steps in your language.",
    hi: "संदिग्ध कॉल अपलोड करें या उसका ट्रांसक्रिप्ट चिपकाएँ। डिजीरक्षा उसे लिखता है, आवाज़ में AI-निर्मित ध्वनि के संकेत (AASIST मॉडल) खोजता है, वीडियो फ़्रेम में डीपफेक की जाँच करता है, और भाषा का मिलान जाने-पहचाने स्कैम पैटर्न से करता है — अंग्रेज़ी, हिंदी और हिंग्लिश में। हर परिणाम की वजह और अगले कदम आपकी भाषा में बताए जाते हैं।",
  },
  "about.registry.title": { en: "Safe-Voice Registry", hi: "सेफ-वॉइस रजिस्ट्री" },
  "about.registry.body": {
    en: "The proactive layer. Enrol the real voices of your family once. When a call claims to be your relative in trouble, check it against the registry in seconds instead of panicking.",
    hi: "यह सुरक्षा की पहली परत है। अपने परिवार की असली आवाज़ें एक बार दर्ज करें। जब कोई कॉल खुद को आपका रिश्तेदार बताए, तो घबराने की बजाय कुछ सेकंड में रजिस्ट्री से जाँचें।",
  },
  "about.report.title": { en: "Report a scam", hi: "स्कैम की शिकायत करें" },
  "about.report.body": {
    en: "National Cyber Crime Reporting Portal: 1930 helpline or cybercrime.gov.in — immediately after a suspected scam call. Keep the number, don’t pay anything, and don’t share OTPs.",
    hi: "राष्ट्रीय साइबर अपराध पोर्टल: 1930 हेल्पलाइन या cybercrime.gov.in — संदिग्ध कॉल के तुरंत बाद। नंबर सहेजें, कोई भुगतान न करें, और OTP कभी साझा न करें।",
  },
  "about.disclaimer": {
    en: "DigiRaksha is an awareness & triage tool, not a replacement for law-enforcement reporting.",
    hi: "डिजीरक्षा जागरूकता और जाँच का उपकरण है, कानून-व्यवस्था की शिकायत का विकल्प नहीं।",
  },
  "footer.disclaimer": {
    en: "Educational & awareness tool. Detector analysis stays on your server; the optional AI review is off by default.",
    hi: "शैक्षिक जागरूकता उपकरण। डिटेक्टर विश्लेषण आपके सर्वर पर रहता है; वैकल्पिक AI समीक्षा डिफ़ॉल्ट रूप से बंद है।",
  },
  "err.network": { en: "Network error — is the backend running?", hi: "नेटवर्क त्रुटि — क्या बैकएंड चालू है?" },
  "err.try": { en: "Try again", hi: "फिर से कोशिश करें" },

  // ---- police suite navigation / shell ----------------------------------
  "nav.dashboard": { en: "Dashboard", hi: "डैशबोर्ड" },
  "nav.cases": { en: "Cases", hi: "मामले" },
  "nav.evidence": { en: "Evidence Vault", hi: "साक्ष्य तिजोरी" },
  "nav.voice-match": { en: "Voice Match", hi: "आवाज़ मिलान" },
  "nav.phone": { en: "Phone Intelligence", hi: "फ़ोन खुफिया" },
  "nav.settings": { en: "Settings", hi: "सेटिंग्स" },
  "auth.setup.title": { en: "Set up DigiRaksha", hi: "डिजीरक्षा सेट करें" },
  "auth.setup.sub": {
    en: "This station PC runs the case tools. Set an officer name and a 4+ digit PIN to lock the app.",
    hi: "यह स्टेशन PC केस टूल चलाता है। ऐप लॉक करने के लिए अधिकारी का नाम और 4+ अंकों का PIN सेट करें।",
  },
  "auth.login.title": { en: "Locked", hi: "लॉक है" },
  "auth.login.sub": { en: "Enter your PIN to unlock DigiRaksha.", hi: "डिजीरक्षा खोलने के लिए PIN डालें।" },
  "field.officer": { en: "Officer name", hi: "अधिकारी का नाम" },
  "field.pin": { en: "PIN", hi: "PIN" },
  "field.newpin": { en: "New PIN", hi: "नया PIN" },
  "field.currentpin": { en: "Current PIN", hi: "वर्तमान PIN" },
  "btn.setup": { en: "Set PIN & continue", hi: "PIN सेट करें और आगे बढ़ें" },
  "btn.unlock": { en: "Unlock", hi: "खोलें" },
  "btn.lock": { en: "Lock", hi: "लॉक" },
  "topbar.officer": { en: "Officer", hi: "अधिकारी" },

  // ---- dashboard ---------------------------------------------------------
  "dash.title": { en: "Command Dashboard", hi: "कमांड डैशबोर्ड" },
  "dash.sub": { en: "Live picture of cases, evidence and scam activity on this station.", hi: "इस स्टेशन पर मामलों, साक्ष्यों और स्कैम गतिविधि की लाइव तस्वीर।" },
  "dash.stat.cases": { en: "Open cases", hi: "खुले मामले" },
  "dash.stat.evidence": { en: "Evidence items", hi: "साक्ष्य आइटम" },
  "dash.stat.scans": { en: "Analyses run", hi: "जाँचें चलीं" },
  "dash.stat.numbers": { en: "Numbers flagged", hi: "चिह्नित नंबर" },
  "dash.stat.high7": { en: "High-risk (7d)", hi: "उच्च जोखिम (7d)" },
  "dash.chart.categories": { en: "Scam categories detected", hi: "पहचाने गए स्कैम प्रकार" },
  "dash.chart.risk": { en: "Risk distribution", hi: "जोखिम वितरण" },
  "dash.chart.trend": { en: "Analyses — last 14 days", hi: "जाँचें — पिछले 14 दिन" },
  "dash.chart.status": { en: "Cases by status", hi: "मामले स्थिति अनुसार" },
  "dash.recent": { en: "Recent high-risk analyses", hi: "हाल की उच्च जोखिम जाँचें" },
  "dash.empty": { en: "No analyses yet. Run one from Analyse.", hi: "अभी कोई जाँच नहीं। जाँच पृष्ठ से चलाएँ।" },

  // ---- cases -------------------------------------------------------------
  "cases.title": { en: "Cases", hi: "मामले" },
  "cases.sub": { en: "Open, investigate and close scam cases with a full audit trail.", hi: "पूरे ऑडिट ट्रेल के साथ स्कैम मामले खोलें, जाँचें और बंद करें।" },
  "cases.new": { en: "New case", hi: "नया मामला" },
  "cases.search": { en: "Search case number, name, phone…", hi: "मामला नंबर, नाम, फ़ोन खोजें…" },
  "cases.empty": { en: "No cases found.", hi: "कोई मामला नहीं मिला।" },
  "case.detail": { en: "Case detail", hi: "मामला विवरण" },
  "case.persons": { en: "Persons of interest", hi: "संबंधित व्यक्ति" },
  "case.evidence": { en: "Evidence", hi: "साक्ष्य" },
  "case.timeline": { en: "Audit timeline", hi: "ऑडिट समयरेखा" },
  "case.notes": { en: "Case notes", hi: "मामला नोट्स" },
  "case.addnote": { en: "Add note", hi: "नोट जोड़ें" },
  "case.addperson": { en: "Add person", hi: "व्यक्ति जोड़ें" },
  "case.uploadevidence": { en: "Add evidence", hi: "साक्ष्य जोड़ें" },
  "case.pdf": { en: "Export PDF", hi: "PDF निर्यात" },
  "case.status.open": { en: "Open", hi: "खुला" },
  "case.status.investigating": { en: "Investigating", hi: "जाँच में" },
  "case.status.closed": { en: "Closed", hi: "बंद" },
  "case.priority.low": { en: "Low", hi: "कम" },
  "case.priority.normal": { en: "Normal", hi: "सामान्य" },
  "case.priority.high": { en: "High", hi: "उच्च" },
  "case.priority.critical": { en: "Critical", hi: "गंभीर" },
  "case.victim": { en: "Victim", hi: "पीड़ित" },
  "case.suspect": { en: "Suspect", hi: "संदिग्ध" },
  "case.officer": { en: "Officer", hi: "अधिकारी" },
  "case.setopen": { en: "Reopen", hi: "फिर खोलें" },
  "case.setinvestigating": { en: "Start investigating", hi: "जाँच शुरू करें" },
  "case.setclosed": { en: "Close case", hi: "मामला बंद करें" },

  // ---- evidence ----------------------------------------------------------
  "evidence.title": { en: "Evidence Vault", hi: "साक्ष्य तिजोरी" },
  "evidence.sub": { en: "Every item is SHA-256 fingerprinted. Verify integrity anytime.", hi: "हर आइटम SHA-256 से फिंगरप्रिंटेड है। कभी भी अखंडता जाँचें।" },
  "evidence.upload": { en: "Ingest evidence", hi: "साक्ष्य दर्ज करें" },
  "evidence.search": { en: "Search filename, hash, note…", hi: "फ़ाइलनाम, हैश, नोट खोजें…" },
  "evidence.filter.type": { en: "Type", hi: "प्रकार" },
  "evidence.filter.risk": { en: "Risk", hi: "जोखिम" },
  "evidence.empty": { en: "No evidence items.", hi: "कोई साक्ष्य नहीं।" },
  "evidence.verify": { en: "Verify hash", hi: "हैश जाँचें" },
  "evidence.verified": { en: "Integrity verified ✓", hi: "अखंडता सत्यापित ✓" },
  "evidence.mismatch": { en: "Hash MISMATCH!", hi: "हैश मेल नहीं खाता!" },
  "evidence.linkcase": { en: "Link to case", hi: "मामले से जोड़ें" },
  "evidence.download": { en: "Download", hi: "डाउनलोड" },
  "evidence.sha": { en: "SHA-256", hi: "SHA-256" },
  "evidence.size": { en: "Size", hi: "आकार" },
  "evidence.date": { en: "Uploaded", hi: "अपलोड हुआ" },
  "evidence.tamper.note": {
    en: "Caution: tampering with evidence files must be logged and documented.",
    hi: "सावधानी: साक्ष्य फ़ाइलों में छेड़छाड़ को लॉग और दस्तावेज़ित किया जाना चाहिए।",
  },

  // ---- voice match -------------------------------------------------------
  "vm.title": { en: "Voice Match", hi: "आवाज़ मिलान" },
  "vm.sub": { en: "Upload an unknown clip — the same caller across cases is matched against every enrolled voice.", hi: "अज्ञात क्लिप अपलोड करें — हर दर्ज आवाज़ से मिलान होगा कि यह वही कॉलर है या नहीं।" },
  "vm.upload": { en: "Unknown clip to identify", hi: "पहचानने के लिए अज्ञात क्लिप" },
  "vm.matches": { en: "Matches", hi: "मेल" },
  "vm.none": { en: "No voices on record to compare against. Enrol a suspect voice or family member first.", hi: "तुलना के लिए कोई आवाज़ दर्ज नहीं। पहले संदिग्ध या परिवार सदस्य की आवाज़ दर्ज करें।" },
  "vm.match": { en: "MATCH", hi: "मेल" },
  "vm.no_match": { en: "no match", hi: "मेल नहीं" },
  "vm.similarity": { en: "similarity", hi: "समानता" },
  "vm.threshold": { en: "threshold", hi: "सीमा" },

  // ---- phone -------------------------------------------------------------
  "phone.title": { en: "Phone Intelligence", hi: "फ़ोन खुफिया" },
  "phone.sub": { en: "Report suspicious numbers and surface links to cases.", hi: "संदिग्ध नंबर दर्ज करें और मामलों से जुड़ाव देखें।" },
  "phone.lookup": { en: "Look up a number", hi: "नंबर जाँचें" },
  "phone.lookup.ph": { en: "Enter phone number…", hi: "फ़ोन नंबर डालें…" },
  "phone.report": { en: "Report a number", hi: "नंबर दर्ज करें" },
  "phone.report.ph": { en: "Suspicious number", hi: "संदिग्ध नंबर" },
  "phone.notes": { en: "Notes", hi: "नोट्स" },
  "phone.status.reported": { en: "Reported", hi: "दर्ज" },
  "phone.status.verified_fraud": { en: "Verified fraud", hi: "सत्यापित धोखा" },
  "phone.status.cleared": { en: "Cleared", hi: "साफ़" },
  "phone.reported.list": { en: "Reported numbers", hi: "दर्ज नंबर" },
  "phone.empty": { en: "No numbers reported yet.", hi: "अभी कोई नंबर दर्ज नहीं।" },
  "phone.linked.cases": { en: "Linked cases", hi: "जुड़े मामले" },
  "phone.notfound": { en: "No reports on record for this number.", hi: "इस नंबर के लिए कोई रिपोर्ट नहीं।" },
  "phone.found": { en: "On record", hi: "रिकॉर्ड में" },

  // ---- settings ----------------------------------------------------------
  "settings.title": { en: "Settings", hi: "सेटिंग्स" },
  "settings.pin.title": { en: "Change PIN", hi: "PIN बदलें" },
  "settings.detectors": { en: "Detector status", hi: "डिटेक्टर स्थिति" },
  "settings.about": { en: "About", hi: "परिचय" },
  "settings.changepin": { en: "Update PIN", hi: "PIN अपडेट करें" },
  "btn.save": { en: "Save", hi: "सहेजें" },
  "btn.cancel": { en: "Cancel", hi: "रद्द करें" },
  "btn.close": { en: "Close", hi: "बंद करें" },
  "btn.back": { en: "Back", hi: "वापस" },
  "ok": { en: "OK", hi: "ठीक है" },
  "done": { en: "Done ✓", hi: "हो गया ✓" },

  // ---- generic status ----------------------------------------------------
  "status.loading": { en: "Loading…", hi: "लोड हो रहा है…" },
  "status.saving": { en: "Saving…", hi: "सहेजा जा रहा है…" },
  "status.matching": { en: "Matching voice…", hi: "आवाज़ मिलान हो रहा है…" },
  "role.victim": { en: "Victim", hi: "पीड़ित" },
  "role.suspect": { en: "Suspect", hi: "संदिग्ध" },
  "role.witness": { en: "Witness", hi: "गवाह" },
  "role.informant": { en: "Informant", hi: "सूचना दाता" },
  "role.unknown": { en: "Unknown", hi: "अज्ञात" },
};

interface I18n {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18n>({ lang: "en", setLang: () => {}, t: (k) => DICT[k]?.en ?? k });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => {
    const saved = localStorage.getItem("digiraksha.lang");
    return saved === "hi" ? "hi" : "en";
  });

  const value = useMemo<I18n>(
    () => ({
      lang,
      setLang: (l) => {
        setLang(l);
        localStorage.setItem("digiraksha.lang", l);
      },
      t: (key: string) => DICT[key]?.[lang] ?? key,
    }),
    [lang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

/** Pick the localised string for a LocalizedText-like object. */
export function pick<T extends { en: string; hi?: string }>(obj: T, lang: Lang): string {
  if (!obj) return "";
  if (lang === "hi" && obj.hi) return obj.hi;
  return obj.en;
}
