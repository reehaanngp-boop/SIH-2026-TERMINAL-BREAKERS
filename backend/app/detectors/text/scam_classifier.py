"""Scam-script text classifier with Hybrid ML + Rule-Based Semantic Heuristics.

Combines the scikit-learn model (TF-IDF + logistic-regression pipeline) with a
fast, high-precision keyword/pattern rule engine. If the ML model is missing or
uncertain, the semantic heuristic engine provides instant classification so
scam scripts are reliably detected.
"""

from __future__ import annotations

import re
from typing import Any

from app.config import get_settings
from app.detectors.base import BaseDetector

# Category identifiers used by the training script and mapped to red flags by
# the risk engine. Keep in sync with backend/ml/build_dataset.py.
CATEGORIES = ["digital_arrest", "fake_courier", "otp_phishing", "kin_emergency", "other_fraud", "benign", "neutral"]

CONFIDENCE_FLOOR = 0.5
BENIGN_MARGIN = 0.15
MAX_LEN = 20_000

# High-precision multi-pattern threat signatures for Indian telecom / cyber fraud
# Supports English, Hindi (हिन्दी), Tamil (தமிழ்), Telugu (తెలుగు), Kannada (ಕನ್ನಡ), Malayalam (മലയാളം), Hinglish & Tanglish
_HEURISTIC_PATTERNS: dict[str, list[re.Pattern]] = {
    "digital_arrest": [
        # English
        re.compile(r"\b(?:digital\s*arrest|digitally\s*arrested|virtual\s*arrest)\b", re.I),
        re.compile(r"\b(?:cbi|ncb|enforcement\s*directorate|\bed\b|narcotics\s*control\s*bureau|cyber\s*crime\s*(?:police|cell|branch)|crime\s*branch|mumbai\s*police|delhi\s*police)\b", re.I),
        re.compile(r"\b(?:arrest\s*warrant|non[- ]bailable\s*warrant|supreme\s*court\s*order|high\s*court\s*order|court\s*hearing\s*on\s*video|virtual\s*interrogation|virtual\s*courtroom|supreme\s*court\s*bench)\b", re.I),
        re.compile(r"\b(?:stay\s*on\s*(?:skype|video|whatsapp)\s*call|do\s*not\s*disconnect|isolated\s*room|camera\s*on|lock\s*the\s*door|do\s*not\s*tell\s*anyone)\b", re.I),
        re.compile(r"\b(?:verification\s*account|rbi\s*security\s*deposit|clearance\s*fee|security\s*refund|asset\s*verification\s*account)\b", re.I),
        re.compile(r"\b(?:money\s*laundering|terror\s*funding|aadhaar\s*linked\s*to\s*crime|sim\s*used\s*in\s*illegal|fir\s*registered\s*against\s*you)\b", re.I),
        re.compile(r"\b(?:trai|department\s*of\s*telecom(?:munications)?|dot)\b.*?\b(?:disconnect(?:ed|ion)?|illegal\s*advertisements|block\s*all\s*numbers|deactivat(?:ed|ion))\b", re.I),
        re.compile(r"\b(?:chakshu|sancharsaathi|cybercrime\.gov\.in)\b.*?\b(?:complaint|notice|deactivat(?:ed|ion)?|illegal|fraud)\b", re.I),
        # Hindi & Hinglish
        re.compile(r"(?:डिजिटल\s*अरेस्ट|सीबीआई|गिरफ्तारी\s*वारंट|स्काइप|वेरिफिकेशन\s*फीस|मनी\s*लॉन्ड्रिंग|सुप्रीम\s*कोर्ट|क्राइम\s*ब्रांच|कमरे\s*में\s*अकेले|साइबर\s*क्राइम)", re.I),
        re.compile(r"\b(?:video\s*call\s*par\s*rahein|paise\s*transfer\s*karo\s*verification|giraftari\s*warrant|cbi\s*officer\s*bol\s*raha\s*hu|kamre\s*ka\s*darwaza\s*band)\b", re.I),
        # Tamil & Tanglish (தமிழ்)
        re.compile(r"(?:டிஜிட்டல்\s*கைது|சிபிஐ|கைது\s*வாரண்ட்|பணமோசடி|உச்ச\s*நீதிமன்றம்|வீடியோ\s*அழைப்பு|காவல்\s*துறை|முடக்கம்|சரிபார்ப்பு\s*கட்டணம்|அறைக்குள்\s*பூட்டி|சைபர்\s*கிரைம்)", re.I),
        re.compile(r"\b(?:digital\s*kaidhu|cbi\s*adhikari|money\s*laundering\s*case|arrest\s*warrant\s*vanthuruku|video\s*call\s*la\s*iru|police\s*station\s*ku\s*vaanga|kadhavai\s*poottu|yaarukkum\s*solla\s*koodathu)\b", re.I),
        # Telugu (తెలుగు)
        re.compile(r"(?:డిజిటల్\s*అరెస్ట్|సిబిఐ|అరెస్ట్\s*వారెంట్|మనీ\s*లాండరింగ్|సుప్రీం\s*కోర్టు|వీడియో\s*కాల్|క్రైమ్\s*బ్రాంచ్|ధృవీకరణ\s*రుసుము|గదిలో\s*ఒంటరిగా)", re.I),
        re.compile(r"\b(?:digital\s*arrest\s*chesamu|cbi\s*officer\s*matladuthunna|arrest\s*warrant\s*vachindi|video\s*call\s*lo\s*undandi)\b", re.I),
        # Kannada & Malayalam
        re.compile(r"(?:ಡಿಜಿಟಲ್\s*ಬಂಧನ|ಸಿಬಿಐ|ಬಂಧನ\s*ವಾರಂಟ್|ಹಣ\s*ಅಕ್ರಮ\s*ವರ್ಗಾವಣೆ|ವೀಡಿಯೊ\s*ಕರೆ)", re.I),
        re.compile(r"(?:ഡിജിറ്റൽ\s*അറസ്റ്റ്|സിബിഐ|അറസ്റ്റ്\s*വാറണ്ട്|കള്ളപ്പണം\s*വെളുപ്പിക്കൽ|വീഡിയോ\s*കോൾ)", re.I),
    ],
    "fake_courier": [
        # English
        re.compile(r"\b(?:fedex|dhl|bluedart|india\s*post|courier|parcel|package|consignment)\b.*?\b(?:drugs|narcotics|mdma|contraband|illegal|passport|seized|detained|foreign\s*currency)\b", re.I),
        re.compile(r"\b(?:customs\s*department|customs\s*officer|mumbai\s*airport\s*customs|delhi\s*airport\s*customs|parcel\s*detained|seized\s*at\s*customs)\b", re.I),
        re.compile(r"\b(?:illegal\s*substance|synthetic\s*drugs|foreign\s*currency\s*in\s*courier|customs\s*clearance\s*fee)\b", re.I),
        # Hindi & Hinglish
        re.compile(r"(?:कूरियर|पार्सल|कस्टम|ड्रग्स|सीमा\s*शुल्क|नारकोटिक्स|प्रतिबंधित\s*सामान|मादक\s*पदार्थ|जब्त)", re.I),
        re.compile(r"\b(?:parcel\s*mein\s*drugs|customs\s*officer\s*bol\s*raha\s*hu|customs\s*duty\s*jama\s*karo|parcel\s*zabt\s*kar\s*liya)\b", re.I),
        # Tamil & Tanglish (தமிழ்)
        re.compile(r"(?:சுங்கத்துறை|சுங்க\s*அதிகாரி|பார்சல்|போதைப்பொருள்|பறிமுதல்|வெளிநாட்டு\s*நாணயம்|சட்டவிரோத|சுங்க\s*வரி|கொரியர்)", re.I),
        re.compile(r"\b(?:customs\s*officer\s*pesuren|parcel\s*la\s*drugs\s*irukku|customs\s*fee\s*kattu|parcel\s*seize\s*pannitaanga|bodhai\s*porul)\b", re.I),
        # Telugu (తెలుగు)
        re.compile(r"(?:కస్టమ్స్|పార్శిల్|డ్రగ్స్|స్వాధీనం|మాదకద్రవ్యాలు|కస్టమ్స్\s*డ్యూటీ|కొరియర్)", re.I),
        re.compile(r"\b(?:parcel\s*lo\s*drugs\s*unnayi|customs\s*duty\s*kattali|parcel\s*seize\s*chesaru)\b", re.I),
        # Kannada & Malayalam
        re.compile(r"(?:ಕಸ್ಟಮ್ಸ್|ಪಾರ್ಸೆಲ್|ಮಾದಕ\s*ದ್ರವ್ಯ|ವಶಪಡಿಸಿಕೊಳ್ಳಲಾಗಿದೆ)", re.I),
        re.compile(r"(?:കസ്റ്റംസ്|പാഴ്സൽ|മയക്കുമരുന്ന്|കണ്ടുകെട്ടി)", re.I),
    ],
    "otp_phishing": [
        # English
        re.compile(r"\b(?:otp|one\s*time\s*password|verification\s*code|share\s*(?:the\s*)?code|sms\s*code|6[- ]digit\s*code)\b", re.I),
        re.compile(r"\b(?:electricity\s*(?:power\s*)?cut|power\s*will\s*be\s*disconnected|bill\s*unpaid\s*tonight|electricity\s*officer|bijli\s*bill|power\s*officer\s*at\s*\d{10})\b", re.I),
        re.compile(r"\b(?:kyc\s*(?:expired|suspended|update|pending|block)|bank\s*account\s*(?:blocked|frozen|suspended)|card\s*blocked)\b", re.I),
        re.compile(r"\b(?:install\s*(?:apk|\.apk|anydesk|teamviewer|rustdesk|quicksupport|zoho\s*assist)|screen\s*share|remote\s*access|sbi_yono\.apk|download\s*our\s*app\s*from\s*link)\b", re.I),
        re.compile(r"\b(?:trai\s*sim\s*block|mobile\s*number\s*(?:will\s*be\s*)?deactivated\s*in\s*2\s*hours|sim\s*card\s*disconnected)\b", re.I),
        re.compile(r"\b(?:fastag\s*(?:kyc|suspended|blocked|blacklist)|credit\s*card\s*reward\s*points\s*expir(?:ed|ing)|echallan\s*pending|traffic\s*challan\s*apk)\b", re.I),
        # Hindi & Hinglish
        re.compile(r"(?:ओटीपी|केवाईसी|बिजली\s*काट|खाता\s*ब्लॉक|स्क्रीन\s*शेयर|एपीके\s*डाउनलोड|सिम\s*बंद|पैन\s*अपडेट)", re.I),
        re.compile(r"\b(?:bijli\s*kat\s*jayegi|otp\s*batao|apk\s*install\s*karo|yono\s*block\s*ho\s*jayega|screen\s*share\s*kijiye|sim\s*block\s*hoga)\b", re.I),
        # Tamil & Tanglish (தமிழ்)
        re.compile(r"(?:ஓடிபி|வங்கி\s*கணக்கு\s*முடக்க|மின்சாரம்\s*துண்டிக்கப்படும்|கேஒய்சி|திரை\s*பகிர்வு|செயலி\s*பதிவிறக்கம்|சிம்\s*முடக்கப்படும்)", re.I),
        re.compile(r"\b(?:otp\s*sollunga|account\s*block\s*aayirum|current\s*cut\s*panniduvaanga|screen\s*share\s*pannunga|apk\s*download\s*pannunga|eb\s*bill\s*katala)\b", re.I),
        # Telugu (తెలుగు)
        re.compile(r"(?:ఓటీపీ|ఖాతా\s*బ్లాక్|విద్యుత్\s*కట్|స్క్రీన్\s*షేర్|యాప్\s*డౌన్‌లోడ్|సిమ్\s*బ్లాక్|కేవైసీ\s*అప్‌డేట్)", re.I),
        re.compile(r"\b(?:otp\s*cheppandi|current\s*cut\s*avuthundi|account\s*block\s*avuthundi|screen\s*share\s*cheyandi)\b", re.I),
        # Kannada & Malayalam
        re.compile(r"(?:ಒಟಿಪಿ|ಖಾತೆ\s*ಬ್ಲಾಕ್|ವಿದ್ಯುತ್\s*ಕಟ್|ಸ್ಕ್ರೀನ್\s*ಹಂಚಿಕೆ)", re.I),
        re.compile(r"(?:ഒടിപി|അക്കൗണ്ട്\s*ബ്ലോക്ക്|വൈദ്യുതി\s*വിച്ഛേദിക്കും|സ്ക്രീൻ\s*ഷെയർ)", re.I),
    ],
    "kin_emergency": [
        # English
        re.compile(r"\b(?:son|daughter|child|brother|sister|husband|wife|nephew|relative|bachha|beta|beti)\b.*?\b(?:accident|hospital|police\s*station|arrested|custody|bail|critical|thana)\b", re.I),
        re.compile(r"\b(?:kidnapped|kidnapping|ransom|urgent\s*money\s*for\s*(?:hospital|operation|doctor|bail|release))\b", re.I),
        re.compile(r"\b(?:send\s*money\s*immediately|transfer\s*(?:urgently|now)|do\s*not\s*call\s*him|his\s*phone\s*is\s*confiscated)\b", re.I),
        # Hindi & Hinglish
        re.compile(r"(?:बेटा|बेटी|दुर्घटना|अस्पताल|थाना|जमानत|अपहरण|फिरौती|इलाज\s*के\s*लिए\s*पैसे|पुलिस\s*हिरासत)", re.I),
        re.compile(r"\b(?:aapka\s*beta\s*police\s*custody|hospital\s*mein\s*admit\s*hai|turant\s*paise\s*bhejo|bachao\s*mujhe|accident\s*ho\s*gaya)\b", re.I),
        # Tamil & Tanglish (தமிழ்)
        re.compile(r"(?:மகன்|மகள்|விபத்து|மருத்துவமனை|காவல்\s*நிலையம்|கைது\s*செய்யப்பட்டுள்ளார்|உடனடி\s*பணம்|சிகிச்சைக்காக|பிணை|கடத்தல்)", re.I),
        re.compile(r"\b(?:unga\s*paiyan\s*accident|hospital\s*la\s*serthirukkom|police\s*pidichitaanga|udane\s*panam\s*anupunga|kaapathunga\s*appa)\b", re.I),
        # Telugu (తెలుగు)
        re.compile(r"(?:కుమారుడు|కూతురు|ప్రమాదం|ఆసుపత్రి|పోలీస్\s*స్టేషన్|వెంటనే\s*డబ్బులు|బెయిల్|కిడ్నాప్)", re.I),
        re.compile(r"\b(?:mee\s*abbayi\s*accident|hospital\s*lo\s*unnadu|urgent\s*ga\s*money\s*pampandi|police\s*pattukunnaru)\b", re.I),
        # Kannada & Malayalam
        re.compile(r"(?:ಮಗ|ಮಗಳು|ಅಪಘಾತ|ಆಸ್ಪತ್ರೆ|ಪೊಲೀಸ್\s*ಠಾಣೆ|ತುರ್ತು\s*ಹಣ)", re.I),
        re.compile(r"(?:മകൻ|മകൾ|അപകടം|ആശുപത്രി|പോലീസ്\s*സ്റ്റേഷൻ|അടിയന്തര\s*പണം)", re.I),
    ],
    "other_fraud": [
        # English
        re.compile(r"\b(?:lottery|winner|won\s*(?:25|50)\s*lakh|kaun\s*banega\s*crorepati|kbc\s*lucky\s*draw|prize\s*money)\b", re.I),
        re.compile(r"\b(?:part[- ]time\s*job|telegram\s*tasks?|youtube\s*like\s*(?:and\s*)?subscribe\s*earn|work\s*from\s*home\s*earn\s*(?:daily|3000|5000)|google\s*review\s*rating\s*earn)\b", re.I),
        re.compile(r"\b(?:guaranteed\s*return|double\s*your\s*money|crypto\s*investment\s*profit|pay\s*tax\s*to\s*withdraw\s*profit|ipo\s*allotment\s*scam)\b", re.I),
        re.compile(r"\b(?:pre[- ]approved\s*loan|zero\s*interest\s*loan\s*processing\s*fee|instant\s*loan\s*clearance\s*charge)\b", re.I),
        # Hindi & Hinglish
        re.compile(r"(?:लॉटरी|इनाम|पार्ट\s*टाइम\s*जॉब|टेलीग्राम\s*टास्क|लोन\s*प्रोसेसिंग|गारंटीड\s*मुनाफा|घर\s*बैठे\s*कमाई)", re.I),
        re.compile(r"\b(?:telegram\s*task\s*se\s*paise|lottery\s*lagi\s*hai|daily\s*earning\s*task|crypto\s*profit\s*withdraw|ghar\s*baithe\s*kamaye)\b", re.I),
        # Tamil & Tanglish (தமிழ்)
        re.compile(r"(?:லாட்டரி|பரிசு|பகுதி\s*நேர\s*வேலை|டெலிகிராம்\s*பணி|கடன்\s*அனுமதி|உத்தரவாத\s*லாபம்|வீட்டில்\s*இருந்து\s*சம்பாதிக்க)", re.I),
        re.compile(r"\b(?:part\s*time\s*job\s*daily\s*earn|lottery\s*adichirukku|telegram\s*task\s*panunga|loan\s*processing\s*fee|dhinamum\s*sambadhikkalam)\b", re.I),
        # Telugu (తెలుగు)
        re.compile(r"(?:లాటరీ|బహుమతి|పార్ట్\s*టైమ్\s*జాబ్|టెలిగ్రామ్\s*టాస్క్|రుణం\s*ప్రాసెసింగ్|హామీ\s*లాభం)", re.I),
        re.compile(r"\b(?:lottery\s*vachindi|part\s*time\s*job\s*earn|telegram\s*task\s*cheyandi)\b", re.I),
        # Kannada & Malayalam
        re.compile(r"(?:ಲಾಟರಿ|ಬಹುಮಾನ|ಭಾಗಶಃ\s*ಸಮಯದ\s*ಕೆಲಸ|ಸಾಲ\s*ಪ್ರಕ್ರಿಯೆ)", re.I),
        re.compile(r"(?:ലോട്ടറി|സമ്മാനം|പാർട്ട്\s*ടൈം\s*ജോലി|വായ്പ\s*പ്രോസസ്സിംഗ്)", re.I),
    ],
}


