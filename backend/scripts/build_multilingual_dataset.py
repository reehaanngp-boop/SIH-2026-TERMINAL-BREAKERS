"""Multilingual Scam Classifier Builder & Trainer.

Expands training data to comprehensively cover:
- Tamil (தமிழ்) & Tanglish (romanised Tamil)
- Telugu (తెలుగు)
- Hindi (हिन्दी) & Hinglish (romanised Hindi)
- English (en)
- Kannada & Malayalam
Across all fraud vectors:
1. digital_arrest
2. fake_courier
3. otp_phishing
4. kin_emergency
5. other_fraud
6. benign
7. neutral
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_JSONL = PROJECT_ROOT / "data" / "datasets" / "scam_dataset.jsonl"
OUT_CSV = PROJECT_ROOT / "data" / "datasets" / "scam_dataset.csv"
OUT_MODEL = PROJECT_ROOT / "data" / "models" / "scam_classifier.joblib"

CATEGORIES = ["digital_arrest", "fake_courier", "otp_phishing", "kin_emergency", "other_fraud", "benign", "neutral"]

FRAGMENTS: dict[str, dict[str, list[str]]] = {
    "digital_arrest": {
        "en": [
            "this is the CBI investigating your case, you are under digital arrest",
            "a case has been registered against you at the cyber crime cell",
            "your Aadhaar and bank account have been used in a money laundering case",
            "you must stay on this video call until the verification is complete",
            "if you hang up or inform anyone, we will send the police to arrest you",
            "you have a red corner notice against your name",
            "we are putting you under digital house arrest for your own safety",
            "pay the verification fee immediately to close the case",
            "a parcel in your name contained drugs and your identity was used",
            "you are suspected in a human trafficking and money laundering case",
            "cooperate with the investigation or you will be arrested at your doorstep",
            "share your bank statement so we can verify your innocence",
            "the Supreme Court has ordered you to pay the penalty today itself",
            "do not tell your family about this investigation, it is confidential",
            "your name is in the Enforcement Directorate money laundering investigation",
            "we have a warrant for your arrest signed by the judge",
            "transfer the amount to the nodal officer account for verification",
            "stay in an isolated room with camera on, this is digital interrogation",
        ],
        "hi": [
            "यह सीबीआई है, आपके खिलाफ जांच चल रही है और आप गिरफ्तार हैं",
            "साइबर क्राइम सेल में आपके नाम पर मामला दर्ज हो गया है",
            "आपके आधार और बैंक खाते का इस्तेमाल मनी लॉन्ड्रिंग में हुआ है",
            "वेरिफिकेशन पूरा होने तक आपको इसी वीडियो कॉल पर रहना होगा",
            "अगर आपने कॉल बंद किया या किसी को बताया तो पुलिस आपको गिरफ्तार करने आएगी",
            "आपके नाम पर रेड कॉर्नर नोटिस जारी हुआ है",
            "आपकी सुरक्षा के लिए आपको डिजिटल नजरबंद रखा गया है",
            "मामला बंद करने के लिए तुरंत वेरिफिकेशन शुल्क जमा करें",
            "आपके नाम से पार्सल में नशीला पदार्थ मिला है",
            "आप पर मानव तस्करी और मनी लॉन्ड्रिंग का संदेह है",
            "जांच में सहयोग करें वरना आपके घर पर गिरफ्तारी होगी",
            "अपनी बेगुनाही साबित करने के लिए बैंक स्टेटमेंट भेजें",
            "अदालत ने आज ही जुर्माना चुकाने का आदेश दिया है",
            "इस जांच के बारे में परिवार को मत बताइए, यह गोपनीय है",
            "प्रवर्तन निदेशालय की मनी लॉन्ड्रिंग जांच में आपका नाम है",
            "जज ने आपकी गिरफ्तारी का वारंट जारी किया है",
            "वेरिफिकेशन के लिए राशि नोडल अधिकारी के खाते में ट्रांसफर करें",
        ],
        "hi-en": [
            "yeh CBI hai, aapke upar case registered hai aur aap arrested ho",
            "cyber crime cell me aapke naam pe case darj ho gaya hai",
            "aapke aadhaar aur bank account se money laundering hua hai",
            "verification complete hone tak aapko video call pe hi rehna hai",
            "agar aapne call band kiya ya kisi ko bataya to police arrest karne aayegi",
            "aapke naam par red corner notice jari hua hai",
            "aapko digital house arrest me rakh rahe hain",
            "case band karne ke liye turant verification fee jama karein",
            "aapke naam ke parcel me nasha mila hai",
            "aap par human trafficking aur money laundering ka sandeh hai",
            "investigation me cooperate karo warna ghar pe arrest hoga",
            "apni be-gunaahi sabit karne ke liye bank statement bhejo",
            "court ne aaj hi penalty bhugtane ka aadesh diya hai",
            "is investigation ke bare me kisi ko mat batana, ye confidential hai",
            "aapka naam enforcement directorate ki money laundering jaanch me hai",
            "judge ne aapki arrest ka warrant jari kiya hai",
            "verification ke liye amount nodal officer ke account me transfer karein",
        ],
        "ta": [
            "நான் சிபிஐ அதிகாரி பேசுகிறேன், உங்கள் மீது பணமோசடி வழக்கு பதிவு செய்யப்பட்டுள்ளது",
            "சைபர் க்ரைம் பிரிவில் உங்கள் பெயரில் புகார் வந்துள்ளது, நீங்கள் டிஜிட்டல் கைது செய்யப்பட்டுள்ளீர்கள்",
            "உங்கள் ஆதார் மற்றும் வங்கி கணக்கு மூலம் சட்டவிரோத பண பரிமாற்றம் நடந்துள்ளது",
            "விசாரணை முடியும் வரை நீங்கள் இந்த வீடியோ அழைப்பில் மட்டுமே இருக்க வேண்டும்",
            "அழைப்பை துண்டித்தாலோ யாரிடமாவது கூறினாலோ உடனடியாக காவல்துறை உங்களை கைது செய்யும்",
            "உங்கள் பெயரில் ரெட் கார்னர் நோட்டீஸ் மற்றும் கைது வாரண்ட் பிறப்பிக்கப்பட்டுள்ளது",
            "உங்களை டிஜிட்டல் வீட்டுக்காவலில் வைக்கிறோம், கதவை பூட்டிக்கொள்ளுங்கள்",
            "வழக்கை முடிக்க சரிபார்ப்புக் கட்டணத்தை அரசு கணக்கில் உடனடியாக செலுத்துங்கள்",
            "உங்கள் பெயரில் வந்த பார்சலில் போதைப்பொருள் மற்றும் கள்ளப்பணம் பறிமுதல் செய்யப்பட்டுள்ளது",
            "மனித கடத்தல் மற்றும் பணமோசடி வழக்கில் நீங்கள் சந்தேக நபராக சேர்க்கப்பட்டுள்ளீர்கள்",
            "விசாரணைக்கு ஒத்துழைக்காவிட்டால் காவல்துறை உங்கள் வீட்டிற்கே வந்து கைது செய்யும்",
            "உங்கள் அப்பாவியான தன்மையை நிரூபிக்க வங்கி கணக்கு அறிக்கையை பகிருங்கள்",
            "உச்ச நீதிமன்றம் இன்று மாலைக்குள் அபராதம் செலுத்த உத்தரவிட்டுள்ளது",
            "இந்த ரகசிய விசாரணை பற்றி குடும்பத்தினரிடம் எதுவும் சொல்லக்கூடாது",
            "அமலாக்கத்துறை பணமோசடி விசாரணையில் உங்கள் பெயர் உள்ளது",
            "நீதிபதி உங்கள் கைது வாரண்டில் கையெழுத்திட்டுள்ளார்",
            "சரிபார்ப்பிற்காக தொகையை பாதுகாப்பு கணக்கிற்கு மாற்றுங்கள்",
        ],
        "ta-en": [
            "naan CBI officer pesuren, unga mela money laundering case irukku, neenga digital arrest",
            "cyber crime cell la unga perla case file aayirukku, digital arrest pannirukkom",
            "unga aadhaar card use panni illegal terror funding pannirukkanga",
            "verification mudiyara varaikkum video call cut panna koodathu, camera on la veinga",
            "call cut pannina police unga veetukku vandhu arrest pannum, kadhava poottunga",
            "unga perla non bailable arrest warrant and supreme court order vanthurukku",
            "ungala digital house arrest la vaikkurom, yaar kittayum pesa koodathu",
            "case close panna verification security deposit fee udane pay pannunga",
            "unga parcel la drugs irundhuchu, customs la pudichitanga, narcotics case",
            "police investigation ku cooperate pannunga illana jail ku poga vendiyirukkum",
            "unga bank statement anupunga, illana account freeze aayidum",
            "court order potturukku, innike penalty katta vendiyirukkum",
            "yaar kittayum idhai pathi pesa koodathu, idhu confidential investigation",
        ],
        "te": [
            "ఇది సిబిఐ దర్యాప్తు, మీపై మనీ లాండరింగ్ కేసు నమోదైంది మరియు మీరు డిజిటల్ అరెస్ట్ అయ్యారు",
            "సైబర్ క్రైమ్ సెల్‌లో మీ పేరుపై కేసు నమోదైంది, మీరు డిజిటల్ అరెస్టులో ఉన్నారు",
            "మీ ఆధార్ మరియు బ్యాంక్ ఖాతా ద్వారా అక్రమ లావాదేవీలు జరిగాయి",
            "ధృవీకరణ పూర్తయ్యే వరకు మీరు వీడియో కాల్‌లోనే ఉండాలి, కెమెరా ఆన్ చేయండి",
            "కాల్ కట్ చేస్తే లేదా ఎవరికైనా చెబితే పోలీసులు మీ ఇంటికి వచ్చి అరెస్ట్ చేస్తారు",
            "మీ పేరు మీద అరెస్ట్ వారెంట్ మరియు సుప్రీం కోర్టు ఆర్డర్ వచ్చింది",
            "మీ కేసు ముగించడానికి ధృవీకరణ రుసుమును వెంటనే ప్రభుత్వ ఖాతాకు చెల్లించండి",
            "మీ పార్శిల్‌లో డ్రగ్స్ మరియు నకిలీ పాస్‌పోర్టులు పట్టుబడ్డాయి",
            "ఈ దర్యాప్తు చాలా గోప్యమైనది, కుటుంబ సభ్యులకు కూడా చెప్పవద్దు",
        ],
    },
    "fake_courier": {
        "en": [
            "your international courier parcel has been stopped at customs",
            "a parcel sent in your name contains drugs and foreign currency",
            "the narcotics control bureau has opened a case about your parcel",
            "you need to pay the customs clearance fee to release the parcel",
            "the parcel has been linked to money laundering and contraband",
            "we have a CCTV image of your Aadhaar being used to book this courier",
            "pay the courier security deposit to avoid legal arrest action",
            "the RBI and customs have flagged your parcel for illegal synthetic drugs",
            "your parcel contained undeclared gold and foreign currency",
            "clear the parcel by paying the clearance charges today itself",
            "the courier company has handed your file to the cyber crime cell",
            "this parcel booking is registered under your mobile and Aadhaar number",
            "you must pay the customs insurance fee to release the package",
            "the police will arrest you for drug trafficking if you do not clear the parcel",
            "pay the refundable parcel clearance fee and the case will be closed",
        ],
        "hi": [
            "आपका अंतरराष्ट्रीय कूरियर पार्सल कस्टम में रुका हुआ है",
            "आपके नाम से भेजे गए पार्सल में नशीला पदार्थ और विदेशी मुद्रा मिली है",
            "नारकोटिक्स कंट्रोल ब्यूरो ने आपके पार्सल पर केस खोल दिया है",
            "पार्सल छुड़ाने के लिए कस्टम क्लियरेंस शुल्क जमा करना होगा",
            "पार्सल को मनी लॉन्ड्रिंग और नशीले पदार्थ से जोड़ा गया है",
            "कूरियर बुक कराने में आपके आधार के इस्तेमाल की सीसीटीवी तस्वीर है",
            "कानूनी कार्रवाई से बचने के लिए कूरियर सिक्योरिटी जमा करें",
            "आरबीआई और कस्टम ने आपके पार्सल को अवैध वस्तुओं के लिए चिह्नित किया है",
            "पार्सल में सोना मिला है जो आपने घोषित नहीं किया",
            "क्लियरेंस शुल्क जमा कर आज ही पार्सल छुड़ाएं",
            "कूरियर कंपनी ने आपकी फाइल साइबर सेल को सौंप दी है",
            "यह पार्सल आपके आधार नंबर पर बुक हुआ है",
            "पैकेज छुड़ाने के लिए बीमा शुल्क जमा करना होगा",
            "यदि आपने पार्सल नहीं छुड़ाया तो नशा तस्करी में गिरफ्तारी होगी",
            "पार्सल शुल्क जमा करें तो मामला बंद हो जाएगा",
        ],
        "hi-en": [
            "aapka international courier parcel customs me atak gaya hai",
            "aapke naam ke parcel me nasha aur foreign currency mili hai",
            "narcotics control bureau ne aapke parcel par case khol diya hai",
            "parcel chudane ke liye customs clearance fee jama karni hogi",
            "parcel money laundering aur drugs se juda hai",
            "courier book karane me aapke aadhaar ki cctv tasveer hai",
            "legal action se bachne ke liye courier security deposit jama karo",
            "rbi aur customs ne aapke parcel ko illegal items ke liye flag kiya hai",
            "parcel me sona mila hai jo aapne declare nahi kiya",
            "clearance charges jama karke aaj hi parcel chudao",
            "courier company ne aapki file cyber cell ko saunp di hai",
            "yeh parcel aapke aadhaar number par book hua hai",
            "package release karne ke liye insurance fee jama karni hogi",
            "parcel nahi chudaya to drug trafficking me arrest hoga",
            "parcel fee jama karo to case band ho jayega",
        ],
        "ta": [
            "உங்கள் சர்வதேச கொரியர் பார்சல் சுங்கத்துறையினரால் தடுத்து வைக்கப்பட்டுள்ளது",
            "உங்கள் பெயரில் அனுப்பப்பட்ட பார்சலில் போதைப்பொருள் மற்றும் வெளிநாட்டு நாணயம் உள்ளது",
            "போதைப்பொருள் கட்டுப்பாட்டு பணியகம் உங்கள் பார்சல் மீது வழக்கு பதிவு செய்துள்ளது",
            "பார்சலை விடுவிக்க சுங்க அனுமதி கட்டணம் செலுத்த வேண்டும்",
            "பார்சல் சட்டவிரோத பணப்பரிவர்த்தனை மற்றும் போதைப்பொருள் கடத்தலுடன் தொடர்புடையது",
            "கொரியர் முன்பதிவு செய்ய உங்கள் ஆதார் பயன்படுத்தப்பட்ட சிசிடிவி காட்சிகள் உள்ளன",
            "சட்ட நடவடிக்கை தவிர்க்க கொரியர் பாதுகாப்பு வைப்புத்தொகையை செலுத்துங்கள்",
            "ஆர்பிஐ மற்றும் சுங்கத்துறை உங்கள் பார்சலை தடை செய்துள்ளது",
            "பார்சலில் தங்கம் மற்றும் தடை செய்யப்பட்ட பொருட்கள் பறிமுதல் செய்யப்பட்டுள்ளன",
            "இன்றே அனுமதி கட்டணம் செலுத்தி பார்சலை விடுவித்துக் கொள்ளுங்கள்",
            "சுங்க வரி செலுத்தவில்லை என்றால் போதைப்பொருள் கடத்தல் சட்டத்தில் கைது செய்யப்படுவீர்கள்",
            "சுங்க அதிகாரி பேசுகிறேன், பார்சலில் போதைப்பொருள் கண்டுபிடிக்கப்பட்டுள்ளது",
        ],
        "ta-en": [
            "unga international courier parcel customs la hold pannirukanga",
            "unga perla vanda parcel la drugs and foreign currency irukku",
            "narcotics control bureau unga parcel mela case file pannitanga",
            "parcel release panna customs clearance fee udane katta vendiyirukkum",
            "legal action vendam na courier security deposit pay pannunga",
            "parcel la illegal items drugs irukkuradha customs officer report panniruku",
            "clearance charge katinal mattume parcel release aagum",
            "parcel chudaika fee katunga illana police case and arrest aagum",
        ],
        "te": [
            "మీ అంతర్జాతీయ కొరియర్ పార్శిల్ కస్టమ్స్‌లో ఆగిపోయింది",
            "మీ పేరుతో పంపిన పార్శిల్‌లో మాదకద్రవ్యాలు మరియు విదేశీ కరెన్సీ ఉన్నాయి",
            "నార్కోటిక్స్ కంట్రోల్ బ్యూరో మీ పార్శిల్ మీద కేసు నమోదు చేసింది",
            "పార్శిల్ విడుదల చేయడానికి కస్టమ్స్ క్లియరెన్స్ రుసుము చెల్లించాలి",
            "పార్శిల్ డ్రగ్స్ స్మగ్లింగ్‌తో ముడిపడి ఉంది, క్లియరెన్స్ ఫీజు కట్టండి",
            "కస్టమ్స్ డ్యూటీ చెల్లించకపోతే మిమ్మల్ని అరెస్ట్ చేస్తారు",
        ],
    },
    "otp_phishing": {
        "en": [
            "your bank account has been blocked due to suspicious activity",
            "your KYC is incomplete and your account will be frozen today",
            "your SIM card will be deactivated in two hours if you do not update now",
            "share the OTP you received to verify your bank account",
            "your net banking has been disabled for security, provide the code",
            "send the card number and the OTP to unblock your account",
            "you have won cashback, share the OTP to credit the amount",
            "your electricity bill is overdue, power will be disconnected tonight",
            "install this APK app to update your electricity bill or KYC",
            "share your screen via AnyDesk to complete mobile banking verification",
            "this is the bank security department, read the six digit OTP",
            "your credit card reward points are expiring, share OTP to redeem",
            "your FASTag account is blacklisted, verify with the OTP immediately",
        ],
        "hi": [
            "संदिग्ध गतिविधि के कारण आपका बैंक खाता ब्लॉक कर दिया गया है",
            "आपका केवाईसी अधूरा है, आज खाता फ्रीज हो जाएगा",
            "अपडेट नहीं किया तो आपका सिम कार्ड बंद हो जाएगा",
            "खाता सत्यापन के लिए प्राप्त ओटीपी साझा करें",
            "सुरक्षा के लिए आपका नेट बैंकिंग बंद कर दिया गया है",
            "खाता अनब्लॉक करने के लिए कार्ड नंबर और ओटीपी भेजें",
            "आपको कैशबैक मिला है, राशि जमा करने के लिए ओटीपी साझा करें",
            "बिजली का बिल बकाया है, आज रात बिजली काट दी जाएगी",
            "बिजली बिल अपडेट करने के लिए एपीके ऐप डाउनलोड करें",
            "स्क्रीन शेयर करें ताकि हम आपका खाता चालू कर सकें",
            "ओटीपी बताएं वरना सिम कार्ड हमेशा के लिए बंद हो जाएगा",
        ],
        "hi-en": [
            "suspicious activity ki wajah se aapka bank account block ho gaya hai",
            "aapka kyc adhura hai, aaj account freeze ho jayega",
            "update nahi kiya to aapka sim card do ghante me band ho jayega",
            "account verify karne ke liye jo otp aaya hai woh share karo",
            "security ke liye aapka net banking band kar diya gaya hai",
            "account unblock karne ke liye card number aur otp bhejo",
            "bijli ka bill baaki hai, aaj raat power cut ho jayega, otp batao",
            "sbi yono apk install karo aur screen share karo",
            "credit card reward points expire ho rahe hain, redeem karne ke liye otp do",
        ],
        "ta": [
            "சந்தேகத்திற்குரிய நடவடிக்கையால் உங்கள் வங்கி கணக்கு முடக்கப்பட்டுள்ளது",
            "உங்கள் கேஒய்சி முழுமையடையவில்லை, இன்று உங்கள் கணக்கு முடக்கப்படும்",
            "உடனடியாக புதுப்பிக்கவில்லை என்றால் உங்கள் சிம் கார்டு இரண்டு மணி நேரத்தில் துண்டிக்கப்படும்",
            "கணக்கை சரிபார்க்க உங்கள் மொபைலுக்கு வந்த ஓடிபியை பகிருங்கள்",
            "பாதுகாப்பு காரணங்களுக்காக உங்கள் நெட் பேங்கிங் நிறுத்தப்பட்டுள்ளது",
            "கணக்கை மீண்டும் செயல்படுத்த அட்டை எண் மற்றும் ஓடிபியை அனுப்புங்கள்",
            "உங்களுக்கு கேஷ்பேக் கிடைத்துள்ளது, பணத்தை வரவு வைக்க ஓடிபியை கூறுங்கள்",
            "உங்கள் மின்சாரக் கட்டணம் செலுத்தப்படவில்லை, இன்று இரவு மின்சாரம் துண்டிக்கப்படும்",
            "மின்சாரக் கட்டணத்தை புதுப்பிக்க கொடுக்கப்பட்ட ஏபிகே செயலியை பதிவிறக்குங்கள்",
            "ஸ்கிரீன் ஷேர் ஆன் செய்து ஓடிபி எண்ணை கூறுங்கள், கணக்கு சரியாகும்",
            "வங்கி அதிகாரி பேசுகிறேன், கணக்கை முடக்காமல் இருக்க ஓடிபி சொல்லுங்கள்",
        ],
        "ta-en": [
            "suspicious activity kaaranamaaga unga bank account block aayiduchu",
            "unga kyc incomplete ah irukku, innike account freeze aayidum",
            "update pannala na unga sim card 2 hours la deactivate aagum",
            "account verify panna ungalukku vandha 6 digit otp ya sollunga",
            "account unblock panna card number and otp send pannunga",
            "iniki night electricity current cut aayidum, bill update panna otp sollunga",
            "sbi yono apk download pannunga illana account block aayidum",
            "screen share on pannunga appo dhaan verify panna mudiyum",
            "otp solla vendiyadhu kattayam, illana bank balance poirum",
        ],
        "te": [
            "అనుమానాస్పద లావాదేవీల వల్ల మీ బ్యాంక్ ఖాతా బ్లాక్ చేయబడింది",
            "మీ కేవైసీ అసంపూర్ణంగా ఉంది, ఈరోజే మీ అకౌంట్ స్తంభింపజేయబడుతుంది",
            "వెంటనే అప్‌డేట్ చేయకపోతే మీ సిమ్ కార్డ్ డీయాక్టివేట్ అవుతుంది",
            "ఖాతా ధృవీకరణ కోసం మీకు వచ్చిన ఓటీపీని షేర్ చేయండి",
            "కరెంట్ బిల్లు పెండింగ్‌లో ఉంది, ఈరోజే విద్యుత్ సరఫరా నిలిపివేయబడుతుంది",
            "యాప్ డౌన్‌లోడ్ చేసి స్క్రీన్ షేర్ చేయండి, ఓటీపీ చెప్పండి",
        ],
    },
    "kin_emergency": {
        "en": [
            "mama, it is me, I am in serious trouble, please help me",
            "I met with an accident and the hospital is asking for money urgently",
            "I have been arrested by the police, they want bail money immediately",
            "please transfer the money urgently, do not tell mom and dad",
            "my phone was seized by the police, calling from the inspector phone",
            "your son has been arrested in a fight, transfer fifty thousand for bail",
            "your daughter met with an accident, send money to doctor UPI right now",
            "do not disconnect or verify, every minute matters for his life",
        ],
        "hi": [
            "मम्मी यह मैं हूँ, मैं बहुत बड़ी मुसीबत में हूँ, मेरी मदद करो",
            "मेरा भयानक एक्सीडेंट हो गया है, अस्पताल में ऑपरेशन के लिए पैसे चाहिए",
            "मुझे पुलिस ने पकड़ लिया है, ज़मानत के लिए तुरंत पैसे भेजो",
            "तुरंत पैसे ट्रांसफर कर दो, पापा को मत बताना, वे परेशान हो जाएंगे",
            "आपका बेटा थाने में बंद है, मामला रफा-दफा करने के लिए पैसे भेजो",
            "आपकी बेटी का एक्सीडेंट हुआ है, तुरंत डॉक्टर के खाते में पैसे डालो",
        ],
        "hi-en": [
            "mummy yeh main hoon, main museebat me hoon, meri madad karo",
            "mera accident ho gaya hai, hospital paise mang raha hai operation ke liye",
            "mujhe police ne arrest kar liya hai, bail ke liye paise chahiye",
            "turant paise transfer kar do, mummy papa ko mat batana",
            "aapka beta police custody me hai, bachana hai to turant paise bhejo",
        ],
        "ta": [
            "அம்மா, நான் விபத்தில் சிக்கிவிட்டேன், மருத்துவமனையில் அறுவை சிகிச்சைக்கு பணம் கேட்கிறார்கள்",
            "காவல்துறை என்னை கைது செய்துள்ளது, ஜாமீன் பெற உடனடியாக பணம் வேண்டும்",
            "உடனடியாக பணத்தை மாற்றுங்கள், அப்பாவிடம் இதை சொல்லாதீர்கள்",
            "என் தொலைபேசி உடைந்துவிட்டது, நண்பனின் எண்ணிலிருந்து அழைக்கிறேன், காப்பாற்றுங்கள்",
            "காவல் நிலையத்திலிருந்து பேசுகிறேன், உங்கள் மகன் வழக்கில் சிக்கியுள்ளார், பணம் அனுப்பவும்",
            "மருத்துவ சிகிச்சைக்கு உடனடியாக பணம் அனுப்பவில்லை என்றால் உயிருக்கு ஆபத்து",
        ],
        "ta-en": [
            "amma naan dhaan pesuren, enakku periya accident aayiduchu, hospital la surgery",
            "police enna arrest pannitanga, bail edukka ippove money anupunga",
            "udane panam anupunga pa, appa kitta sollidatheenga bayandhuduvanga",
            "en phone damaged, friend phone lendhu call panren, kaapathunga",
            "police station lendhu pesurom, unga paiyan custoday la irukkan, panam kattunga",
        ],
        "te": [
            "అమ్మా నేను ఆపదలో ఉన్నాను, నాకు యాక్సిడెంట్ అయింది, ఆసుపత్రికి డబ్బులు కావాలి",
            "పోలీసులు నన్ను అరెస్ట్ చేశారు, బెయిల్ కోసం వెంటనే డబ్బులు పంపించండి",
            "మీ అబ్బాయి పోలీస్ స్టేషన్‌లో ఉన్నాడు, కేసు లేకుండా ఉండాలంటే డబ్బులు పంపండి",
        ],
    },
    "other_fraud": {
        "en": [
            "congratulations, you have won the mega lottery of twenty five lakh rupees",
            "your number was selected in lucky draw, pay registration fee to claim prize",
            "invest in our crypto trading group and double your money in three days",
            "work from home part time job, earn five thousand daily by liking videos",
            "telegram task scam, complete simple rating tasks and get paid instantly",
            "instant pre approved loan approved with zero percent interest, pay processing charge",
            "guaranteed return on investment, pay the clearance tax to withdraw profits",
        ],
        "hi": [
            "बधाई हो, आपने पच्चीस लाख रुपये की लॉटरी जीती है",
            "आपका नंबर केबीसी लकी ड्रा में चुना गया है, प्रोसेसिंग फीस जमा करें",
            "पार्ट टाइम जॉब, टेलीग्राम पर वीडियो लाइक करके रोज़ तीन हज़ार कमाएं",
            "क्रिप्टो ट्रेडिंग में पैसा दोगुना करें, गारंटीड रिटर्न पाएं",
            "बिना ब्याज का पर्सनल लोन पास हो गया है, फाइल चार्ज जमा करें",
        ],
        "hi-en": [
            "badhai ho, aapne 25 lakh rupaye ki lottery jeeti hai",
            "kbc lucky draw me number laga hai, processing fee jama karo",
            "telegram task se daily 3000 kamao, work from home",
            "crypto profit double karne ke liye tax fee transfer karo",
        ],
        "ta": [
            "வாழ்த்துக்கள், நீங்கள் இருபத்தைந்து லட்சம் ரூபாய் மெகா லாட்டரியை வென்றுள்ளீர்கள்",
            "உங்கள் எண் பரிசுக்காக தேர்ந்தெடுக்கப்பட்டுள்ளது, செயலாக்கக் கட்டணம் செலுத்தி பணத்தைப் பெறுங்கள்",
            "வீட்டில் இருந்தே பகுதி நேர வேலை, யூடியூப் வீடியோக்களை லைக் செய்து தினமும் சம்பாதிக்கலாம்",
            "டெலிகிராம் டாஸ்க் செய்து தினமும் மூவாயிரம் ரூபாய் சம்பாதிக்கலாம்",
            "பூஜ்ஜிய வட்டி விகிதத்தில் உடனடி கடன், ஆவணக் கட்டணத்தை செலுத்துங்கள்",
        ],
        "ta-en": [
            "congratulations, ungalukku 25 lakh lottery prize adichirukku",
            "processing fee kattina prize money unga account ku credit aagum",
            "work from home part time job, youtube videos like panni daily 3000 earn pannalam",
            "telegram tasks mudicha instant payment, registration fee mattum kattunga",
        ],
        "te": [
            "అభినందనలు, మీరు 25 లక్షల రూపాయల లాటరీని గెలుచుకున్నారు",
            "పార్ట్ టైమ్ జాబ్, టెలిగ్రామ్ టాస్క్ చేసి రోజుకు వేలు సంపాదించండి",
            "తక్కువ వడ్డీతో తక్షణ రుణం, ప్రాసెసింగ్ ఫీజు చెల్లించండి",
        ],
    },
    "benign": {
        "en": [
            "good morning, this is the restaurant calling to confirm your food order",
            "hi dad, I will reach home by evening, no need to worry",
            "your parcel will be delivered tomorrow morning by the courier company",
            "this is the bank calling to confirm you received our new card",
            "your electricity bill for this month has been paid successfully",
            "the doctor appointment is scheduled for tomorrow at ten in the morning",
            "let us meet for lunch this weekend, let me know your availability",
            "the school parent teacher meeting is on Saturday at ten am",
            "your subscription renewal has been processed and invoice emailed",
            "the service technician will visit your home today between three and five",
        ],
        "hi": [
            "नमस्ते, आपके खाने के ऑर्डर की पुष्टि के लिए रेस्तरां से बोल रहे हैं",
            "पापा, मैं शाम तक घर पहुंच जाऊँगा, चिंता मत करिए",
            "आपका पार्सल कल सुबह कूरियर कंपनी द्वारा डिलीवर किया जाएगा",
            "हम बैंक से बोल रहे हैं, आपका नया डेबिट कार्ड मिल गया क्या",
            "इस महीने का बिजली बिल सफलतापूर्वक जमा हो गया है",
            "कल डॉक्टर से मिलने का समय सुबह दस बजे तय हुआ है",
            "इस सप्ताहांत दोपहर के भोजन पर मिलते हैं",
        ],
        "hi-en": [
            "namaste, aapke order ki pushti ke liye restaurant se bol rahe hain",
            "papa, main shaam tak ghar pahunch jaunga, chinta mat karo",
            "yeh courier company se bol rahe hain, aapka parcel kal subah deliver hoga",
            "is mahine ka bijli bill successfully jama ho gaya hai",
            "doctor appointment kal subah 10 baje confirm hai",
        ],
        "ta": [
            "வணக்கம், உங்கள் உணவு ஆர்டரை உறுதிப்படுத்த உணவகத்திலிருந்து அழைக்கிறோம்",
            "அப்பா, நான் மாலைக்குள் வீட்டிற்கு வந்துவிடுவேன், கவலைப்பட வேண்டாம்",
            "கொரியர் நிறுவனம் பேசுகிறோம், உங்கள் பார்சல் நாளை காலை வந்து சேரும்",
            "இந்த மாதத்திற்கான உங்கள் மின்சாரக் கட்டணம் வெற்றிகரமாக செலுத்தப்பட்டது",
            "மருத்துவரை சந்திக்கும் நேரம் நாளை காலை பத்து மணிக்கு உறுதி செய்யப்பட்டுள்ளது",
            "இந்த வார இறுதியில் மதிய உணவிற்கு சந்திக்கலாம், வருகிறீர்களா",
            "பள்ளியில் பெற்றோர் ஆசிரியர் சந்திப்பு சனிக்கிழமை நடைபெற உள்ளது",
        ],
        "ta-en": [
            "vanakkam, unga food order confirm panna restaurant lendhu call panrom",
            "appa naan evening kulla veetukku vandhuduven, don't worry",
            "courier parcel naalaikku morning unga address ku deliver aagidum",
            "intha month electricity bill successfully pay aayirukku",
            "doctor appointment naalaikku 10 AM ku fix pannirukanga",
            "weekend lunch ku meet pannalam, time sollu",
        ],
        "te": [
            "నమస్కారం, మీ ఆహార ఆర్డర్ నిర్ధారణ కోసం రెస్టారెంట్ నుండి కాల్ చేస్తున్నాము",
            "నాన్నా నేను సాయంత్రానికి ఇంటికి వస్తాను, ఆందోళన చెందవద్దు",
            "మీ కొరియర్ పార్శిల్ రేపు ఉదయం డెలివరీ చేయబడుతుంది",
            "ఈ నెల విద్యుత్ బిల్లు విజయవంతంగా చెల్లించబడింది",
        ],
    },
    "neutral": {
        "en": [
            "hello, sorry I think I dialed the wrong number",
            "can you hear me clearly, the network seems patchy today",
            "are you free this evening to catch up, let me check my calendar",
            "the meeting has been moved to three pm today, please note",
            "I am stuck in traffic, will be there in half an hour",
            "please send me the office address by text message",
            "how is the family doing, hope everyone is well at home",
        ],
        "hi": [
            "नमस्ते, मुझे लगता है गलत नंबर लग गया",
            "क्या आप मेरी आवाज सुन पा रहे हैं, नेटवर्क कट रहा है",
            "मैं ट्रैफिक में फंसा हूँ, आधे घंटे में पहुँच जाऊँगा",
            "घर पर सब कैसे हैं, सब ठीक ठाक है",
            "कृपया पता एसएमएस में भेज दीजिए",
        ],
        "hi-en": [
            "namaste, lagta hai galat number laga",
            "kya aap meri baat sun paa rahe ho, network issue hai",
            "main traffic me phansa hoon, aadhe ghante me pahunch jaunga",
            "office ka address whatsapp kar dijiye",
        ],
        "ta": [
            "வணக்கம், மன்னிக்கவும், நான் தவறான எண்ணிற்கு அழைத்துவிட்டேன் என்று நினைக்கிறேன்",
            "நான் பேசுவது தெளிவாக கேட்கிறதா, சிக்னல் சரியாக கிடைக்கவில்லை",
            "நான் டிராஃபிக்கில் சிக்கியுள்ளேன், அரை மணி நேரத்தில் வந்துவிடுவேன்",
            "வீட்டில் அனைவரும் நலமாக இருக்கிறார்களா, எல்லோருக்கும் நலம் விசாரித்தேன்",
            "அலுவலக முகவரியை எனக்கு குறுஞ்செய்தியாக அனுப்புங்கள்",
        ],
        "ta-en": [
            "hello sorry, wrong number ku call panniten nenaikiren",
            "pesardhu clear ah kekudha, network konjam weak ah irukku",
            "traffic la maatikiten, half an hour la reach aayiduven",
            "office address ah sms la anupunga",
        ],
        "te": [
            "హలో క్షమించండి, నేను తప్పు నంబర్‌కు కాల్ చేసినట్లున్నాను",
            "నా మాట స్పష్టంగా వినిపిస్తుందా, నెట్‌వర్క్ సరిగ్గా లేదు",
            "ట్రాఫిక్‌లో చిక్కుకున్నాను, అరగంటలో చేరుకుంటాను",
        ],
    },
}

OPENERS: dict[str, list[str]] = {
    "en": ["hello", "good morning", "namaste", "good afternoon", "excuse me", "sir", "madam"],
    "hi": ["नमस्ते", "सुप्रभात", "नमस्कार", "जी", "सुनिए", "साहब"],
    "hi-en": ["hello", "namaste", "ji", "suniye", "good morning"],
    "ta": ["வணக்கம்", "சார்", "மேடம்", "கேளுங்கள்", "வணக்கங்க"],
    "ta-en": ["vanakkam", "sir", "madam", "hello", "kelunga"],
    "te": ["నమస్కారం", "సర్", "మేడమ్", "వినండి"],
}
CONNECTORS: dict[str, list[str]] = {
    "en": ["and", "also", "so", "because", "therefore", "now", "listen"],
    "hi": ["और", "क्योंकि", "इसलिए", "लेकिन", "अब", "सुनिए"],
    "hi-en": ["aur", "kyunki", "isliye", "ab", "suniye"],
    "ta": ["மற்றும்", "மேலும்", "ஆனால்", "அதனால்", "இப்போது", "கேளுங்கள்"],
    "ta-en": ["aprom", "ana", "adhanaala", "ippo", "kelunga"],
    "te": ["మరియు", "అలాగే", "కానీ", "అందువల్ల", "ఇప్పుడు"],
}
CLOSERS: dict[str, list[str]] = {
    "en": ["do it immediately", "understand?", "ok?", "right now", "today itself"],
    "hi": ["तुरंत करें", "समझे?", "ठीक है?", "अभी", "आज ही"],
    "hi-en": ["turant karo", "samjhe?", "theek hai?", "abhi", "aaj hi"],
    "ta": ["உடனடியாக செய்யுங்கள்", "புரிகிறதா?", "சரிதானே?", "இப்போதே", "இன்றே"],
    "ta-en": ["udane pannunga", "puridha?", "seriya?", "ippove", "innike"],
    "te": ["వెంటనే చేయండి", "అర్థమైందా?", "సరేనా?", "ఇప్పుడే"],
}
FILLERS: dict[str, list[str]] = {
    "en": ["yes", "okay", "right", "hmm", "well", "actually"],
    "hi": ["हाँ", "ठीक है", "जी", "अच्छा", "सुनिए"],
    "hi-en": ["haan", "theek hai", "ji", "achha", "suniye"],
    "ta": ["ஆம்", "சரி", "சரிங்க", "பாருங்கள்"],
    "ta-en": ["aama", "sari", "saringa", "seri"],
    "te": ["అవును", "సరే", "చూడండి"],
}

LANG_WEIGHTS = {"en": 0.25, "hi": 0.20, "hi-en": 0.15, "ta": 0.20, "ta-en": 0.10, "te": 0.10}


def _gen(category: str, lang: str, rng: random.Random) -> str:
    frags = FRAGMENTS[category][lang]
    parts: list[str] = []
    if rng.random() < 0.3:
        parts.append(rng.choice(FILLERS[lang]))
    if rng.random() < 0.7:
        parts.append(rng.choice(OPENERS[lang]))
    if rng.random() < 0.5:
        parts.append(rng.choice(CONNECTORS[lang]))

    n_core = rng.randint(1, 3)
    chosen = rng.sample(frags, k=min(n_core, len(frags)))
    for f in chosen:
        parts.append(f)

    if rng.random() < 0.5:
        parts.append(rng.choice(CLOSERS[lang]))
    return " ".join(parts)


def build_and_train(n_per_category: int = 500) -> None:
    rng = random.Random(42)
    rows: list[dict] = []
    for category in CATEGORIES:
        for lang, w in LANG_WEIGHTS.items():
            n = max(5, int(n_per_category * w))
            for _ in range(n):
                text = _gen(category, lang, rng)
                rows.append({"text": text, "label": category, "lang": lang})

    print(f"Generated {len(rows)} multilingual samples across {len(CATEGORIES)} categories.")

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    texts = [r["text"] for r in rows]
    labels = [r["label"] for r in rows]

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    pipeline = Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        ("word", TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(1, 2), analyzer="word")),
                        ("char", TfidfVectorizer(sublinear_tf=True, min_df=2, ngram_range=(3, 6), analyzer="char_wb")),
                    ]
                ),
            ),
            (
                "clf",
                LogisticRegression(C=5.0, max_iter=1500, solver="lbfgs", random_state=42),
            ),
        ]
    )

    print("Fitting multilingual TF-IDF + LogisticRegression pipeline...")
    pipeline.fit(X_train, y_train)

    pred = pipeline.predict(X_test)
    acc = (pred == np.asarray(y_test)).mean()
    print(f"\nHeld-out Accuracy: {acc * 100:.2f}%\n")
    print(classification_report(y_test, pred))

    OUT_MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, OUT_MODEL)
    print(f"Model saved to {OUT_MODEL}")


if __name__ == "__main__":
    build_and_train()
