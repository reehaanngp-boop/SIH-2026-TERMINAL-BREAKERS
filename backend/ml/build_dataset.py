"""Build a synthetic multilingual scam-script training dataset.

Generates thousands of transcripts by combining *fragments* drawn from
publicly documented I4C / RBI / cybercrime.gov.in scam advisories. Six classes
are produced; the ``benign`` class covers ordinary non-scam calls.

Languages: English (en), Hindi in Devanagari (hi), and Hinglish / romanised
Hindi (hi-en), reflecting the code-mixed reality of real scam calls.

Output: ``data/datasets/scam_dataset.jsonl`` and ``scam_dataset.csv``.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_JSONL = PROJECT_ROOT / "data" / "datasets" / "scam_dataset.jsonl"
OUT_CSV = PROJECT_ROOT / "data" / "datasets" / "scam_dataset.csv"

CATEGORIES = ["digital_arrest", "fake_courier", "otp_phishing", "kin_emergency", "other_fraud", "benign", "neutral"]

# Each category has core scam fragments per language. Randomly sampled fragments
# are combined so the dataset sees combinatorial (not templated-identical) text.
FRAGMENTS: dict[str, dict[str, list[str]]] = {
    "digital_arrest": {
        "en": [
            "this is the CBI investigating your case, you are under arrest",
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
            "the court has ordered you to pay the penalty today itself",
            "do not tell your family about this investigation, it is confidential",
            "your name is in the Enforcement Directorate's money laundering investigation",
            "we have a warrant for your arrest signed by the judge",
            "transfer the amount to the nodal officer's account for verification",
            "this is a sensitive investigation, keep it secret and stay available",
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
    },
    "fake_courier": {
        "en": [
            "your international courier parcel has been stopped at customs",
            "a parcel sent in your name contains drugs and foreign currency",
            "the narcotics control bureau has opened a case about your parcel",
            "you need to pay the customs clearance fee to release the parcel",
            "the parcel has been linked to money laundering and drugs",
            "we have a CCTV image of your Aadhaar being used to book this courier",
            "pay the courier security deposit to avoid legal action",
            "the RBI and customs have flagged your parcel for illegal items",
            "your parcel contained gold and you have not declared it",
            "clear the parcel by paying the clearance charges today",
            "the courier company has handed your file to the cyber cell",
            "this parcel booking is registered under your Aadhaar number",
            "you must pay the insurance fee to release the package",
            "the police will arrest you for drug trafficking if you do not clear the parcel",
            "pay the refundable parcel fee and the case will be closed",
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
    },
    "otp_phishing": {
        "en": [
            "your bank account has been blocked due to suspicious activity",
            "your KYC is incomplete and your account will be frozen today",
            "your SIM card will be deactivated if you do not update now",
            "share the OTP you received to verify your account",
            "your net banking has been disabled for security",
            "send the card number and the OTP to unblock your account",
            "you have won cashback, share the OTP to credit the amount",
            "your UPI account has a limit, share the OTP to increase it",
            "this is the bank's security department, we need the OTP for verification",
            "your ATM card has been blocked, send the OTP to reactivate it",
            "the electricity bill is overdue, share the OTP to clear the pending amount",
            "your wallet balance will be transferred to another user unless you share the OTP",
            "the order you placed needs a confirmation OTP to be delivered",
            "we noticed fraud on your account, share the OTP to secure it immediately",
            "your account has an unused reward, share the OTP to redeem it",
        ],
        "hi": [
            "संदिग्ध गतिविधि के कारण आपका बैंक खाता ब्लॉक कर दिया गया है",
            "आपका केवाईसी अधूरा है, आज खाता फ्रीज हो जाएगा",
            "अपडेट नहीं किया तो आपका सिम कार्ड बंद हो जाएगा",
            "खाता सत्यापन के लिए प्राप्त ओटीपी साझा करें",
            "सुरक्षा के लिए आपका नेट बैंकिंग बंद कर दिया गया है",
            "खाता अनब्लॉक करने के लिए कार्ड नंबर और ओटीपी भेजें",
            "आपको कैशबैक मिला है, राशि जमा करने के लिए ओटीपी साझा करें",
            "आपके यूपीआई खाते की सीमा बढ़ाने के लिए ओटीपी साझा करें",
            "हम बैंक की सुरक्षा शाखा से बोल रहे हैं, ओटीपी की आवश्यकता है",
            "आपका एटीएम कार्ड ब्लॉक है, फिर से चालू करने के लिए ओटीपी भेजें",
            "बिजली का बिल बकाया है, राशि चुकाने के लिए ओटीपी साझा करें",
            "ओटीपी नहीं साझा किया तो वॉलेट राशि दूसरे उपयोगकर्ता को जाएगी",
            "आपके ऑर्डर की डिलीवरी के लिए ओटीपी की पुष्टि आवश्यक है",
            "आपके खाते में धोखाधड़ी हुई है, सुरक्षा के लिए तुरंत ओटीपी साझा करें",
            "आपके खाते पर अनुपयोगी रिवार्ड है, भुनाने के लिए ओटीपी साझा करें",
        ],
        "hi-en": [
            "suspicious activity ki wajah se aapka bank account block ho gaya hai",
            "aapka kyc adhura hai, aaj account freeze ho jayega",
            "update nahi kiya to aapka sim card band ho jayega",
            "account verify karne ke liye jo otp aaya hai woh share karo",
            "security ke liye aapka net banking band kar diya gaya hai",
            "account unblock karne ke liye card number aur otp bhejo",
            "aapko cashback mila hai, credit karne ke liye otp share karo",
            "upi account ki limit badhane ke liye otp share karo",
            "hum bank ki security branch se bol rahe hain, otp chahiye",
            "aapka atm card block hai, reactivate karne ke liye otp bhejo",
            "bijli ka bill baaki hai, amount clear karne ke liye otp share karo",
            "otp nahi diya to wallet amount doosre user ko transfer ho jayegi",
            "order deliver karne ke liye confirmation otp chahiye",
            "aapke account me fraud hua hai, secure karne ke liye turant otp share karo",
            "account pe reward hai, redeem karne ke liye otp share karo",
        ],
    },
    "kin_emergency": {
        "en": [
            "mama, it's me, I am in trouble, please help",
            "I met with an accident and the hospital is asking for money",
            "I have been arrested in this city, the police want bail money",
            "please transfer the money urgently, I will return it tonight",
            "do not tell mom and dad about this, they will get upset",
            "a friend of mine needs money immediately for my release",
            "I am stuck in this city with no money, send me the amount now",
            "the person who saved me is here, give him the cash",
            "my phone has been damaged, I am calling from a friend's number",
            "I booked a course, the fees must be paid by today",
            "there has been an emergency with my documents, pay the agent today",
            "the courier office is holding my passport, send the money to release it",
            "my account is frozen, send the amount to this account for now",
            "bhai, I am in trouble, transfer the money to this number",
            "the lawyer says if we pay today the case will close",
        ],
        "hi": [
            "मम्मी यह मैं हूँ, मैं मुसीबत में हूँ, मेरी मदद करो",
            "मेरा एक्सीडेंट हो गया है, अस्पताल पैसे मांग रहा है",
            "मुझे इस शहर में गिरफ्तार कर लिया गया है, पुलिस ज़मानत के पैसे मांग रही है",
            "तुरंत पैसे ट्रांसफर कर दो, आज रात ही लौटा दूँगा",
            "मम्मी पापा को मत बताना, वे परेशान हो जाएंगे",
            "मेरी रिहाई के लिए मेरे दोस्त को तुरंत पैसे दे दो",
            "मैं बिना पैसे के इस शहर में फंस गया हूँ, अभी पैसे भेजो",
            "जो मुझे बचाया है वह यहीं है, उसे पैसे दे दो",
            "मेरा फोन खराब हो गया है, दोस्त के नंबर से बोल रहा हूँ",
            "मैंने कोर्स लिया है, फीस आज जमा करनी है",
            "मेरे दस्तावेजों में आपात स्थिति है, आज ही एजेंट को पैसे दो",
            "कूरियर ऑफिस मेरा पासपोर्ट रोके हुए है, पैसे भेजो",
            "मेरा खाता फ्रीज है, पैसे इस खाते में भेज दो",
            "भाई मैं मुसीबत में हूँ, इस नंबर पर पैसे ट्रांसफर कर दो",
            "वकील कहता है आज भुगतान किया तो मामला बंद हो जाएगा",
        ],
        "hi-en": [
            "mummy yeh main hoon, main museebat me hoon, meri madad karo",
            "mera accident ho gaya hai, hospital paise mang raha hai",
            "mujhe is sheher me arrest kar liya gaya hai, police bail ke paise mang rahi hai",
            "turant paise transfer kar do, aaj raat hi wapas kar dunga",
            "mummy papa ko mat batana, woh pareshan ho jayenge",
            "meri rihaai ke liye mere dost ko turant paise de do",
            "main bina paise ke is sheher me phas gaya hoon, abhi paise bhejo",
            "jo mujhe bachaya hai woh yahin hai, use paise de do",
            "mera phone kharab ho gaya hai, dost ke number se bol raha hoon",
            "maine course liya hai, fees aaj jama karni hai",
            "mere documents me emergency hai, aaj hi agent ko paise do",
            "courier office mera passport roke hua hai, paise bhejo",
            "mera account freeze hai, paise is account me bhej do",
            "bhai main museebat me hoon, is number pe paise transfer kar do",
            "lawyer kehta hai aaj bhugtaan kiya to case band ho jayega",
        ],
    },
    "other_fraud": {
        "en": [
            "congratulations, you have won the mega lottery of one crore rupees",
            "your number has been selected for a reward, pay the processing fee to receive it",
            "invest in our trading group and double your money in one week",
            "we have a guaranteed job offer, pay the registration fee today",
            "do small tasks on our app and earn five thousand rupees daily",
            "you have a pending refund from the government, share the OTP to release it",
            "your mutual fund has grown, withdraw it by paying the service fee",
            "this business opportunity will make you rich, join before midnight",
            "the tax department has a refund for you, verify with the OTP",
            "we will send you free samples, pay only the delivery charge",
            "your internet banking reward is ready, redeem with a small fee",
            "earn by liking videos, the joining fee is refundable",
            "the share market tips are guaranteed, pay the subscription today",
            "your old insurance policy has matured, claim it by paying the document fee",
            "you won a shopping voucher, pay the courier charge to receive it",
        ],
        "hi": [
            "बधाई हो, आपने एक करोड़ रुपये की मेगा लॉटरी जीती है",
            "आपका नंबर रिवार्ड के लिए चुना गया है, पाने के लिए प्रोसेसिंग शुल्क जमा करें",
            "हमारे ट्रेडिंग ग्रुप में निवेश करें और एक हफ्ते में पैसे दोगुने करें",
            "हमारे पास गारंटीड नौकरी है, आज ही पंजीकरण शुल्क जमा करें",
            "हमारे ऐप पर छोटे कार्य करें और रोज़ पाँच हज़ार कमाएं",
            "सरकार की ओर से आपका रिफंड बकाया है, ओटीपी साझा करें",
            "आपका म्यूचुअल फंड बढ़ गया है, सेवा शुल्क देकर निकालें",
            "यह कारोबार का अवसर आपको अमीर बना देगा, आज ही जुड़ें",
            "कर विभाग के पास आपका रिफंड है, ओटीपी से पुष्टि करें",
            "हम आपको फ्री सैंपल भेजेंगे, केवल डिलीवरी शुल्क दें",
            "आपका इंटरनेट बैंकिंग रिवार्ड तैयार है, छोटे शुल्क पर भुनाएं",
            "वीडियो लाइक करके कमाएं, जॉइनिंग शुल्क वापस मिलता है",
            "शेयर बाजार की टिप्स गारंटीड हैं, आज ही सब्सक्रिप्शन दें",
            "आपकी पुरानी बीमा पॉलिसी मैच्योर हुई है, दस्तावेज शुल्क देकर दावा करें",
            "आपने शॉपिंग वाउचर जीता है, कूरियर शुल्क देकर प्राप्त करें",
        ],
        "hi-en": [
            "badhai ho, aapne ek crore rupaye ki mega lottery jeeti hai",
            "aapka number reward ke liye chuna gaya hai, processing fee jama karein",
            "hamare trading group me invest karein aur ek hafte me paise double karein",
            "hamare paas guaranteed naukri hai, aaj hi registration fee jama karo",
            "hamare app pe chhote tasks karo aur roz paanch hazaar kamao",
            "sarkar ki taraf se aapka refund baaki hai, otp share karo",
            "aapka mutual fund badh gaya hai, service fee dekar nikaalo",
            "yeh business opportunity aapko ameer bana degi, aaj hi judo",
            "tax department ke paas aapka refund hai, otp se confirm karo",
            "hum aapko free samples bhejenge, sirf delivery charge do",
            "aapka internet banking reward taiyaar hai, chhoti fee pe bhumao",
            "video like karke kamao, joining fee wapas milti hai",
            "share market ki tips guaranteed hain, aaj hi subscription do",
            "aapki purani insurance policy mature hui hai, document fee dekar claim karo",
            "aapne shopping voucher jeeta hai, courier charge dekar pao",
        ],
    },
    "benign": {
        "en": [
            "hi, this is the restaurant calling to confirm your order",
            "your food delivery is at the gate, please collect it",
            "this is the school, calling about your child's parent-teacher meeting",
            "your doctor has scheduled your appointment for tomorrow at ten",
            "we are confirming your flight for Sunday morning",
            "the electrician has arrived, is this a good time?",
            "just checking in to see how you are doing",
            "the parcel you ordered has arrived at the pickup point",
            "your bank sent a notification about a new branch near you",
            "we would like to invite you to our store's opening",
            "your subscription has been renewed for the next month",
            "hi dad, I will reach home by evening, no need to worry",
            "the meeting has been moved to three pm today",
            "your car is ready for the service pickup tomorrow",
            "let's meet for lunch this weekend",
            "your insurance premium payment was successful this month",
            "the documents you asked for have been signed and emailed",
            "this is the courier company, your parcel will be delivered tomorrow morning",
            "we received your payment of five hundred rupees, thank you for the order",
            "your parcel has reached the delivery hub and will arrive today",
            "this is the bank calling to confirm you received our new card",
            "your electricity bill for this month has been paid successfully",
            "the airline has rescheduled your flight, please check your email",
            "please carry your ID card to collect the courier at the pickup point",
            "your subscription renewal is confirmed and the receipt has been emailed",
            "we are calling to update your contact details on the account",
            "the shop will deliver your order today before six",
            "the restaurant confirms your order of two burgers and a drink",
        ],
        "hi": [
            "नमस्ते, आपके ऑर्डर की पुष्टि के लिए रेस्तरां से बोल रहे हैं",
            "आपका फूड डिलीवरी गेट पर पहुंच गया है, ले लीजिए",
            "यह स्कूल से बोल रहे हैं, अभिभावक बैठक के बारे में",
            "आपका डॉक्टर कल सुबह दस बजे अपॉइंटमेंट ले रहा है",
            "हम रविवार सुबह की आपकी फ्लाइट की पुष्टि कर रहे हैं",
            "इलेक्ट्रीशियन आ गया है, क्या यह समय ठीक है?",
            "बस आपका हालचाल लेने के लिए बोल रहा था",
            "आपका पार्सल पिकअप पॉइंट पर आ गया है",
            "आपके बैंक की ओर से नई शाखा की सूचना है",
            "हम आपको अपने स्टोर के उद्घाटन में आमंत्रित करना चाहते हैं",
            "आपकी सदस्यता अगले महीने के लिए नवीनीकृत हो गई है",
            "पापा, मैं शाम तक घर पहुंच जाऊँगा, चिंता मत करो",
            "आज की बैठक दोपहर तीन बजे हो गई है",
            "कल आपकी कार सर्विस के लिए तैयार रहेगी",
            "इस हफ्ते दोपहर के खाने पर मिलते हैं",
            "आपका बीमा प्रीमियम इस महीने सफलतापूर्वक जमा हो गया",
            "आपके मांगे गए दस्तावेज साइन कर ईमेल कर दिए गए हैं",
            "यह कूरियर कंपनी से बोल रहे हैं, आपका पार्सल कल सुबह डिलीवर होगा",
            "आपका पाँच सौ रुपये का भुगतान प्राप्त हो गया है, ऑर्डर के लिए धन्यवाद",
            "आपका पार्सल डिलीवरी हब पहुँच गया है, आज आ जाएगा",
            "हम आपके नए कार्ड की पुष्टि के लिए बैंक से बोल रहे हैं",
            "इस महीने का बिजली बिल सफलतापूर्वक जमा हो गया है",
            "पार्सल लेने के लिए पिकअप पॉइंट पर पहचान पत्र साथ ले जाएँ",
            "आपकी सदस्यता नवीनीकरण की पुष्टि हो गई है, रसीद ईमेल हुई है",
            "हम खाते में संपर्क विवरण अपडेट करने के लिए बोल रहे हैं",
            "दुकान आज शाम छह बजे से पहले आपका ऑर्डर पहुँचाएगी",
            "रेस्तरां आपके दो बर्गर और एक ड्रिंक के ऑर्डर की पुष्टि करता है",
        ],
        "hi-en": [
            "namaste, aapke order ki pushti ke liye restaurant se bol rahe hain",
            "aapka food delivery gate pe aa gaya hai, le lijiye",
            "yeh school se bol rahe hain, parent teacher meeting ke baare me",
            "aapka doctor kal subah das baje appointment le raha hai",
            "hum raviwaar subah ki aapki flight confirm kar rahe hain",
            "electrician aa gaya hai, kya yeh time theek hai?",
            "bas aapka haal-chaal lene ke liye bol raha tha",
            "aapka parcel pickup point pe aa gaya hai",
            "aapke bank ki taraf se nayi branch ki suchna hai",
            "hum aapko apne store ke udghatan par invite karna chahte hain",
            "aapki membership agle mahine ke liye renew ho gayi hai",
            "papa, main shaam tak ghar pahunch jaunga, chinta mat karo",
            "aaj ki meeting dopahar teen baje ho gayi hai",
            "kal aapki car service ke liye taiyaar rahegi",
            "is hafte lunch par milte hain",
            "aapka insurance premium is mahine successfully jama ho gaya",
            "aapke maange gaye documents sign karke email kar diye",
            "yeh courier company se bol rahe hain, aapka parcel kal subah deliver hoga",
            "aapka paanch sau rupaye ka payment mil gaya hai, order ke liye dhanyavaad",
            "aapka parcel delivery hub pahunch gaya hai, aaj aa jayega",
            "hum aapke naye card ki pushti ke liye bank se bol rahe hain",
            "is mahine ka bijli bill successfully jama ho gaya hai",
            "parcel lene ke liye pickup point par pehchaan patra saath le jayen",
            "aapki membership renewal confirm ho gayi hai, receipt email hui hai",
            "hum account me contact details update karne ke liye bol rahe hain",
            "dukaan aaj shaam chhah baje se pehle aapka order pahunchaayegi",
            "restaurant aapke do burger aur ek drink ke order ki pushti karta hai",
        ],
    },
    "neutral": {
        "en": [
            "hello, sorry I think I dialed the wrong number",
            "can you hear me clearly, the network seems patchy",
            "what is the weather like there today",
            "are you free this evening to catch up",
            "let me check my calendar and call you back in ten minutes",
            "I will be at the office till six, you can reach me there",
            "could you please repeat that, I missed what you said",
            "the meeting got postponed, I will share the new time",
            "are you coming to the function on Saturday",
            "let me ask my wife and confirm with you tomorrow",
            "how is the family doing, everyone well at home",
            "I am stuck in traffic, will be there in half an hour",
            "have you heard from our mutual friend recently",
            "please send me the address by text message",
            "no problem, take your time, no rush at all",
        ],
        "hi": [
            "नमस्ते, क्षमा करें, मुझे लगता है गलत नंबर लग गया",
            "क्या आप मेरी बात सुन पा रहे हैं, नेटवर्क थोड़ा कमज़ोर है",
            "वहाँ आज मौसम कैसा है",
            "क्या आप आज शाम खाली हैं",
            "मैं अपना कैलेंडर देखकर दस मिनट में आपको कॉल करता हूँ",
            "मैं शाम छह बजे तक ऑफिस में रहूँगा",
            "कृपया दोबारा बताइए, आपकी बात कट गई थी",
            "बैठक स्थगित हो गई है, नया समय बताऊँगा",
            "क्या आप शनिवार को समारोह में आ रहे हैं",
            "मैं पत्नी से पूछकर कल आपको बता दूँगा",
            "घर पर सब ठीक है, परिवार कैसा है",
            "मैं ट्रैफिक में फंसा हूँ, आधे घंटे में पहुँच जाऊँगा",
            "हमारे साझा मित्र के बारे में कुछ सुना?",
            "पता एसएमएस में भेज दीजिए",
            "कोई बात नहीं, आराम से, जल्दी नहीं है",
        ],
        "hi-en": [
            "namaste, sorry, lagta hai galat number laga",
            "kya aap meri baat sun paa rahe ho, network kamzor hai",
            "wahan aaj mausam kaisa hai",
            "kya aap aaj shaam khali ho",
            "main apna calendar dekh kar das minute me call karta hoon",
            "main shaam chhah baje tak office me rahunga",
            "kripya dobara bataiye, aapki baat kat gayi thi",
            "baithak stagit ho gayi hai, naya time bataunga",
            "kya aap shanivaar ko samaaroh me aa rahe ho",
            "main patni se pooch kar kal bata dunga",
            "ghar pe sab theek hai, parivaar kaisa hai",
            "main traffic me phansa hoon, aadhe ghante me pahunch jaunga",
            "hamare sajha mitra ke baare me kuch suna?",
            "pata sms me bhej dijiye",
            "koi baat nahi, aaram se, jaldi nahi hai",
        ],
    },
}

# Connectors / openers / closers that add realistic variety.
OPENERS: dict[str, list[str]] = {
    "en": ["hello", "good morning", "namaste", "good afternoon", "excuse me", "sir", "madam", "good evening"],
    "hi": ["नमस्ते", "सुप्रभात", "नमस्कार", "जी", "सुनिए", "माफ़ कीजिए", "साहब", "शुभ संध्या"],
    "hi-en": ["hello", "namaste", "ji", "suniye", "maaf kijiye", "sahab", "good morning", "namaskar"],
}
CONNECTORS: dict[str, list[str]] = {
    "en": ["and", "also", "but", "so", "because", "therefore", "now", "look", "listen"],
    "hi": ["और", "क्योंकि", "इसलिए", "लेकिन", "तो", "अब", "सुनिए", "देखिए"],
    "hi-en": ["aur", "kyunki", "isliye", "lekin", "to", "ab", "suniye", "dekhiye"],
}
CLOSERS: dict[str, list[str]] = {
    "en": ["do it immediately", "understand?", "ok?", "right now", "today itself", "do not delay"],
    "hi": ["तुरंत करें", "समझे?", "ठीक है?", "अभी", "आज ही", "देरी मत करें"],
    "hi-en": ["turant karo", "samjhe?", "theek hai?", "abhi", "aaj hi", "deri mat karo"],
}

# Natural conversational fillers — real transcripts are full of these, and the
# synthetic training set used to be too "clean" compared to actual ASR output.
FILLERS: dict[str, list[str]] = {
    "en": ["yes", "okay", "right", "hmm", "well", "actually", "you see", "I mean", "sure"],
    "hi": ["हाँ", "ठीक है", "जी", "अच्छा", "मतलब", "देखिए", "सुनिए", "हम्म", "वैसे"],
    "hi-en": ["haan", "theek hai", "ji", "achha", "matlab", "dekhiye", "suniye", "hmm", "waise"],
}

NAMES = ["Amit", "Priya", "Rahul", "Sunita", "Vikram", "Anjali", "Rajesh", "Meena", "Suresh", "Kavita", "Arjun", "Neha"]
CITIES = ["Mumbai", "Delhi", "Pune", "Bengaluru", "Chennai", "Jaipur", "Lucknow", "Kolkata", "Hyderabad", "Ahmedabad"]
AMOUNTS = ["five thousand", "ten thousand", "twenty thousand", "fifty thousand", "one lakh", "two lakh", "five lakh", "twelve thousand"]
LANG_WEIGHTS = {"en": 0.34, "hi": 0.33, "hi-en": 0.33}


def _pick(rng: random.Random, pool: list[str]) -> str:
    return rng.choice(pool)


def _gen(category: str, lang: str, rng: random.Random) -> str:
    """Generate one transcript for a category/language pair."""
    frags = FRAGMENTS[category][lang]
    parts: list[str] = []
    if rng.random() < 0.3:
        parts.append(_pick(rng, FILLERS[lang]))
    if rng.random() < 0.75:
        parts.append(_pick(rng, OPENERS[lang]))
    if rng.random() < 0.55:
        parts.append(_pick(rng, CONNECTORS[lang]))

    n_core = rng.randint(1, 3)
    chosen = rng.sample(frags, k=min(n_core, len(frags)))
    for i, f in enumerate(chosen):
        if rng.random() < 0.4 and category != "benign":
            parts.append(_pick(rng, CONNECTORS[lang]))
        parts.append(f)

    if rng.random() < 0.45:
        parts.append(_pick(rng, CLOSERS[lang]))
    return " ".join(parts)


def _noise(text: str, rng: random.Random) -> str:
    """Inject realistic references (names, amounts, cities) when sensible."""
    if rng.random() < 0.4:
        text = text.replace("the amount", _pick(rng, AMOUNTS))
    if rng.random() < 0.3:
        text = text + " my name is " + _pick(rng, NAMES)
    if rng.random() < 0.25:
        text = text + " from " + _pick(rng, CITIES)
    return text


def generate_dataset(n_per_category: int = 400, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    for category in CATEGORIES:
        for lang, w in LANG_WEIGHTS.items():
            n = int(n_per_category * w)
            for _ in range(n):
                text = _noise(_gen(category, lang, rng), rng)
                rows.append({"text": text, "label": category, "lang": lang})
    # Keep the dataset deterministic and balanced per category.
    rows = [r for r in rows if r["text"].strip()]
    return rows


def main(n_per_category: int = 400) -> None:
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_dataset(n_per_category=n_per_category)

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "lang"])
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter

    counts = Counter(r["label"] for r in rows)
    print(f"Wrote {len(rows)} rows -> {OUT_JSONL}")
    for cat, n in sorted(counts.items()):
        print(f"  {cat:18s} {n}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Build the synthetic scam-script dataset")
    ap.add_argument("--per-category", type=int, default=400)
    args = ap.parse_args()
    main(n_per_category=args.per_category)
