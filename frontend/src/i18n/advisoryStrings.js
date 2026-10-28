/**
 * Citizen Advisory Layer — trilingual string packs (EN / HI / BN).
 *
 * Public-facing copy only. Road names stay transliterated (as they appear on
 * city signage) across all languages. Add languages by appending a pack and
 * registering its code in SUPPORTED.
 */

export const SUPPORTED = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'bn', label: 'বাংলা' },
];

const PACKS = {
  en: {
    brand: 'Corridor Alerts · Kolkata',
    tagline: 'Know before the barricade goes up.',
    updated: 'Updated live from the traffic control room',
    statusActive: 'Protected movement in progress',
    statusActiveSub: 'Rolling holds of ~2–3 minutes per stretch — not a full freeze.',
    statusClear: 'No active corridor restrictions',
    statusClearSub: 'Normal traffic across all city corridors.',
    statusDone: 'Movement completed — corridor released',
    statusDoneSub: 'Traffic returning to normal flow.',
    startDemo: 'Play a demo movement',
    freezeTitle: 'Where holds are expected',
    freezeZone: 'Stretch',
    freezeWindow: 'Hold window',
    freezeMinutes: (m) => `~${m} min`,
    alternate: 'Use instead',
    holdNow: 'Holding now',
    passed: 'Cleared',
    why: 'Why so short?',
    whyBody:
      'Closures are timed to the convoy’s live position (60–180 s ahead) using traffic forecasting — the corridor freezes only while the movement actually passes.',
    subscribeTitle: 'Get alerts on your phone',
    subscribeSub: 'SMS / WhatsApp, free, in your language.',
    phoneLabel: 'Mobile number',
    phonePlaceholder: '10-digit mobile',
    languageLabel: 'Alert language',
    subscribeBtn: 'Subscribe',
    demoBadge: 'Demo preview — no real SMS/WhatsApp is sent',
    previewTitle: 'You would receive:',
    subscribed: 'Subscribed (demo)',
    emergencyTitle: 'Driving an ambulance or fire vehicle?',
    emergencyBody:
      'Request a green-corridor window through the active movement — the control room answers in seconds.',
    emergencyCta: 'Request green corridor',
    backToOps: 'Operator console',
    footerNote:
      'Illustrative public advisory built on the VVIP Corridor Orchestration prototype. Alternate routes are indicative.',

    // ── Green-corridor driver flow (108) ──────────────────────────
    driverTitle: 'Green Corridor — 108 driver',
    driverSub: 'One tap. The control room answers in seconds.',
    driverBack: 'Citizen alerts',
    noMovement: 'No active corridor',
    noMovementSub: 'No protected movement right now — drive normally. Start the demo movement from the citizen page to try this flow.',
    atStretch: 'You are at',
    urgency: 'Patient urgency',
    urgCardiac: 'Cardiac',
    urgTrauma: 'Trauma',
    urgStroke: 'Stroke',
    urgOther: 'Other emergency',
    requestBtn: 'Request corridor window',
    evaluating: 'Evaluating corridor gap…',
    proposalTitle: 'Window proposed by the platform',
    convoyReachesIn: 'Convoy reaches your stretch in',
    crossBefore: 'Cross before',
    officerLabel: 'Duty officer (demo)',
    approveBtn: 'Approve · open window',
    deferBtn: 'Defer',
    windowOpen: 'WINDOW OPEN — CROSS NOW',
    windowClosesIn: 'Window closes in',
    minutesReturned: 'minutes returned to the golden hour',
    holdPosition: 'Hold position — next window at',
    baselineNote: 'Without a request channel: documented ambulance holds behind convoy corridors run 5–20 minutes.',
    openDriverView: 'Open the 108 driver view',
    demoNote: 'Demo flow driven by the scripted simulation — no real dispatch, no real patient data.',
  },

  hi: {
    brand: 'कॉरिडोर अलर्ट · कोलकाता',
    tagline: 'बैरिकेड लगने से पहले ही जानें।',
    updated: 'ट्रैफ़िक कंट्रोल रूम से सीधे अपडेट',
    statusActive: 'सुरक्षित वाहन काफ़िला चल रहा है',
    statusActiveSub: 'हर हिस्से पर ~2–3 मिनट के छोटे रोक — पूरी सड़क बंद नहीं।',
    statusClear: 'इस समय कोई सड़क प्रतिबंध नहीं',
    statusClearSub: 'शहर के सभी कॉरिडोर पर सामान्य यातायात।',
    statusDone: 'काफ़िला पार — कॉरिडोर खुल गया',
    statusDoneSub: 'यातायात सामान्य हो रहा है।',
    startDemo: 'डेमो काफ़िला चलाएँ',
    freezeTitle: 'कहाँ रोक संभावित है',
    freezeZone: 'सड़क हिस्सा',
    freezeWindow: 'रोक का समय',
    freezeMinutes: (m) => `~${m} मिनट`,
    alternate: 'इसके बदले चलें',
    holdNow: 'अभी रुका हुआ',
    passed: 'खुल गया',
    why: 'इतना छोटा रोक क्यों?',
    whyBody:
      'रोक काफ़िले की लाइव स्थिति (60–180 सेकंड पहले) और ट्रैफ़िक पूर्वानुमान से तय होती है — सड़क सिर्फ़ तब बंद रहती है जब काफ़िला सच में पास हो।',
    subscribeTitle: 'अपने फ़ोन पर अलर्ट पाएँ',
    subscribeSub: 'SMS / WhatsApp, निःशुल्क, आपकी भाषा में।',
    phoneLabel: 'मोबाइल नंबर',
    phonePlaceholder: '10 अंकों का नंबर',
    languageLabel: 'अलर्ट की भाषा',
    subscribeBtn: 'सब्सक्राइब करें',
    demoBadge: 'डेमो पूर्वावलोकन — कोई असली SMS/WhatsApp नहीं भेजा जाता',
    previewTitle: 'आपको मिलेगा:',
    subscribed: 'सब्सक्राइब हुआ (डेमो)',
    emergencyTitle: 'एम्बुलेंस या फ़ायर वाहन चला रहे हैं?',
    emergencyBody:
      'चालू काफ़िले से ग्रीन-कॉरिडोर समय माँगें — कंट्रोल रूम सेकंडों में जवाब देता है।',
    emergencyCta: 'ग्रीन कॉरिडोर का अनुरोध',
    backToOps: 'ऑपरेटर कंसोल',
    footerNote:
      'VVIP कॉरिडोर प्रोटोटाइप पर बना नमूना सूचना पटल। वैकल्पिक मार्ग सांकेतिक हैं।',

    // ── Green-corridor driver flow (108) ──────────────────────────
    driverTitle: 'ग्रीन कॉरिडोर — 108 ड्राइवर',
    driverSub: 'एक टैप। कंट्रोल रूम सेकंडों में जवाब देता है।',
    driverBack: 'नागरिक अलर्ट',
    noMovement: 'कोई कॉरिडोर सक्रिय नहीं',
    noMovementSub: 'अभी कोई सुरक्षित वाहन नहीं — सामान्य चलें। यह फ़्लो आज़माने के लिए नागरिक पेज से डेमो काफ़िला चलाएँ।',
    atStretch: 'आप यहाँ हैं',
    urgency: 'मरीज़ की तात्कालिकता',
    urgCardiac: 'हृदय',
    urgTrauma: 'दुर्घटना',
    urgStroke: 'स्ट्रोक',
    urgOther: 'अन्य आपात',
    requestBtn: 'कॉरिडोर समय का अनुरोध',
    evaluating: 'कॉरिडोर गैप आँका जा रहा है…',
    proposalTitle: 'प्लेटफ़ॉर्म का प्रस्तावित समय',
    convoyReachesIn: 'काफ़िला आपके हिस्से तक पहुँचेगा',
    crossBefore: 'इससे पहले पार करें',
    officerLabel: 'ड्यूटी अधिकारी (डेमो)',
    approveBtn: 'मंज़ूर · विंडो खोलें',
    deferBtn: 'टालें',
    windowOpen: 'विंडो खुली — अभी पार करें',
    windowClosesIn: 'विंडो बंद होगी',
    minutesReturned: 'मिनट गोल्डन आवर को लौटाए गए',
    holdPosition: 'रुकें — अगली विंडो',
    baselineNote: 'अनुरोध का कोई रास्ता न हो तो: दर्ज आँकड़ों में एम्बुलेंस 5–20 मिनट रुकती है।',
    openDriverView: '108 ड्राइवर व्यू खोलें',
    demoNote: 'स्क्रिप्टेड सिमुलेशन पर चलने वाला डेमो — कोई असली डिस्पैच नहीं।',
  },

  bn: {
    brand: 'করিডর সতর্কতা · কলকাতা',
    tagline: 'ব্যারিকেড ওঠার আগেই জেনে নিন।',
    updated: 'ট্রাফিক কন্ট্রোল রুম থেকে সরাসরি আপডেট',
    statusActive: 'সুরক্ষিত যাত্রা চলছে',
    statusActiveSub: 'প্রতিটি অংশে ~2–3 মিনিটের ধাপে ধাপে হোল্ড — পুরো রাস্তা বন্ধ নয়।',
    statusClear: 'এখন কোনও করিডর নিষেধাজ্ঞা নেই',
    statusClearSub: 'শহরের সব করিডরে স্বাভাবিক ট্রাফিক।',
    statusDone: 'যাত্রা শেষ — করিডর খোলা',
    statusDoneSub: 'ট্রাফিক স্বাভাবিক হচ্ছে।',
    startDemo: 'একটি ডেমো যাত্রা চালান',
    freezeTitle: 'কোথায় হোল্ড হতে পারে',
    freezeZone: 'রাস্তার অংশ',
    freezeWindow: 'হোল্ডের সময়',
    freezeMinutes: (m) => `~${m} মিনিট`,
    alternate: 'এর বদলে চলুন',
    holdNow: 'এখন হোল্ড',
    passed: 'খোলা',
    why: 'এত অল্প সময় কেন?',
    whyBody:
      'হোল্ডের সময় ঠিক হয় কনভয়ের লাইভ অবস্থান (60–180 সেকেন্ড আগে) আর ট্রাফিক পূর্বাভাস দেখে — কনভয় সত্যিই পার হওয়ার সময়টুকুই রাস্তা বন্ধ থাকে।',
    subscribeTitle: 'আপনার ফোনে সতর্কবার্তা পান',
    subscribeSub: 'SMS / WhatsApp, বিনামূল্যে, আপনার ভাষায়।',
    phoneLabel: 'মোবাইল নম্বর',
    phonePlaceholder: '10 অঙ্কের মোবাইল নম্বর',
    languageLabel: 'সতর্কবার্তার ভাষা',
    subscribeBtn: 'সাবস্ক্রাইব করুন',
    demoBadge: 'ডেমো প্রিভিউ — কোনও আসল SMS/WhatsApp পাঠানো হয় না',
    previewTitle: 'আপনি পাবেন:',
    subscribed: 'সাবস্ক্রাইব হয়েছে (ডেমো)',
    emergencyTitle: 'অ্যাম্বুলেন্স বা দমকলের গাড়ি চালাচ্ছেন?',
    emergencyBody:
      'চলমান যাত্রার মধ্যে গ্রিন-করিডরের সময় চান — কন্ট্রোল রুম কয়েক সেকেন্ডে উত্তর দেয়।',
    emergencyCta: 'গ্রিন করিডরের অনুরোধ',
    backToOps: 'অপারেটর কনসোল',
    footerNote:
      'করিডর পরিচালনার প্রোটোটাইপের উপর তৈরি নমুনা জনসাধারণের পরামর্শ। বিকল্প পথগুলি নির্দেশক মাত্র।',

    // ── Green-corridor driver flow (108) ──────────────────────────
    driverTitle: 'গ্রিন করিডর — অ্যাম্বুলেন্স (108) চালক',
    driverSub: 'একটি ট্যাপ। কন্ট্রোল রুম কয়েক সেকেন্ডে উত্তর দেয়।',
    driverBack: 'নাগরিক সতর্কতা',
    noMovement: 'কোনও করিডর সক্রিয় নেই',
    noMovementSub: 'এখন কোনও সুরক্ষিত যাত্রা নেই — স্বাভাবিকভাবে চালান। এই প্রক্রিয়াটি দেখতে নাগরিক পেজ থেকে ডেমো যাত্রা চালু করুন।',
    atStretch: 'আপনি এখানে',
    urgency: 'রোগীর জরুরি অবস্থা',
    urgCardiac: 'হৃদ্‌রোগ',
    urgTrauma: 'দুর্ঘটনাজনিত আঘাত',
    urgStroke: 'স্ট্রোক',
    urgOther: 'অন্য জরুরি অবস্থা',
    requestBtn: 'করিডরের সময় চান',
    evaluating: 'করিডরের ফাঁক যাচাই হচ্ছে…',
    proposalTitle: 'প্ল্যাটফর্মের প্রস্তাবিত সময়',
    convoyReachesIn: 'কনভয় আপনার অংশে পৌঁছবে',
    crossBefore: 'এর আগে পার হোন',
    officerLabel: 'ডিউটি অফিসার (ডেমো)',
    approveBtn: 'অনুমোদন করুন · সময় খুলুন',
    deferBtn: 'পরে',
    windowOpen: 'সময় খোলা — এখনই পার হোন',
    windowClosesIn: 'সময় শেষ হবে',
    minutesReturned: 'মিনিট গোল্ডেন আওয়ারে ফিরল',
    holdPosition: 'অপেক্ষা করুন — পরের সময়',
    baselineNote: 'অনুরোধের কোনও উপায় না থাকলে: নথিভুক্ত হিসেবে কনভয় করিডরের পিছনে অ্যাম্বুলেন্স 5–20 মিনিট আটকে থাকে।',
    openDriverView: 'অ্যাম্বুলেন্স (108) চালকের ভিউ খুলুন',
    demoNote: 'স্ক্রিপ্টেড সিমুলেশনে চলা ডেমো — কোনও আসল ডিসপ্যাচ বা রোগীর তথ্য নেই।',
  },
};

export function t(lang, key, ...args) {
  const pack = PACKS[lang] || PACKS.en;
  const val = pack[key];
  if (typeof val === 'function') return val(...args);
  return val != null ? val : key;
}

/**
 * Indic-script digits for the demo alert preview (authentic touch — Indian
 * SMS gateways deliver in the subscriber's script).
 */
const DIGITS = {
  en: '0123456789',
  hi: '०१२३४५६७८९',
  bn: '০১২৩৪৫৬৭৮৯',
};

export function localizeNumber(n, lang) {
  const table = DIGITS[lang] || DIGITS.en;
  return String(n).replace(/[0-9]/g, (d) => table[+d]);
}
