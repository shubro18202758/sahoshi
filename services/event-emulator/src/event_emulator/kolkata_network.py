"""The Kolkata network ids the emulator names — GENERATED, do not edit.

Written by ``tools/kolkata_library.py`` from the city road network
(``cities/kolkata/network.json``): the living city's sites (EN + Bengali names, the
landmarks.json place each sits at), its emulated field units' beats,
the signalised junctions (those with a signal program) and the segments
the profiles' own causes sit on.  Re-run the tool when the network is
regenerated; the emulator's network check (ambient.py) and its tests
(tests/data/kolkata_network_slim.json) catch any drift.
"""

from __future__ import annotations

#: (site_id, kind, EN name, BN name, segments, junctions, detail EN,
#:  detail BN, landmarks.json place, festival)
SITE_ROWS: tuple[tuple, ...] = (
    ('BD-1001', 'breakdown', 'Howrah Bridge', 'হাওড়া ব্রিজ', (1001,), (2, 3), 'WBTC bus breakdown', 'ডব্লিউবিটিসি বাস বিকল', 'howrah_bridge', None),
    ('BD-1003', 'breakdown', 'Vidyasagar Setu', 'বিদ্যাসাগর সেতু', (1003,), (1, 4), 'Truck breakdown', 'ট্রাক বিকল', 'vidyasagar_setu', None),
    ('BD-1035', 'breakdown', 'EM Bypass (Ruby–Science City)', 'ই এম বাইপাস (রুবি–সায়েন্স সিটি)', (1035,), (29, 30), 'Container truck breakdown', 'কন্টেনার ট্রাক বিকল', 'ruby', None),
    ('BD-1037', 'breakdown', 'EM Bypass (Chingrighata)', 'ই এম বাইপাস (চিংড়িঘাটা)', (1037,), (31, 32), 'Goods tempo breakdown', 'মালবাহী টেম্পো বিকল', 'chingrighata', None),
    ('BD-1040', 'breakdown', 'VIP Road (Lake Town–Kestopur)', 'ভিআইপি রোড (লেক টাউন–কেষ্টপুর)', (1040,), (34, 35), 'App-cab breakdown', 'অ্যাপ ক্যাব বিকল', 'kestopur', None),
    ('BD-1049', 'breakdown', 'Diamond Harbour Road (Majerhat bridge)', 'ডায়মন্ড হারবার রোড (মাঝেরহাট সেতু)', (1049,), (26, 27), 'Truck breakdown', 'ট্রাক বিকল', 'majerhat', None),
    ('BD-1023', 'breakdown', 'AJC Bose Road (Mullickbazar)', 'এজেসি বোস রোড (মল্লিকবাজার)', (1023,), (13, 14), 'Stalled car', 'গাড়ি বিকল', None, None),
    ('BD-1053', 'breakdown', 'Chittaranjan Avenue (Girish Park)', 'চিত্তরঞ্জন অ্যাভিনিউ (গিরিশ পার্ক)', (1053,), (41, 43), 'Private bus breakdown', 'বেসরকারি বাস বিকল', None, None),
    ('BD-1004', 'breakdown', 'Strand Road (Babughat)', 'স্ট্র্যান্ড রোড (বাবুঘাট)', (1004,), (3, 11), 'Truck breakdown', 'ট্রাক বিকল', 'babughat', None),
    ('BD-1044', 'breakdown', 'Salt Lake Bypass (Sector V)', 'সল্টলেক বাইপাস (সেক্টর ফাইভ)', (1044,), (31, 39), 'App-cab breakdown', 'অ্যাপ ক্যাব বিকল', 'sector_v', None),
    ('BD-1046', 'breakdown', 'Biswa Bangla Sarani (New Town)', 'বিশ্ব বাংলা সরণি (নিউ টাউন)', (1046,), (37, 40), 'Stalled car', 'গাড়ি বিকল', 'biswa_bangla_sarani', None),
    ('BD-1062', 'breakdown', 'Bidhannagar Road (Ultadanga)', 'বিধাননগর রোড (উল্টোডাঙা)', (1062,), (33, 41), 'Tanker breakdown', 'ট্যাঙ্কার বিকল', 'ultadanga', None),
    ('BD-1029', 'breakdown', 'Maa Flyover', 'মা উড়ালপুল', (1029,), (17, 30), 'Stalled car', 'গাড়ি বিকল', 'park_circus', None),
    ('BD-1002', 'breakdown', 'Grand Trunk Road (Howrah)', 'জি টি রোড (হাওড়া)', (1002,), (1, 2), 'Private bus breakdown', 'বেসরকারি বাস বিকল', 'howrah_station', None),
    ('MK-1033', 'market_spillover', 'Gariahat (Rash Behari Avenue)', 'গড়িয়াহাট (রাসবিহারী অ্যাভিনিউ)', (1033,), (22, 23), '', '', 'gariahat', None),
    ('MK-1058', 'market_spillover', 'Hatibagan (Bidhan Sarani)', 'হাতিবাগান (বিধান সরণি)', (1058,), (41, 45), '', '', 'shyambazar', None),
    ('MK-1054', 'market_spillover', 'Burrabazar (MG Road)', 'বড়বাজার (মহাত্মা গান্ধী রোড)', (1054,), (3, 44), '', '', None, None),
    ('MK-1008', 'market_spillover', 'Brabourne Road (Burrabazar)', 'ব্রেবোর্ন রোড (বড়বাজার)', (1008,), (3, 6), '', '', 'bbd_bag', None),
    ('MK-1063', 'market_spillover', 'Esplanade (Lenin Sarani)', 'এসপ্ল্যানেড (লেনিন সরণি)', (1063,), (7, 15), '', '', 'esplanade', None),
    ('MK-1055', 'market_spillover', 'College Street (MG Road)', 'কলেজ স্ট্রিট (মহাত্মা গান্ধী রোড)', (1055,), (44, 45), '', '', 'college_square', None),
    ('MK-1056', 'market_spillover', 'Sealdah (APC Road)', 'শিয়ালদহ (আচার্য প্রফুল্লচন্দ্র রোড)', (1056,), (16, 42), '', '', 'sealdah', None),
    ('SE-1030', 'school_egress', 'Syed Amir Ali Avenue', 'সৈয়দ আমির আলি অ্যাভিনিউ', (1030,), (17, 24), '', '', 'ballygunge', None),
    ('SE-1031', 'school_egress', 'Hazra Road', 'হাজরা রোড', (1031,), (18, 24), '', '', 'hazra', None),
    ('SE-1019', 'school_egress', 'Ashutosh Mukherjee Road (Bhowanipore)', 'আশুতোষ মুখার্জি রোড (ভবানীপুর)', (1019,), (13, 18), '', '', 'hazra', None),
    ('SE-1015', 'school_egress', 'Queensway – Cathedral Road', 'কুইন্সওয়ে – ক্যাথিড্রাল রোড', (1015,), (13, 48), '', '', 'victoria_memorial', None),
    ('SE-1050', 'school_egress', 'Diamond Harbour Road (Behala)', 'ডায়মন্ড হারবার রোড (বেহালা)', (1050,), (27, 28), '', '', 'behala_chowrasta', None),
    ('SE-1044', 'school_egress', 'Salt Lake Bypass (Salt Lake)', 'সল্টলেক বাইপাস (সল্টলেক)', (1044,), (31, 39), '', '', 'sector_v', None),
    ('OR-1001', 'office_rush', 'Howrah Bridge', 'হাওড়া ব্রিজ', (1001,), (2, 3), '', '', 'howrah_bridge', None),
    ('OR-1008', 'office_rush', 'Brabourne Road (BBD Bag)', 'ব্রেবোর্ন রোড (বিবাদী বাগ)', (1008,), (3, 6), '', '', 'bbd_bag', None),
    ('OR-1009', 'office_rush', 'Old Court House Street (BBD Bag)', 'ওল্ড কোর্ট হাউস স্ট্রিট (বিবাদী বাগ)', (1009,), (6, 9), '', '', 'bbd_bag', None),
    ('OR-1051', 'office_rush', 'Chittaranjan Avenue (Esplanade)', 'চিত্তরঞ্জন অ্যাভিনিউ (এসপ্ল্যানেড)', (1051,), (7, 44), '', '', 'esplanade', None),
    ('OR-1017', 'office_rush', 'Jawaharlal Nehru Road (Chowringhee)', 'জওহরলাল নেহরু রোড (চৌরঙ্গি)', (1017,), (8, 12), '', '', 'park_street', None),
    ('OR-1003', 'office_rush', 'Vidyasagar Setu', 'বিদ্যাসাগর সেতু', (1003,), (1, 4), '', '', 'vidyasagar_setu', None),
    ('OR-1044', 'office_rush', 'Salt Lake Bypass (to Sector V)', 'সল্টলেক বাইপাস (সেক্টর ফাইভের পথে)', (1044,), (31, 39), '', '', 'sector_v', None),
    ('OR-1036', 'office_rush', 'EM Bypass (Science City)', 'ই এম বাইপাস (সায়েন্স সিটি)', (1036,), (30, 31), '', '', 'science_city', None),
    ('IT-1045', 'it_shift_change', 'Sector V – New Town link', 'সেক্টর ফাইভ – নিউ টাউন সংযোগ', (1045,), (39, 40), '', '', 'sector_v', None),
    ('IT-1046', 'it_shift_change', 'Biswa Bangla Sarani (New Town)', 'বিশ্ব বাংলা সরণি (নিউ টাউন)', (1046,), (37, 40), '', '', 'biswa_bangla_sarani', None),
    ('IT-1044', 'it_shift_change', 'Salt Lake Bypass (Sector V)', 'সল্টলেক বাইপাস (সেক্টর ফাইভ)', (1044,), (31, 39), '', '', 'sector_v', None),
    ('IT-1037', 'it_shift_change', 'EM Bypass (Chingrighata)', 'ই এম বাইপাস (চিংড়িঘাটা)', (1037,), (31, 32), '', '', 'chingrighata', None),
    ('WL-1058', 'waterlogging', 'Bidhan Sarani (Thanthania)', 'বিধান সরণি (ঠনঠনিয়া)', (1058,), (41, 45), '', '', 'thanthania', None),
    ('WL-1062', 'waterlogging', 'Bidhannagar Road (Ultadanga)', 'বিধাননগর রোড (উল্টোডাঙা)', (1062,), (33, 41), '', '', 'ultadanga', None),
    ('WL-1039', 'waterlogging', 'VIP Road (Ultadanga–Lake Town)', 'ভিআইপি রোড (উল্টোডাঙা–লেক টাউন)', (1039,), (33, 34), '', '', 'ultadanga', None),
    ('WL-1055', 'waterlogging', 'MG Road (College Street)', 'মহাত্মা গান্ধী রোড (কলেজ স্ট্রিট)', (1055,), (44, 45), '', '', 'college_square', None),
    ('WL-1057', 'waterlogging', 'APC Road (Maniktala)', 'আচার্য প্রফুল্লচন্দ্র রোড (মানিকতলা)', (1057,), (41, 42), '', '', None, None),
    ('WL-1025', 'waterlogging', 'AJC Bose Road (Moulali)', 'এজেসি বোস রোড (মৌলালি)', (1025,), (15, 16), '', '', 'moulali', None),
    ('WL-1027', 'waterlogging', 'Mother Teresa Sarani (Park Circus)', 'মাদার টেরিজা সরণি (পার্ক সার্কাস)', (1027,), (14, 17), '', '', 'park_circus', None),
    ('WL-1050', 'waterlogging', 'Diamond Harbour Road (Behala)', 'ডায়মন্ড হারবার রোড (বেহালা)', (1050,), (27, 28), '', '', 'behala_chowrasta', None),
    ('WL-1033', 'waterlogging', 'Rash Behari Avenue (Gariahat)', 'রাসবিহারী অ্যাভিনিউ (গড়িয়াহাট)', (1033,), (22, 23), '', '', 'gariahat', None),
    ('WL-1021', 'waterlogging', 'SP Mukherjee Road (Kalighat)', 'শ্যামাপ্রসাদ মুখার্জি রোড (কালীঘাট)', (1021,), (19, 20), '', '', 'kalighat', None),
    ('FC-1060', 'festival_crowd', 'Bagbazar Street (Bagbazar Sarbojanin)', 'বাগবাজার স্ট্রিট (বাগবাজার সর্বজনীন)', (1060,), (41, 47), '', '', 'bagbazar', 'puja'),
    ('FC-1061', 'festival_crowd', 'Strand Bank Road (Kumartuli Park)', 'স্ট্র্যান্ড ব্যাঙ্ক রোড (কুমোরটুলি পার্ক)', (1061,), (3, 47), '', '', 'kumartuli', 'puja'),
    ('FC-1055', 'festival_crowd', 'MG Road (College Square)', 'মহাত্মা গান্ধী রোড (কলেজ স্কোয়্যার)', (1055,), (44, 45), '', '', 'college_square', 'puja'),
    ('FC-1063', 'festival_crowd', 'Santosh Mitra Square', 'সন্তোষ মিত্র স্কোয়্যার', (1063,), (7, 15), '', '', 'santosh_mitra_square', 'puja'),
    ('FC-1032', 'festival_crowd', 'Rash Behari Avenue (Deshapriya Park)', 'রাসবিহারী অ্যাভিনিউ (দেশপ্রিয় পার্ক)', (1032,), (20, 22), '', '', 'deshapriya_park', 'puja'),
    ('FC-1033', 'festival_crowd', 'Rash Behari Avenue (Ekdalia Evergreen)', 'রাসবিহারী অ্যাভিনিউ (একডালিয়া এভারগ্রিন)', (1033,), (22, 23), '', '', 'ekdalia', 'puja'),
    ('FC-1058', 'festival_crowd', 'Bidhan Sarani (Hatibagan)', 'বিধান সরণি (হাতিবাগান)', (1058,), (41, 45), '', '', 'shyambazar', 'puja'),
    ('FC-1026', 'festival_crowd', 'Park Street', 'পার্ক স্ট্রিট', (1026,), (12, 14), '', '', 'park_street', 'year_end'),
    ('FC-1017', 'festival_crowd', 'Jawaharlal Nehru Road (Park Street)', 'জওহরলাল নেহরু রোড (পার্ক স্ট্রিট)', (1017,), (8, 12), '', '', 'park_street', 'year_end'),
    ('FC-1027', 'festival_crowd', 'Mother Teresa Sarani', 'মাদার টেরিজা সরণি', (1027,), (14, 17), '', '', 'park_street', 'year_end'),
    ('SF-J12', 'signal_fault', 'Park Street crossing', 'পার্ক স্ট্রিট মোড়', (1017, 1018, 1026), (12,), '', '', 'park_street', None),
    ('SF-J14', 'signal_fault', 'Mullickbazar crossing', 'মল্লিকবাজার মোড়', (1023, 1024, 1026, 1027), (14,), '', '', None, None),
    ('SF-J18', 'signal_fault', 'Hazra crossing', 'হাজরা মোড়', (1019, 1020, 1031), (18,), '', '', 'hazra', None),
    ('SF-J19', 'signal_fault', 'Kalighat (SP Mukherjee Road)', 'কালীঘাট (শ্যামাপ্রসাদ মুখার্জি রোড)', (1021, 1022), (19,), '', '', 'kalighat', None),
    ('SF-J20', 'signal_fault', 'Rashbehari crossing', 'রাসবিহারী মোড়', (1020, 1021, 1032), (20,), '', '', 'rashbehari', None),
    ('SF-J33', 'signal_fault', 'Ultadanga', 'উল্টোডাঙা', (1038, 1039, 1062), (33,), '', '', 'ultadanga', None),
)

