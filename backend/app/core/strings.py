"""Localized user-facing strings (English + Hindi).

This module is the single source of truth for red-flag explanations and
recommended next steps shown to users. Keeping the text here (not scattered
through detectors) makes it easy to add languages and keep tone consistent.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Red flags produced by the risk engine. `category` maps to the detector that
# raised it (voice / video / text) so the UI can colour-code by source.
# ---------------------------------------------------------------------------

RED_FLAGS: dict[str, dict] = {
    # -- Voice signals -------------------------------------------------------
    "voice-ai-likely": {
        "category": "voice",
        "severity": "critical",
        "title": {"en": "Voice appears AI-generated or cloned", "hi": "आवाज़ AI-जनित या क्लोन की गई लगती है"},
        "detail": {
            "en": "The audio shows strong markers of synthetic or cloned speech (verified by the anti-spoofing model). A caller claiming to be a relative may be an impersonator.",
            "hi": "ऑडियो में सिंथेटिक या क्लोन की गई आवाज़ के स्पष्ट संकेत मिले। परिवार के सदस्य का दावा करने वाला कॉलर वास्तव में धोखेबाज़ हो सकता है।",
        },
    },
    "voice-artifacts": {
        "category": "voice",
        "severity": "warning",
        "title": {"en": "Voice shows signs of manipulation", "hi": "आवाज़ में हेरफेर के संकेत"},
        "detail": {
            "en": "The audio contains digital artifacts or unusual timing typical of AI-generated voice. This alone is not proof of fraud but is a caution signal.",
            "hi": "ऑडियो में AI-जनित आवाज़ के विशिष्ट अजीब संकेत या टाइमिंग की गड़बड़ी है। यह अकेले धोखे का प्रमाण नहीं है, पर सावधानी का संकेत है।",
        },
    },
    "voice-cannot-check": {
        "category": "voice",
        "severity": "info",
        "title": {"en": "Voice authenticity could not be checked", "hi": "आवाज़ की प्रामाणिकता जाँची नहीं जा सकी"},
        "detail": {
            "en": "No deepfake-voice model is loaded on this server. Speech-analyis results rely on statistical artifacts only.",
            "hi": "इस सर्वर पर डीपफेक-आवाज़ मॉडल उपलब्ध नहीं है। परिणाम केवल सांख्यिकीय संकेतों पर आधारित हैं।",
        },
    },
    # -- Video signals -------------------------------------------------------
    "video-edited": {
        "category": "video",
        "severity": "critical",
        "title": {"en": "Video shows signs of editing", "hi": "वीडियो में एडिटिंग के संकेत"},
        "detail": {
            "en": "Frame-level analysis found inconsistent face regions or frame duplication typical of deepfake manipulation.",
            "hi": "फ़्रेम-स्तरीय विश्लेषण में डीपफेक हेरफेर के विशिष्ट फ़ेस-क्षेत्र में असंगति या फ़्रेम दोहराव मिला।",
        },
    },
    "video-warning": {
        "category": "video",
        "severity": "warning",
        "title": {"en": "Video analysis flagged irregularities", "hi": "वीडियो विश्लेषण में अनियमितता मिली"},
        "detail": {
            "en": "The clip showed abnormal motion or sharpness patterns in the face region. Verify the caller by another channel.",
            "hi": "क्लिप में चेहरे के क्षेत्र में असामान्य गति या शार्पनेस पैटर्न मिला। कॉलर की किसी और माध्यम से पुष्टि करें।",
        },
    },
    "video-cannot-check": {
        "category": "video",
        "severity": "info",
        "title": {"en": "Video face analysis was limited", "hi": "वीडियो चेहरे का विश्लेषण सीमित था"},
        "detail": {
            "en": "No clear face was detected, so deepfake indicators could not be computed. This is common for short clips.",
            "hi": "कोई स्पष्ट चेहरा नहीं मिला, इसलिए डीपफेक संकेतों की गणना नहीं हो सकी। छोटी क्लिप में यह आम है।",
        },
    },
    # -- AI second-opinion signals -----------------------------------------
    "ai-llm-corrob": {
        "category": "ai",
        "severity": "warning",
        "title": {"en": "AI found additional scam indicators", "hi": "AI ने अतिरिक्त धोखाधड़ी के संकेत पाए"},
        "detail": {
            "en": "An independent AI review of the transcript found language consistent with a known scam pattern, even though the local models rated it low risk. Verify the caller through an official channel before trusting any request.",
            "hi": "ट्रांसक्रिप्ट की स्वतंत्र AI समीक्षा में जाने-माने स्कैम पैटर्न जैसी भाषा मिली, हालाँकि स्थानीय मॉडलों ने इसे कम जोखिम बताया था। किसी अनुरोध पर भरोसा करने से पहले कॉलर की पुष्टि आधिकारिक माध्यम से करें।",
        },
    },
    # -- Text / scam-script signals -----------------------------------------
    "scam-arrest": {
        "category": "text",
        "severity": "critical",
        "title": {"en": "Matches known 'digital arrest' scam script", "hi": "जाने-माने 'डिजिटल अरेस्ट' घोटाले के पैटर्न से मेल"},
        "detail": {
            "en": "The conversation repeats phrases used in fake police/CBI/customs 'digital arrest' scams — threats of arrest, demands to stay on a video call, and 'verification' pressure. Police never arrest or 'verify' you over a video call, and no agency demands money to drop charges.",
            "hi": "बातचीत में फर्जी पुलिस/सीबीआई/कस्टम्स 'डिजिटल अरेस्ट' घोटाले के वाक्यांश हैं — गिरफ़्तारी की धमकी, वीडियो कॉल पर बने रहने का दबाव और 'वेरिफिकेशन'। पुलिस वीडियो कॉल पर कभी गिरफ़्तार या 'वेरिफाई' नहीं करती, और कोई एजेंसी आरोप हटाने के लिए पैसे नहीं माँगती।",
        },
    },
    "scam-courier": {
        "category": "text",
        "severity": "critical",
        "title": {"en": "Matches fake courier/parcel scam script", "hi": "फर्जी कूरियर/पार्सल घोटाले के पैटर्न से मेल"},
        "detail": {
            "en": "The call uses the fake parcel trap — 'your parcel has illegal drugs' — used to create panic and push you to share bank details or pay 'fees'.",
            "hi": "कॉल में फर्जी पार्सल का जाल है — 'आपके पार्सल में नशीला पदार्थ मिला' — जो घबराहट पैदा कर बैंक विवरण या 'फीस' माँगने के लिए इस्तेमाल होता है।",
        },
    },
    "scam-otp": {
        "category": "text",
        "severity": "critical",
        "title": {"en": "Requests for OTP / bank verification", "hi": "OTP / बैंक वेरिफिकेशन की माँग"},
        "detail": {
            "en": "The caller asks for OTPs, PINs, or UPI details. No genuine bank, KYC or service agent ever asks for these — sharing them lets a fraudster empty your account.",
            "hi": "कॉलर OTP, PIN या UPI विवरण माँग रहा है। कोई भी असली बैंक, KYC या सेवा एजेंट यह कभी नहीं माँगता — इन्हें साझा करते ही धोखेबाज़ आपका खाता खाली कर सकता है।",
        },
    },
    "scam-kin": {
        "category": "text",
        "severity": "critical",
        "title": {"en": "Urgent money request impersonating a relative", "hi": "रिश्तेदार बनकर तुरंत पैसे की माँग"},
        "detail": {
            "en": "The pattern matches 'fake relative in trouble' fraud (often paired with a cloned voice). Always verify by calling the person's known number before sending money.",
            "hi": "यह पैटर्न 'रिश्तेदार मुसीबत में' वाले धोखे (अक्सर क्लोन की गई आवाज़ के साथ) से मेल खाता है। पैसे भेजने से पहले हमेशा जाने-पहचाने नंबर पर कॉल करके पुष्टि करें।",
        },
    },
    "scam-generic": {
        "category": "text",
        "severity": "warning",
        "title": {"en": "Scam-like language pattern detected", "hi": "घोटाले जैसा भाषा-पैटर्न मिला"},
        "detail": {
            "en": "The transcript contains pressure tactics common to fraud: urgency, secrecy, threats, or requests for personal/financial details.",
            "hi": "ट्रांसक्रिप्ट में धोखे की आम दबाव रणनीति है: जल्दबाज़ी, गोपनीयता, धमकी, या व्यक्तिगत/वित्तीय जानकारी की माँग।",
        },
    },
    "text-benign": {
        "category": "text",
        "severity": "info",
        "title": {"en": "No known scam pattern in the speech", "hi": "बोली में कोई ज्ञात घोटाला पैटर्न नहीं"},
        "detail": {
            "en": "The transcription did not match any documented scam script. Always remain cautious with unknown callers.",
            "hi": "ट्रांसक्रिप्शन किसी दस्तावेजित घोटाला स्क्रिप्ट से नहीं मेल खाता। अनजान कॉलरों से हमेशा सतर्क रहें।",
        },
    },
    "low-audio-quality": {
        "category": "audio",
        "severity": "info",
        "title": {"en": "Audio quality limited transcription", "hi": "ऑडियो गुणवत्ता ने ट्रांसक्रिप्शन सीमित किया"},
        "detail": {
            "en": "Background noise or poor recording quality reduced confidence. Results should be treated with extra caution.",
            "hi": "पृष्ठभूमि शोर या खराब रिकॉर्डिंग से आत्मविश्वास कम रहा। परिणामों को अतिरिक्त सावधानी से लें।",
        },
    },
}

# ---------------------------------------------------------------------------
# Next steps shown alongside the risk verdict.
# ---------------------------------------------------------------------------

NEXT_STEPS: dict[str, dict] = {
    "verify-official": {
        "kind": "verify",
        "title": {
            "en": "Hang up and verify through an official channel",
            "hi": "कॉल बंद करें और आधिकारिक माध्यम से पुष्टि करें",
        },
        "detail": {
            "en": "Independently call the police station, bank, or agency the caller claims to represent — using a number you find yourself, not one they give you.",
            "hi": "कॉलर जिस पुलिस थाने, बैंक या एजेंसी का दावा करता है, उसे स्वयं से जुड़े नंबर पर कॉल करें — उनके बताए नंबर पर नहीं।",
        },
    },
    "no-otp": {
        "kind": "generic",
        "title": {"en": "Never share OTP, PIN or UPI details", "hi": "OTP, PIN या UPI विवरण कभी साझा न करें"},
        "detail": {
            "en": "No genuine authority asks for these over a call. Sharing them can empty your bank account instantly.",
            "hi": "कोई भी असली प्राधिकरण कॉल पर ये कभी नहीं माँगता। इन्हें साझा करने से आपका बैंक खाता तुरंत खाली हो सकता है।",
        },
    },
    "no-arrest-fee": {
        "kind": "generic",
        "title": {"en": "There is no 'digital arrest' fee", "hi": "'डिजिटल अरेस्ट' शुल्क जैसी कोई चीज़ नहीं है"},
        "detail": {
            "en": "Indian agencies never demand money to avoid arrest, bail or 'verification'. Anyone asking you to pay or transfer money is committing fraud.",
            "hi": "भारतीय एजेंसियां गिरफ़्तारी, ज़मानत या 'वेरिफिकेशन' से बचने के लिए कभी पैसे नहीं माँगतीं। जो भी पैसे माँगे या ट्रांसफर कराए, वह धोखा है।",
        },
    },
    "stay-on-call": {
        "kind": "generic",
        "title": {"en": "You are not under 'digital arrest'", "hi": "आप 'डिजिटल अरेस्ट' में नहीं हैं"},
        "detail": {
            "en": "Staying on a video call under someone's orders is a hallmark of this scam. You can and should hang up at any time.",
            "hi": "किसी के आदेश पर वीडियो कॉल पर बने रहना इस घोटाले की पहचान है। आप कभी भी कॉल बंद कर सकते हैं और करना चाहिए।",
        },
    },
    "report-1930": {
        "kind": "call",
        "title": {"en": "Report to the national helpline 1930", "hi": "राष्ट्रीय हेल्पलाइन 1930 पर शिकायत करें"},
        "detail": {
            "en": "Call 1930 immediately if money has been lost or the caller persists. The helpline can help freeze the fraudulent transaction.",
            "hi": "यदि पैसे गए हैं या कॉलर ज़िद करता है तो तुरंत 1930 पर कॉल करें। हेल्पलाइन धोखाधड़ी वाले लेन-देन को रोकने में मदद कर सकती है।",
        },
    },
    "report-portal": {
        "kind": "visit",
        "title": {"en": "File a complaint at cybercrime.gov.in", "hi": "cybercrime.gov.in पर शिकायत दर्ज करें"},
        "detail": {
            "en": "Report online through the National Cyber Crime Reporting Portal. Attach the recording and caller details you have.",
            "hi": "राष्ट्रीय साइबर अपराध रिपोर्टिंग पोर्टल पर ऑनलाइन शिकायत करें। अपनी रिकॉर्डिंग और कॉलर विवरण संलग्न करें।",
        },
    },
    "contact-family": {
        "kind": "generic",
        "title": {"en": "Verify with a trusted person", "hi": "किसी विश्वसनीय व्यक्ति से पुष्टि करें"},
        "detail": {
            "en": "Talk to a family member or your local police before acting on any urgent money request.",
            "hi": "किसी भी तत्काल पैसे की माँग पर कार्रवाई से पहले परिवार के सदस्य या स्थानीय पुलिस से बात करें।",
        },
    },
    "registry-verify": {
        "kind": "verify",
        "title": {"en": "Check against the Family Safe-Voice Registry", "hi": "फैमिली सेफ-वॉइस रजिस्ट्री से मिलान करें"},
        "detail": {
            "en": "Verify the voice note against a registered family member before trusting a money request.",
            "hi": "पैसे की माँग पर भरोसा करने से पहले वॉइस नोट का रजिस्टर्ड परिवार सदस्य से मिलान करें।",
        },
    },
    "stay-vigilant": {
        "kind": "generic",
        "title": {"en": "Stay cautious with unknown callers", "hi": "अनजान कॉलरों से सतर्क रहें"},
        "detail": {
            "en": "Legitimate institutions never rush you or demand secrecy. When in doubt, disconnect and verify independently.",
            "hi": "वैध संस्थान कभी जल्दबाज़ी नहीं करते और गोपनीयता की ज़िद नहीं करते। संदेह होने पर कॉल बंद करें और स्वयं पुष्टि करें।",
        },
    },
    "terminate-call": {
        "kind": "generic",
        "title": {"en": "TERMINATE the call — AI-generated voice detected", "hi": "कॉल समाप्त करें — AI-जनित आवाज़ का पता चला है"},
        "detail": {
            "en": "Model-backed classifiers confirm the caller's voice is synthetic or cloned (AASIST/wav2vec2/Dhwani). Do not share any information, OTP or money, and disconnect now.",
            "hi": "मॉडल-आधारित क्लासिफ़ायर पुष्टि करते हैं कि कॉलर की आवाज़ सिंथेटिक या क्लोन की गई है। कोई जानकारी, OTP या पैसा साझा न करें और अभी कॉल समाप्त करें।",
        },
    },
}

RISK_LABELS: dict[str, dict] = {
    "low": {
        "en": "Low risk — no strong fraud signals detected",
        "hi": "कम जोखिम — कोई स्पष्ट धोखाधड़ी संकेत नहीं मिला",
    },
    "medium": {
        "en": "Medium risk — be cautious and verify independently",
        "hi": "मध्यम जोखिम — सतर्क रहें और स्वयं पुष्टि करें",
    },
    "high": {
        "en": "High risk — this looks like a likely scam call",
        "hi": "उच्च जोखिम — यह संभावित धोखाधड़ी कॉल प्रतीत होती है",
    },
}
