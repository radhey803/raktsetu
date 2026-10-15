/**
 * BloodGrid Multilingual Translation Dictionary
 * Human-curated medical terminology in English, Hindi, and Gujarati.
 * Strictly adheres to clinical accuracy without machine translation hallucinations.
 */

const TRANSLATIONS = {
    en: {
        navFind: "Find blood",
        navNetwork: "Network",
        navRadar: "Rare blood",
        navShortages: "Shortages",
        navAbout: "Architecture",
        liveSync: "Live sync",
        heroKicker: "CHARUSAT MCA Academic Project • 800 Marks Mini Project",
        heroTitle: "National Blood Availability & Shortage Intelligence",
        heroSub: "Direct ingestion from eRaktKosh (MoHFW, Govt. of India). Engineered with DuckDB, dbt Medallion Lakehouse architecture (Bronze → Silver → Gold), and append-only snapshot analytics across 4,680+ verified facilities.",
        filterLabel: "Filter by blood group & component",
        filterHint: "Select a group to verify real-time units",
        all: "All",
        univ: "Univ",
        platelets: "Platelets",
        plasma: "Plasma",
        stateLabel: "State / UT",
        allIndia: "All India (Nationwide)",
        districtLabel: "District",
        allDistricts: "All Districts",
        componentLabel: "Blood Component",
        prbc: "Packed Red Blood Cells (PRBC)",
        wholeBlood: "Whole Blood",
        ffp: "Fresh Frozen Plasma (FFP)",
        plateletConc: "Platelet Concentrate",
        sdp: "Single Donor Platelet (SDP)",
        rdp: "Random Donor Platelets (RDP)",
        cryo: "Cryoprecipitate",
        allComponents: "All Components",
        facilitySearchLabel: "Facility or Address",
        searchPlaceholder: "e.g. Civil Hospital, Red Cross Society...",
        searchBtn: "Search facilities",
        resetBtn: "Reset",
        kpiRegistered: "Registered facilities",
        kpiRegisteredSub: "Across 36 states & union territories",
        kpiFresh: "Verified fresh stock",
        kpiFreshSub: "Updated in past 24 hours",
        kpiStale: "Flagged for review",
        kpiStaleSub: "No updates recorded for >30 days",
        kpiReporting: "Facilities reporting today",
        kpiReportingSub: "Active nodes transmitting availability",
        chartTitle: "National facility distribution",
        chartSub: "Top states by active blood banks aggregated from Gold warehouse marts",
        chartNote: "Updated hourly via DuckDB pipeline",
        resultsHeading: "blood banks",
        sortedBy: "Sorted by data recency",
        gridView: "Grid view",
        mapView: "Live blood map",
        callHospital: "Call Hospital",
        directions: "Directions",
        viewTrend: "7-Day Trend",
        shareSos: "Share SOS Card",
        unitsAvailable: "units in stock",
        reliabilityScore: "Reliability",
        mandatoryNotice: "Data sourced from eRaktKosh (Ministry of Health & Family Welfare, Govt. of India). Academic project, not an official service. Always call the blood bank to confirm before travelling.",
        trendEmptyState: "Trend data builds up daily. First genuine lakehouse snapshot recorded today. Multi-day trajectory requires at least 2 consecutive daily scrapes.",
        sosTitle: "Emergency Blood Availability SOS Card",
        sosCopyBtn: "Copy SOS Message",
        sosWhatsAppBtn: "Share via WhatsApp",
        sosCopied: "SOS card copied to clipboard!"
    },
    hi: {
        navFind: "रक्त खोजें",
        navNetwork: "नेटवर्क",
        navRadar: "दुर्लभ रक्त",
        navShortages: "रक्त की कमी",
        navAbout: "वास्तुकला",
        liveSync: "लाइव सिंक",
        heroKicker: "चारुसैट एमसीए शैक्षणिक प्रोजेक्ट • 800 मार्क्स मिनी प्रोजेक्ट",
        heroTitle: "राष्ट्रीय रक्त उपलब्धता एवं कमी आसूचना",
        heroSub: "ई-रक्तकोश (स्वास्थ्य एवं परिवार कल्याण मंत्रालय, भारत सरकार) से सीधा संकलन। डकडीबी, डीबीटी मेडेलियन लेकहाउस आर्किटेक्चर द्वारा संचालित।",
        filterLabel: "रक्त समूह एवं घटक चुनें",
        filterHint: "वास्तविक समय की इकाइयों को सत्यापित करने के लिए समूह चुनें",
        all: "सभी",
        univ: "सर्वदाता",
        platelets: "प्लेटलेट्स",
        plasma: "प्लाज्मा",
        stateLabel: "राज्य / केंद्र शासित प्रदेश",
        allIndia: "अखिल भारतीय (राष्ट्रीय)",
        districtLabel: "ज़िला",
        allDistricts: "सभी ज़िले",
        componentLabel: "रक्त घटक",
        prbc: "पैक्ड रेड ब्लड सेल्स (PRBC)",
        wholeBlood: "होल ब्लड (पूर्ण रक्त)",
        ffp: "फ्रेश फ्रोजन प्लाज्मा (FFP)",
        plateletConc: "प्लेटलेट कॉन्संट्रेट",
        sdp: "सिंगल डोनर प्लेटलेट (SDP)",
        rdp: "रैंडम डोनर प्लेटलेट्स (RDP)",
        cryo: "क्रायोप्रेसिपिटेट",
        allComponents: "सभी घटक",
        facilitySearchLabel: "अस्पताल या पता खोजें",
        searchPlaceholder: "उदा. सिविल अस्पताल, रेड क्रॉस सोसाइटी...",
        searchBtn: "ब्लड बैंक खोजें",
        resetBtn: "रीसेट करें",
        kpiRegistered: "पंजीकृत ब्लड बैंक",
        kpiRegisteredSub: "36 राज्यों और केंद्र शासित प्रदेशों में",
        kpiFresh: "ताज़ा सत्यापित स्टॉक",
        kpiFreshSub: "पिछले 24 घंटों में अद्यतन",
        kpiStale: "समीक्षा हेतु चिह्नित",
        kpiStaleSub: ">30 दिनों से कोई अपडेट नहीं",
        kpiReporting: "आज रिपोर्ट करने वाले बैंक",
        kpiReportingSub: "सक्रिय ब्लड बैंक केंद्र",
        chartTitle: "राष्ट्रीय ब्लड बैंक वितरण",
        chartSub: "गोल्ड डेटा वेयरहाउस से शीर्ष राज्यों का संकलन",
        chartNote: "डकडीबी पाइपलाइन द्वारा प्रति घंटा अद्यतन",
        resultsHeading: "ब्लड बैंक उपलब्ध",
        sortedBy: "डेटा नवीनता के अनुसार क्रमित",
        gridView: "ग्रिड दृश्य",
        mapView: "लाइव नक्शा",
        callHospital: "अस्पताल को कॉल करें",
        directions: "दिशा-निर्देश",
        viewTrend: "7-दिवसीय रुझान",
        shareSos: "SOS कार्ड साझा करें",
        unitsAvailable: "यूनिट उपलब्ध",
        reliabilityScore: "विश्वसनीयता स्कोर",
        mandatoryNotice: "डेटा ई-रक्तकोश (स्वास्थ्य एवं परिवार कल्याण मंत्रालय, भारत सरकार) से प्राप्त। यह कोई आधिकारिक सेवा नहीं है। यात्रा करने से पहले उपलब्धता की पुष्टि हेतु हमेशा ब्लड बैंक को फ़ोन करें।",
        trendEmptyState: "रुझान डेटा प्रतिदिन जमा होता है। प्रक्षेपवक्र चार्ट प्रदर्शित करने के लिए कम से कम 2 लगातार दैनिक स्नैपशॉट की आवश्यकता होती है।",
        sosTitle: "आपातकालीन रक्त उपलब्धता SOS कार्ड",
        sosCopyBtn: "SOS संदेश कॉपी करें",
        sosWhatsAppBtn: "व्हाट्सएप पर साझा करें",
        sosCopied: "SOS संदेश क्लिपबोर्ड पर कॉपी हो गया!"
    },
    gu: {
        navFind: "રક્ત શોધો",
        navNetwork: "નેટવર્ક",
        navRadar: "દુર્લભ રક્ત",
        navShortages: "અછત રડાર",
        navAbout: "આર્કિટેક્ચર",
        liveSync: "લાઈવ સિંક",
        heroKicker: "ચારુસેટ એમસીએ શૈક્ષણિક પ્રોજેક્ટ • 800 માર્ક્સ મિની પ્રોજેક્ટ",
        heroTitle: "રાષ્ટ્રીય રક્ત ઉપલબ્ધતા અને અછત ઇન્ટેલિજન્સ",
        heroSub: "ઇ-રક્તકોશ (આરોગ્ય અને પરિવાર કલ્યાણ મંત્રાલય, ભારત સરકાર) માંથી સીધું સંકલન. ડકડબી અને ડીબીટી મેડેલિયન લેકહાઉસ દ્વારા સંચાલિત.",
        filterLabel: "બ્લડ ગ્રુપ અને ઘટક પસંદ કરો",
        filterHint: "રીઅલ-ટાઇમ યુનિટ્સ ચકાસવા માટે બ્લડ ગ્રૂપ પસંદ કરો",
        all: "બધા",
        univ: "સર્વદાતા",
        platelets: "પ્લેટલેટ્સ",
        plasma: "પ્લાઝ્મા",
        stateLabel: "રાજ્ય",
        allIndia: "સમગ્ર ભારત (રાષ્ટ્રીય)",
        districtLabel: "જિલ્લો",
        allDistricts: "બધા જિલ્લાઓ",
        componentLabel: "બ્લડ કમ્પોનન્ટ",
        prbc: "પેક્ડ રેડ બ્લડ સેલ્સ (PRBC)",
        wholeBlood: "હોલ બ્લડ (સંપૂર્ણ રક્ત)",
        ffp: "ફ્રેશ ફ્રોઝન પ્લાઝ્મા (FFP)",
        plateletConc: "પ્લેટલેટ કોન્સન્ટ્રેટ",
        sdp: "સિંગલ ડોનર પ્લેટલેટ (SDP)",
        rdp: "રેન્ડમ ડોનર પ્લેટલેટ્સ (RDP)",
        cryo: "ક્રાયોપ્રેસિપિટેટ",
        allComponents: "બધા ઘટકો",
        facilitySearchLabel: "હોસ્પિટલ અથવા સરનામું શોધો",
        searchPlaceholder: "દા.ત. સિવિલ હોસ્પિટલ, રેડ ક્રોસ સોસાયટી...",
        searchBtn: "બ્લડ બેંક શોધો",
        resetBtn: "રીસેટ કરો",
        kpiRegistered: "નોંધાયેલ બ્લડ બેંકો",
        kpiRegisteredSub: "36 રાજ્યો અને કેન્દ્રશાસિત પ્રદેશોમાં",
        kpiFresh: "તાજું ચકાસાયેલ સ્ટોક",
        kpiFreshSub: "છેલ્લા 24 કલાકમાં અપડેટ થયેલ",
        kpiStale: "ચકાસણી માટે ચિહ્નિત",
        kpiStaleSub: ">30 દિવસથી કોઈ અપડેટ નથી",
        kpiReporting: "આજે રિપોર્ટ કરતી બેંકો",
        kpiReportingSub: "સક્રિય બ્લડ બેંક કેન્દ્રો",
        chartTitle: "રાષ્ટ્રીય બ્લડ બેંક વિતરણ",
        chartSub: "ગોલ્ડ ડેટા વેરહાઉસમાંથી મુખ્ય રાજ્યોનું સંકલન",
        chartNote: "ડકડીબી પાઇપલાઇન દ્વારા કલાકે અપડેટ",
        resultsHeading: "બ્લડ બેંકો ઉપલબ્ધ",
        sortedBy: "ડેટા તાજગી અનુસાર ક્રમબદ્ધ",
        gridView: "ગ્રીડ વ્યૂ",
        mapView: "લાઈવ નકશો",
        callHospital: "હોસ્પિટલ પર કૉલ કરો",
        directions: "દિશા-નિર્દેશ",
        viewTrend: "7-દિવસનો ટ્રેન્ડ",
        shareSos: "SOS કાર્ડ શેર કરો",
        unitsAvailable: "યુનિટ ઉપલબ્ધ",
        reliabilityScore: "વિશ્વસનીયતા સ્કોર",
        mandatoryNotice: "ડેટા ઈ-રક્તકોષ (સ્વાસ્થ્ય અને પરિવાર કલ્યાણ મંત્રાલય, ભારત સરકાર) માંથી મેળવેલ છે. આ કોઈ સત્તાવાર સેવા નથી. મુસાફરી કરતા પહેલા પુષ્ટિ માટે હંમેશા બ્લડ બેંક પર કૉલ કરો.",
        trendEmptyState: "ટ્રેન્ડ ડેટા દરરોજ એકત્રિત થાય છે. ટ્રેજેક્ટરી ચાર્ટ પ્રદર્શિત કરવા માટે ઓછામાં ઓછા 2 સતત દૈનિક સ્નેપશોટ જરૂરી છે.",
        sosTitle: "ઇમરજન્સી બ્લડ ઉપલબ્ધતા SOS કાર્ડ",
        sosCopyBtn: "SOS સંદેશ કૉપિ કરો",
        sosCopied: "SOS સંદેશ ક્લિપબોર્ડ પર કૉપિ થયો!"
    }
};

let currentLang = localStorage.getItem("bloodgrid_lang") || "en";

function setLanguage(lang) {
    if (!TRANSLATIONS[lang]) return;
    currentLang = lang;
    localStorage.setItem("bloodgrid_lang", lang);
    applyTranslations();
}

function applyTranslations() {
    const t = TRANSLATIONS[currentLang];
    if (!t) return;

    // Translate all elements with data-i18n attribute
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (t[key]) {
            el.textContent = t[key];
        }
    });

    // Translate placeholders
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        const key = el.getAttribute("data-i18n-placeholder");
        if (t[key]) {
            el.placeholder = t[key];
        }
    });

    // Update lang selector UI state
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.lang === currentLang);
    });
}