#: (unit id, beat, connected segment chain)
PATROL_ROWS: tuple[tuple, ...] = (
    ('KTP-EM-LC1', 'Howrah Bridge–BBD Bag–Esplanade', (1001, 1008, 1009, 1010)),
    ('KTP-EM-LC2', 'EM Bypass (Ruby–Salt Lake Stadium)', (1035, 1036, 1037)),
    ('KTP-EM-LC3', 'Vidyasagar Setu–Nabanna–GT Road', (1003, 1002)),
    ('KTP-EM-LC4', 'JL Nehru Road (Esplanade–Exide)', (1016, 1017, 1018)),
    ('KTP-EM-LC5', 'APC Road (Sealdah–Shyambazar)', (1056, 1057)),
    ('KTP-EM-LC6', 'AJC Bose Road (Exide–Sealdah)', (1023, 1024, 1025)),
    ('KTP-EM-LC7', 'Hazra–Rash Behari Avenue–Gariahat', (1020, 1032, 1033)),
    ('KTP-EM-LC8', 'CR Avenue (Central Avenue–Shyambazar)', (1052, 1053)),
    ('KTP-EM-LC9', 'Salt Lake Bypass–Sector V–New Town', (1044, 1045)),
    ('KTP-EM-LC10', 'DH Road (Kidderpore–Behala)', (1048, 1049, 1050)),
    ('KTP-EM-LC11', 'VIP Road (Ultadanga–Baguiati)', (1039, 1040, 1041)),
    ('KP-EM-PCR1', 'Strand Road (Howrah Bridge–Prinsep Ghat)', (1004, 1005)),
    ('KP-EM-PCR2', 'SP Mukherjee Road (Rashbehari–Tollygunge)', (1021, 1022)),
    ('KP-EM-PCR3', 'Park Street–Mother Teresa Sarani', (1026, 1027)),
    ('108-EM-LC1', 'Ashutosh Mukherjee Rd–Hazra Rd', (1019, 1031)),
    ('108-EM-LC2', 'Maa Flyover to Science City', (1029,)),
    ('108-EM-LC3', 'Bijon Setu (Gariahat–Ruby)', (1034,)),
    ('108-EM-LC4', 'CR Avenue–College Street', (1051, 1055)),
)

#: Junctions with a signal program (corridor.signal_programs).
SIGNALISED_JUNCTIONS: frozenset[int] = frozenset({12, 14, 18, 19, 20, 33})

#: The segments the profiles' own causes sit on, by role.
PROFILE_SEGMENTS: dict[str, int] = {
    'bidhan_sarani': 1058,  # Bidhan Sarani
    'em_bypass_salt_lake': 1037,  # Eastern Metropolitan Bypass
    'khudiram_bose_road': 1012,  # Sahid Khudiram Bose Road
    'rg_kar_road_ultadanga': 1062,  # Radha Gobinda Kar Road - Bidhannagar Road
    'strand_road_babughat': 1004,  # Strand Road
    'sweep_market_road': 1054,  # Mahatma Gandhi Road
}
