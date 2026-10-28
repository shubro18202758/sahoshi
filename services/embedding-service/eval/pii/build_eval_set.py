"""Build ``pii_eval_set.synthetic.json``: a SYNTHETIC, hand-labelled set of short Kolkata news-style sentences for
measuring person-name redaction (and the place names it must never touch).

Every sentence below is invented for this evaluation. The person names are fictional combinations of common
Bengali, Hindi and other Indian given names and surnames; they refer to no real individual. The places are real
public Kolkata places (many named after historical figures), which is the point: a redactor must leave them alone.
Phone numbers are invented and e-mail addresses use the reserved ``example.com`` / ``example.in`` domains.

Markup: ``[[TAG|text]]`` marks a labelled span. Tags:

* ``P``  a private person's name (gold PII)            * ``PH`` a phone number (gold PII)
* ``EM`` an e-mail address (gold PII)                  * ``A``  an age (informational: the rules redact ages)
* ``L``  a place name that must NOT be redacted        * ``O``  a public-office title, no name (must NOT be redacted)
* ``N``  a public emergency number (must NOT be redacted)
* ``V``  a vehicle plate (informational: plates are masked by a separate rule, not by name redaction)

Languages: ``en`` English, ``bn`` Bengali (Bengali script), ``hi`` Hindi (Devanagari), ``bn-Latn`` romanised
Bengali and Bengali-English code-mixing.

Run: ``python3 build_eval_set.py`` (stdlib only) rewrites the JSON next to this file.
"""

# ruff: noqa: E501  (the sentences are data)
from __future__ import annotations

import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().with_name("pii_eval_set.synthetic.json")

TAGS = {
    "P": "person",
    "PH": "phone",
    "EM": "email",
    "A": "age",
    "L": "place",
    "O": "office",
    "N": "public_number",
    "V": "plate",
}

