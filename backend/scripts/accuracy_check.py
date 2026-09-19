"""Quick accuracy sanity-check for the DigiRaksha analysis pipeline.

Runs representative benign / neutral / scam transcripts through the full
pipeline and prints the risk verdict for each. Use it to demo the app and to
verify that ordinary calls no longer get flagged as high-risk.

Run:  C:\\dr-venv\\Scripts\\python.exe scripts\\accuracy_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.pipeline import get_pipeline  # noqa: E402

CASES: list[tuple[str, str]] = [
    # English Benign
    ("low", "good morning, this is the restaurant calling to confirm your food order"),
    ("low", "hi dad, I will reach home by evening, no need to worry"),
    ("low", "your parcel will be delivered tomorrow morning by the courier company"),
    ("low", "this is the bank calling to confirm you received our new card"),
    ("low", "your electricity bill for this month has been paid successfully"),
    ("low", "hello, sorry I think I dialed the wrong number, can you hear me clearly"),
    # Hindi Benign & Neutral
    ("low", "yeh courier company se bol rahe hain, aapka parcel kal subah deliver hoga"),
    ("low", "namaste, aapke order ki pushti ke liye restaurant se bol rahe hain"),
    # Tamil Benign
    ("low", "வணக்கம், உங்கள் உணவு ஆர்டரை உறுதிப்படுத்த உணவகத்திலிருந்து அழைக்கிறோம்"),
    ("low", "அப்பா, நான் மாலைக்குள் வீட்டிற்கு வந்துவிடுவேன், கவலைப்பட வேண்டாம்"),
    # English Scams
    ("high", "this is the CBI, you are under digital arrest, stay on the video call, pay the verification fee now"),
    ("high", "a parcel in your name contains drugs and foreign currency, pay the customs clearance fee to release it"),
    ("high", "your bank account will be blocked, share the OTP you received to verify your KYC"),
    ("high", "mama it is me, I am in trouble, the police want bail money, transfer it urgently and do not tell anyone"),
    ("high", "congratulations you have won a lottery, pay the processing fee to claim your prize"),
    # Hindi Scams
    ("high", "yeh CBI hai, aap digital arrest ho, turant verification fee jama karo"),
    ("high", "मैं सीबीआई से बोल रहा हूँ, आपके नाम पर मनी लॉन्ड्रिंग का केस दर्ज हुआ है, आप डिजिटल अरेस्ट में हैं"),
    ("high", "आपका बैंक खाता ब्लॉक हो गया है, तुरंत ओटीपी बताएं बिजली कट जाएगी"),
    # Tamil Scams (தமிழ்)
    ("high", "நான் சிபிஐ அதிகாரி பேசுகிறேன், உங்கள் மீது பணமோசடி வழக்கு பதிவு செய்யப்பட்டுள்ளது, நீங்கள் டிஜிட்டல் கைது"),
    ("high", "உங்கள் பார்சலில் போதைப்பொருள் மற்றும் கள்ளப்பணம் சுங்கத்துறையினரால் பறிமுதல் செய்யப்பட்டுள்ளது, சுங்க வரி கட்டவும்"),
    ("high", "சந்தேகத்திற்குரிய நடவடிக்கையால் வங்கி கணக்கு முடக்கப்பட்டுள்ளது, ஓடிபி எண்ணை உடனடியாக பகிருங்கள்"),
    ("high", "naan CBI officer pesuren, unga mela money laundering case irukku, neenga digital arrest video call cut panna koodathu"),
    # Telugu Scams (తెలుగు)
    ("high", "ఇది సిబిఐ దర్యాప్తు, మీపై మనీ లాండరింగ్ కేసు నమోదైంది మరియు మీరు డిజిటల్ అరెస్ట్ అయ్యారు"),
]


def main() -> int:
    pipeline = get_pipeline()
    print(f"{'expected':<8} {'level':<8} {'score':>6}  text-label")
    print("-" * 58)
    bad = 0
    for expected, text in CASES:
        res = pipeline.analyze_transcript(text, skip_ai=True)
        risk = res["risk"]
        text_label = (res["signals"]["text"] or {}).get("label")
        ok = risk["level"].startswith(expected)
        if not ok:
            bad += 1
        flag = "OK " if ok else "MISS"
        print(f"{expected:<8} {risk['level']:<8} {risk['score']:>6.1f}  {text_label:<14} {flag}", flush=True)
    print("-" * 58, flush=True)
    print(f"{len(CASES) - bad}/{len(CASES)} matched expected level")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