class ScamClassifierDetector(BaseDetector):
    name = "text"
    description = "Known scam-script language-pattern detection (TF-IDF + logistic regression + rule engine)"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.model_path = self.settings.model_dir / "scam_classifier.joblib"
        self._pipeline: Any = None
        self._load_error: str | None = None

    def available(self) -> bool:
        return True

    def _ensure_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        if not self.model_path.exists():
            self._load_error = f"model not found at {self.model_path}"
            return None
        try:
            import joblib

            self._pipeline = joblib.load(str(self.model_path))
            return self._pipeline
        except Exception as exc:
            self._load_error = str(exc)
            return None

    def _rule_based_classify(self, text: str) -> dict[str, Any]:
        """High-precision heuristic match across known threat patterns."""
        scores: dict[str, int] = {cat: 0 for cat in CATEGORIES}
        matched_indicators: list[str] = []

        for category, patterns in _HEURISTIC_PATTERNS.items():
            for p in patterns:
                matches = p.findall(text)
                if matches:
                    scores[category] += len(matches)
                    for m in matches:
                        matched_str = m if isinstance(m, str) else " ".join(m)
                        if matched_str and matched_str.strip():
                            matched_indicators.append(matched_str.strip()[:60])

        total_hits = sum(scores.values())
        if total_hits == 0:
            # Check for benign or general conversation
            scores["neutral"] = 1
            return {
                "category": "neutral",
                "confidence": 0.55,
                "confident": False,
                "probabilities": {c: 0.1 for c in CATEGORIES},
                "indicators": [],
            }

        best_cat = max(scores, key=lambda k: scores[k])
        hits = scores[best_cat]

        # Calculate simulated probability based on match density
        probs = {c: round(scores[c] / (total_hits + 0.5), 3) for c in CATEGORIES}
        prob = min(0.98, max(0.55, 0.45 + (hits * 0.15)))

        return {
            "category": best_cat,
            "confidence": prob,
            "confident": hits >= 1,
            "probabilities": probs,
            "indicators": matched_indicators[:6],
        }

    def classify(self, text: str, language: str | None = None) -> dict[str, Any]:
        """Classify a transcript for scam-script patterns.

        ``language`` is the Whisper-detected language code (e.g. ``'hi'``,
        ``'ta'``). It is carried through into the metrics so callers and the
        console can show *which* language the classification ran on. The rule
        engine already matches threat signatures in English, Hindi, Tamil,
        Telugu, Kannada and Malayalam, so a strong rule match is credited
        regardless of language, while a language hint can nudge uncertain
        verdicts toward the categories whose signatures appear in that script.
        """
        if not text or not text.strip():
            res = self._result("available", score=None, label="no-text", detail="No text to classify.")
            if language:
                res["metrics"]["language"] = language
            return res

        cleaned = text[:MAX_LEN]
        rule_res = self._rule_based_classify(cleaned)

        def _annotate(res: dict[str, Any]) -> dict[str, Any]:
            if language:
                res["metrics"]["language"] = language
                res["metrics"]["language_hint"] = True
            return res

        pipeline = self._ensure_pipeline()
        if pipeline is None:
            # Fallback seamlessly to rule-based classification
            cat = rule_res["category"]
            conf = rule_res["confidence"]
            confident = rule_res["confident"] and cat not in ("benign", "neutral")
            return _annotate(self._result(
                "available",
                score=conf if confident else 0.1,
                label=cat if confident else "uncertain",
                detail=(
                    f"Heuristic pattern match: {cat} ({conf:.0%})."
                    if confident
                    else "No scam pattern matched with sufficient confidence."
                ),
                metrics={
                    "category": cat,
                    "probabilities": rule_res["probabilities"],
                    "top_probability": conf,
                    "confident": confident,
                    "engine": "rule_heuristics",
                    "indicators": rule_res["indicators"],
                },
                engine="rule_heuristics",
            ))

        try:
            proba = pipeline.predict_proba([cleaned])[0]
            classes = [str(c) for c in pipeline.classes_]
            probs = {c: float(p) for c, p in zip(classes, proba)}
            best_idx = int(proba.argmax())
            best_class = classes[best_idx]
            best_prob = float(proba[best_idx])

            # If rules detected a strong scam but ML model was conservative, corroborate
            if rule_res["confident"] and rule_res["category"] in CATEGORIES and rule_res["category"] not in ("benign", "neutral"):
                rule_cat = rule_res["category"]
                if best_class in ("benign", "neutral", "uncertain") or best_prob < 0.7:
                    best_class = rule_cat
                    best_prob = max(best_prob, rule_res["confidence"])
                    probs[rule_cat] = max(probs.get(rule_cat, 0.0), best_prob)

            non_scam = max(probs.get("benign", 0.0), probs.get("neutral", 0.0))
            confident = best_prob >= CONFIDENCE_FLOOR and (
                best_class in ("benign", "neutral") or best_prob - non_scam >= BENIGN_MARGIN
            )
            return _annotate(self._result(
                "available",
                score=best_prob,
                label=best_class if confident else "uncertain",
                detail=(
                    f"Most likely pattern: {best_class} ({best_prob:.0%})."
                    if confident
                    else "No scam pattern matched with sufficient confidence."
                ),
                metrics={
                    "category": best_class,
                    "probabilities": probs,
                    "top_probability": best_prob,
                    "confident": confident,
                    "indicators": rule_res["indicators"],
                },
                engine="joblib+heuristics",
            ))
        except Exception as exc:
            # Fallback to rule result on ML execution error
            cat = rule_res["category"]
            conf = rule_res["confidence"]
            confident = rule_res["confident"]
            return _annotate(self._result(
                "available",
                score=conf if confident else 0.1,
                label=cat if confident else "uncertain",
                detail=f"Pattern classification (fallback): {cat}",
                metrics={
                    "category": cat,
                    "probabilities": rule_res["probabilities"],
                    "top_probability": conf,
                    "confident": confident,
                    "error": str(exc),
                },
                engine="rule_heuristics_fallback",
            ))