# fmt: off
SENTENCES: dict[str, list[str]] = {
    "en": [
        "Waterlogging on [[L|Rash Behari Avenue]] after two hours of rain; [[O|the Mayor]] said pumps were running.",
        "A bus broke down on [[L|Sarat Bose Road]] near [[L|Deshapriya Park]]; driver [[P|Subrata Mondal]] was unhurt.",
        "Local resident Mrs [[P|Mitali Ghosh]], [[A|54]], said the drains on [[L|Bidhan Sarani]] were choked again.",
        "Traffic was diverted from [[L|Chittaranjan Avenue]] to [[L|Jatindra Mohan Avenue]] for the procession.",
        "[[P|Amit Pal]], a vegetable vendor, was injured when a tree fell on [[L|Shyama Prasad Mukherjee Road]].",
        "Morning walkers at [[L|Rabindra Sarobar]] reported a fallen branch blocking the eastern gate.",
        "A cultural programme at [[L|Rabindra Sadan]] will end at 9 pm; expect slow traffic on [[L|AJC Bose Road]].",
        "Heavy vehicles are barred from [[L|Vidyasagar Setu]] between 8 am and 11 am on Sunday.",
        "Flights at [[L|Netaji Subhas Chandra Bose International Airport]] were delayed by up to 40 minutes after the storm.",
        "Dr [[P|Anirban Mitra]] of [[L|SSKM Hospital]] said the injured pedestrian was stable.",
        "A water main burst on [[L|Aurobindo Sarani]]; KMC crews were on site by noon.",
        "Signals on [[L|Acharya Jagadish Chandra Bose Road]] failed for an hour during the downpour.",
        "[[L|Rani Rashmoni Avenue]] will stay closed for the Red Road rehearsal, [[O|the Deputy Commissioner of Police (Traffic)]] said.",
        "Commuters on [[L|Kazi Nazrul Islam Avenue]] faced a long queue near the toll plaza.",
        "A transformer fire was reported at [[L|Bagha Jatin]] late on Tuesday; no one was hurt.",
        "Shopkeeper [[P|Partha Chakraborty]] said water entered his shop near [[L|Deshbandhu Park]].",
        "[[L|Mother Teresa Sarani]] is one-way towards [[L|Park Street]] until Friday.",
        "A truck carrying bricks overturned on [[L|Prafulla Chandra Road]]; the cleaner [[P|Rakesh Yadav]], [[A|31]], was taken to hospital.",
        "Office traffic around [[L|BBD Bag]] eased by 7 pm.",
        "Biker [[P|Sayan Das]] dies after his scooter skidded on [[L|Netaji Subhas Road]].",
        "Contact the ward office at [[PH|98300 41526]] or write to [[EM|ward87.help@example.in]] to report a blocked drain.",
        "A car, [[V|WB 02 AB 1234]], hit the divider on [[L|AJC Bose Road]]; call [[N|112]] for emergencies.",
        "Ambulance ([[N|108]]) crews were stuck for 20 minutes on [[L|Chittaranjan Avenue]].",
        "[[O|The Officer-in-Charge of Lake police station]] said the crossing near [[L|Rabindra Sarobar]] metro would reopen soon.",
        "[[P|Moumita Saha]]'s family said she had left for [[L|Esplanade]] at 6 pm.",
        "[[P|Debashis Sarkar]] and [[P|Sanchita Bhattacharya]] were rescued from a waterlogged lane off [[L|Bidhan Sarani]].",
        "[[O|A KMC drainage engineer]] said the [[L|Thanthania]] pumping station was running at full capacity.",
        "Police seized a motorcycle, [[V|WB 06 K 5678]], abandoned near [[L|Girish Park]] metro station.",
        "Passengers alighting at [[L|Masterda Surya Sen]] metro station were held back during the signal failure.",
        "The pandal near [[L|Mahanayak Uttam Kumar]] metro station drew large crowds on Saptami.",
        "Retired teacher [[P|Arijit Roy]], [[A|67]], told reporters the footpath on [[L|Sarat Bose Road]] was broken.",
        "Water stood knee-deep at [[L|Kalighat]] and on [[L|Shyama Prasad Mukherjee Road]] at high tide.",
        "Mr [[P|Kaushik Adhikari]], who runs a tea stall on [[L|Lenin Sarani]], said sales had halved.",
        "Fire tenders reached [[L|Bipin Behari Ganguly Street]] within 15 minutes, [[O|the fire department]] said.",
        "Volunteers led by [[P|Paromita Pal]] distributed water at [[L|Santosh Mitra Square]].",
        "[[P|Tanmoy Halder]] ([[A|29]]) was arrested for rash driving on [[L|Hemanta Basu Sarani]].",
        "For lost property call [[PH|+91 90070 23418]]; the counter at [[L|Howrah Station]] is open all night.",
        "Students of a school on [[L|Ashutosh Mukherjee Road]] were sent home early because of the rain.",
        "[[O|The Commissioner of Police]] reviewed crowd arrangements at [[L|Eden Gardens]] ahead of the match.",
        "Smt [[P|Shampa Basak]] said the queue at the [[L|Sealdah]] taxi stand stretched to the flyover.",
    ],
    "bn": [
        "[[L|রাসবিহারী অ্যাভিনিউতে]] জল জমেছে, স্থানীয় বাসিন্দা [[P|সুব্রত মণ্ডল]] জানালেন।",
        "[[L|শরৎ বসু রোডে]] বাস বিকল, চালক [[P|অমিত পাল]] আহত।",
        "[[L|বিধান সরণিতে]] যানজট, [[O|ট্রাফিক বিভাগের ডেপুটি কমিশনার]] জানিয়েছেন দুপুরের মধ্যে স্বাভাবিক হবে।",
        "[[L|নেতাজি সুভাষ রোডে]] একটি গাছ ভেঙে পড়েছে, কেউ আহত হননি।",
        "[[L|চিত্তরঞ্জন অ্যাভিনিউ]] দিয়ে মিছিল যাবে, তাই [[L|যতীন্দ্রমোহন অ্যাভিনিউ]] দিয়ে গাড়ি ঘোরানো হচ্ছে।",
        "[[L|শ্যামাপ্রসাদ মুখার্জি রোডে]] হাঁটুজল, দোকানদার [[P|পার্থ চক্রবর্তী]] বললেন দোকানে জল ঢুকেছে।",
        "[[L|রবীন্দ্র সরোবরে]] প্রাতর্ভ্রমণকারীরা ভেঙে পড়া ডাল দেখতে পান।",
        "[[L|রবীন্দ্র সদনে]] অনুষ্ঠান রাত ন'টায় শেষ হবে।",
        "[[L|বিদ্যাসাগর সেতুতে]] রবিবার সকালে ভারী গাড়ি চলবে না।",
        "ঝড়ের পরে [[L|নেতাজি সুভাষচন্দ্র বসু আন্তর্জাতিক বিমানবন্দরে]] বিমান দেরিতে ছেড়েছে।",
        "[[L|অরবিন্দ সরণিতে]] জলের পাইপ ফেটেছে, পুরসভার কর্মীরা কাজ করছেন।",
        "[[L|আচার্য জগদীশচন্দ্র বসু রোডে]] সিগন্যাল এক ঘণ্টা বন্ধ ছিল।",
        "মহড়ার জন্য [[L|রানি রাসমণি অ্যাভিনিউ]] বন্ধ থাকবে, জানিয়েছেন [[O|পুলিশ কমিশনার]]।",
        "[[L|কাজী নজরুল ইসলাম অ্যাভিনিউতে]] টোল প্লাজার কাছে লম্বা লাইন।",
        "[[L|বাঘাযতীনে]] মঙ্গলবার রাতে ট্রান্সফরমারে আগুন লাগে, কেউ আহত হননি।",
        "[[L|দেশবন্ধু পার্কের]] কাছে দোকানে জল ঢুকেছে বলে জানালেন ব্যবসায়ী [[P|তন্ময় হালদার]]।",
        "শুক্রবার পর্যন্ত [[L|মাদার টেরিজা সরণি]] একমুখী থাকবে।",
        "[[L|প্রফুল্লচন্দ্র রোডে]] ইট বোঝাই লরি উল্টে গেছে, খালাসি [[P|রাকেশ যাদব]] হাসপাতালে।",
        "সন্ধ্যা সাতটার পর [[L|বিবাদী বাগে]] যানজট কমেছে।",
        "[[A|৪৫ বছর বয়সী]] [[P|মৌমিতা সাহা]] [[L|গড়িয়াহাট মোড়ে]] দুর্ঘটনায় আহত হয়েছেন।",
        "শ্রীমতী [[P|রীতা সেন]] জানান, [[L|বিধান সরণির]] নর্দমা আবার বুজে গেছে।",
        "ডাঃ [[P|অনির্বাণ মিত্র]] বলেন, আহত পথচারীর অবস্থা স্থিতিশীল।",
        "[[P|দেবাশিস সরকার]] ও [[P|সঞ্চিতা ভট্টাচার্যকে]] জলমগ্ন গলি থেকে উদ্ধার করা হয়।",
        "নিকাশি নালা বুজে গেলে [[PH|৯৮৩০০ ৪১৫২৬]] নম্বরে ফোন করুন।",
        "জরুরি প্রয়োজনে [[N|১১২]] নম্বরে ফোন করুন, অ্যাম্বুলেন্সের জন্য [[N|১০৮]]।",
        "[[L|এসপ্ল্যানেডে]] রওনা হওয়ার পর থেকে [[P|পায়েল দে]]-র খোঁজ মিলছে না বলে পরিবার জানিয়েছে।",
        "অবসরপ্রাপ্ত শিক্ষক [[P|অরিজিৎ রায়]] জানালেন, [[L|শরৎ বসু রোডের]] ফুটপাত ভাঙা।",
        "[[L|কালীঘাটে]] ও [[L|শ্যামাপ্রসাদ মুখার্জি রোডে]] জোয়ারের সময় হাঁটুজল।",
        "[[L|গিরিশ পার্ক]] মেট্রো স্টেশনের কাছে একটি পরিত্যক্ত মোটরবাইক উদ্ধার হয়েছে।",
        "[[L|মাস্টারদা সূর্য সেন]] মেট্রো স্টেশনে সিগন্যাল বিভ্রাটে যাত্রীরা আটকে পড়েন।",
        "স্বেচ্ছাসেবক [[P|শ্রেয়া মজুমদার]] [[L|সন্তোষ মিত্র স্কোয়্যারে]] জল বিতরণ করেন।",
        "[[L|সল্টলেক স্টেডিয়ামের]] সামনে ম্যাচের পরে ভিড়, [[O|বিধাননগর পুলিশের এক আধিকারিক]] জানান।",
        "বেপরোয়া গাড়ি চালানোর অভিযোগে [[P|সৌগত কুণ্ডুকে]] গ্রেফতার করা হয়েছে।",
        "[[L|হাওড়া স্টেশনে]] হারানো জিনিসের কাউন্টার সারা রাত খোলা।",
        "[[O|মেয়র]] জানিয়েছেন, [[L|ঠনঠনিয়ায়]] পাম্প পুরোদমে চলছে।",
        "[[L|লেনিন সরণিতে]] চায়ের দোকান চালান [[P|কৌশিক অধিকারী]], তিনি বলেন বিক্রি অর্ধেক হয়ে গেছে।",
        "[[L|হেমন্ত বসু সরণিতে]] গাড়ি দুর্ঘটনায় [[P|বিশ্বজিৎ নস্কর]] ([[A|৩৮]]) আহত।",
        "[[L|আশুতোষ মুখার্জি রোডের]] একটি স্কুল বৃষ্টির জন্য আগে ছুটি দিয়েছে।",
    ],
    "hi": [
        "[[L|रासबिहारी एवेन्यू]] पर जलभराव, स्थानीय निवासी [[P|सुनीता शर्मा]] ने बताया कि नाली जाम है।",
        "[[L|शरत बोस रोड]] पर बस खराब, ड्राइवर [[P|राकेश यादव]] घायल।",
        "[[L|विधान सरणी]] पर जाम, [[O|यातायात उपायुक्त]] ने कहा दोपहर तक सामान्य होगा।",
        "[[L|नेताजी सुभाष रोड]] पर पेड़ गिरा, कोई घायल नहीं।",
        "[[L|चित्तरंजन एवेन्यू]] पर जुलूस के कारण यातायात [[L|जतींद्र मोहन एवेन्यू]] की ओर मोड़ा गया।",
        "[[L|विद्यासागर सेतु]] पर रविवार सुबह भारी वाहनों पर रोक रहेगी।",
        "तूफ़ान के बाद [[L|नेताजी सुभाष चंद्र बोस अंतरराष्ट्रीय हवाई अड्डे]] पर उड़ानें देर से चलीं।",
        "दुकानदार [[P|मनोज गुप्ता]] ने कहा [[L|बीबीडी बाग]] के पास दुकान में पानी घुस गया।",
        "[[A|45 वर्षीय]] [[P|पूजा सिंह]] [[L|हावड़ा ब्रिज]] पर हादसे में घायल हुईं।",
        "[[P|इमरान अंसारी]] और [[P|सलमा खातून]] को [[L|रवींद्र सरोवर]] के पास जलमग्न गली से निकाला गया।",
        "नाली जाम होने पर [[PH|98300 41526]] पर फ़ोन करें।",
        "आपात स्थिति में [[N|112]] पर कॉल करें, एम्बुलेंस के लिए [[N|108]]।",
        "[[O|पुलिस आयुक्त]] ने [[L|ईडन गार्डन्स]] में भीड़ प्रबंधन की समीक्षा की।",
        "डॉ. [[P|अनिल वर्मा]] ने कहा घायल पैदल यात्री की हालत स्थिर है।",
        "[[L|काज़ी नज़रुल इस्लाम एवेन्यू]] पर टोल प्लाज़ा के पास लंबी कतार।",
        "[[L|सियालदह]] स्टेशन पर टैक्सी की कतार में खड़े [[P|विकास तिवारी]] ने बताया कि एक घंटा लगा।",
    ],
    "bn-Latn": [
        "[[L|Rashbehari Avenue]] te jol jomeche, [[P|Subrata]] da bollen 2 foot jol.",
        "[[L|Sarat Bose Road]] e bus kharap hoye geche, driver [[P|Bapi Mondal]] ahoto.",
        "[[L|Bidhan Sarani]] te jam, amar boudi [[P|Mitali Ghosh]] 1 ghonta atke ache.",
        "[[L|Gariahat]] more e accident, [[P|Ananya Das]] er scooty te dhakka dieche ekta taxi.",
        "Aaj [[L|Rabindra Sarobar]] er gate bondho, morning walk e jawa jabe na.",
        "[[L|Netaji Subhas Chandra Bose International Airport]] e flight delay, [[P|Rina Sen]] bollen 2 ghonta wait korchi.",
        "[[L|Vidyasagar Setu]] te heavy jam, office jete late hobe.",
        "[[L|Chittaranjan Avenue]] diye michil jabe, tai [[L|Jatindra Mohan Avenue]] diye ghuriye dicche.",
        "Pujor bhir [[L|Deshbandhu Park]] er samne, [[P|Tumpa Sinha]] r sathe dekha holo.",
        "[[L|AJC Bose Road]] e signal bondho, traffic police haath diye control korche.",
        "[[L|Kazi Nazrul Islam Avenue]] e long queue, [[P|Joydeep Kundu]] bollo toll plaza te 30 min.",
        "Contact [[P|Sudipta]] da for flood relief: [[PH|9830015577]].",
        "Ki obostha [[L|Rani Rashmoni Avenue]] te? Rehearsal er jonno bondho naki?",
        "[[L|Bagha Jatin]] e transformer e agun legeche, kew ahoto noy.",
        "[[L|Mother Teresa Sarani]] one-way, [[L|Park Street]] er dike jaoa jabe na.",
        "[[L|Prafulla Chandra Road]] e lorry ulte geche, khalashi [[P|Raju Naskar]] hospital e.",
        "[[L|BBD Bag]] e sondhe 7 tar por jam kome geche.",
        "Amar neighbour [[P|Arnab Biswas]] [[L|Shyama Prasad Mukherjee Road]] e atke ache, knee deep jol.",
        "Email [[EM|tapas.dey84@example.com]] if you found a blue bag near [[L|Sealdah]].",
        "[[V|WB 11 C 4321]] number er car ta [[L|Howrah Bridge]] e breakdown.",
        "[[L|Rabindra Sadan]] e program ache, [[L|Exide]] more e slow traffic.",
        "[[P|Pritam]] bhai bollo [[L|Ultadanga]] te jol nei, [[L|EM Bypass]] clear.",
        "[[L|Aurobindo Sarani]] te pipe burst, KMC lok kaaj korche.",
        "[[L|Acharya Jagadish Chandra Bose Road]] e signal fail, ek ghonta dhore.",
        "Didi [[P|Swapna Saha]] [[L|Kalighat]] theke bollen ghater dike jol uthche.",
        "[[O|Mayor]] bollen [[L|Thanthania]] te pump puro dome cholche.",
    ],
}
# fmt: on

_MARK = re.compile(r"\[\[(?P<tag>[A-Z]{1,2})\|(?P<body>[^\]]+)\]\]")


def parse(marked: str) -> tuple[str, list[dict]]:
    """Strip the markup; return the plain text and its labelled spans (character offsets into the plain text)."""
    out: list[str] = []
    spans: list[dict] = []
    pos = 0
    plain_len = 0
    for m in _MARK.finditer(marked):
        before = marked[pos : m.start()]
        out.append(before)
        plain_len += len(before)
        body = m.group("body")
        tag = m.group("tag")
        if tag not in TAGS:
            raise ValueError(f"unknown tag {tag!r} in {marked!r}")
        spans.append({"start": plain_len, "end": plain_len + len(body), "type": TAGS[tag], "text": body})
        out.append(body)
        plain_len += len(body)
        pos = m.end()
    out.append(marked[pos:])
    text = "".join(out)
    if "[[" in text or "]]" in text:
        raise ValueError(f"unbalanced markup in {marked!r}")
    for s in spans:
        assert text[s["start"] : s["end"]] == s["text"]
    return text, spans


def build() -> dict:
    items = []
    for lang, sentences in SENTENCES.items():
        for i, marked in enumerate(sentences, 1):
            text, spans = parse(marked)
            items.append({"id": f"{lang}-{i:03d}", "lang": lang, "text": text, "spans": spans})
    return {
        "schema": "sahoshi.pii_eval/1",
        "synthetic": True,
        "label": "SYNTHETIC",
        "note": (
            "SYNTHETIC evaluation set: every sentence is invented; person names are fictional combinations of "
            "common given names and surnames and refer to no real individual; places are real public Kolkata "
            "places; phone numbers are invented; e-mail addresses use reserved example domains. Gold PII types: "
            "person, phone, email. Must-not-redact types: place, office, public_number. Informational: age, plate."
        ),
        "gold_pii_types": ["person", "phone", "email"],
        "protected_types": ["place", "office", "public_number"],
        "informational_types": ["age", "plate"],
        "items": items,
    }


if __name__ == "__main__":
    doc = build()
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    from collections import Counter

    langs = Counter(it["lang"] for it in doc["items"])
    types = Counter(s["type"] for it in doc["items"] for s in it["spans"])
    print(f"wrote {OUT.name}: {len(doc['items'])} sentences {dict(langs)}; spans {dict(types)}")
