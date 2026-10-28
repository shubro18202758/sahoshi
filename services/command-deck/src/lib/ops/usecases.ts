/**
 * The corridor-event use-case profiles: the eight seeded event profiles
 * (migration 008) and the five city-feeds scenarios (a market fire, a river
 * release with waterlogging, festival-night air quality, a heatwave and a
 * Nor'wester). Every one is SIMULATED.
 *
 * Every field is transcribed from the emulator's Kolkata use-case library
 * (event-emulator use_case_library.json: scenario_id, route spine, seed,
 * baseline closure policy, departure, replications, horizon, name,
 * description). The route spines are the library's on the Kolkata
 * (OpenStreetMap) network, cities/kolkata/network.json — each a legal path,
 * one-ways driven their own way (the contract tests hold them equal). They
 * serve three purposes:
 *
 *   1. OFFLINE FIXTURES for the multi-event board when GET /api/v1/events/active
 *      is not deployed yet (rows are tagged `offline-fixture` and labelled).
 *   2. Scenario picker + explicit fields for the twin shadow-eval panel.
 *   3. Launch presets surfaced to the emulator panel (use_case_id values).
 *
 * event_kind and crowd_class are the showcase's mapping of each profile onto
 * the generalized axes; the mapping follows the profile descriptions.
 */

import type {
	ClosurePolicySpec,
	CrowdClass,
	EventKind,
	EventPhase,
	ProtectionClass,
} from './types';

export interface UseCaseProfile {
	id: string;
	scenarioId: string;
	name: string;
	eventKind: EventKind;
	protectionClass: ProtectionClass;
	crowdClass: CrowdClass;
	routeSegmentIds: number[];
	departureTime: string; // ISO 8601 with +05:30
	baselinePolicy: ClosurePolicySpec;
	seed: number;
	nReplications: number;
	horizonMin: number;
	phases: EventPhase[];
	description: string;
}

const ISO_IST = (d: string) => d; // configs already carry +05:30 offsets

function movementPhases(
	departure: string,
	horizonMin: number,
	policy: ClosurePolicySpec,
	extra?: EventPhase[],
): EventPhase[] {
	const start = new Date(departure).toISOString();
	const end = new Date(new Date(departure).getTime() + horizonMin * 60_000).toISOString();
	const main: EventPhase = {
		label: 'movement window',
		startTime: start,
		endTime: end,
		closurePolicy: {
			advanceClosureSec: policy.advanceClosureSec,
			closureType: policy.closureType,
		},
		state: 'planned',
	};
	return extra ? [...extra, main] : [main];
}

export const USE_CASES: UseCaseProfile[] = [
	{
		id: 'vvip_convoy_base',
		scenarioId: 'vvip_convoy_base',
		name: 'VIP Movement — Base Case (Nabanna to Kolkata Airport)',
		eventKind: 'protected_movement',
		protectionClass: 'Z+',
		crowdClass: 'LOW',
		routeSegmentIds: [1003, 1028, 1029, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1065],
		departureTime: ISO_IST('2026-11-02T15:00:00+05:30'),
		baselinePolicy: { advanceClosureSec: 180, closureType: 'full_closure' },
		seed: 20261102,
		nReplications: 10,
		horizonMin: 45,
		phases: movementPhases('2026-11-02T15:00:00+05:30', 45, {
			advanceClosureSec: 180,
			closureType: 'full_closure',
		}),
		description:
			'SIMULATED BASE CASE. A Z+ protected movement from Nabanna, the state secretariat on the Howrah side, to Kolkata Airport on a Monday afternoon: across the Hooghly on Vidyasagar Setu, along the AJC Bose Road flyover to Park Circus, over the Maa Flyover to Science City, north on EM Bypass past Chingrighata and Salt Lake Stadium to Ultadanga, then up VIP Road past Lake Town, Kestopur and Baguiati to the airport and its approach road to the terminal forecourt. Maximum-protocol closure (180 s advance, full closure), default event rates, no weather — the reference movement every other scenario generalises. One planted cause (the profile): a goods vehicle stalls on EM Bypass ten minutes in. Public-safety logistics only: no person is named or tracked. The convoy speed (60 km/h) and the timings are modelled assumptions; the AI proposes the plan and a named officer decides.',
	},
	{
		id: 'durga_puja_north',
		scenarioId: 'durga_puja_north',
		name: 'Durga Puja Night — Pandal Crowds and Ambulance Access',
		eventKind: 'mass_gathering',
		protectionClass: 'X',
		crowdClass: 'EXTREME',
		routeSegmentIds: [1061, 1060, 1058],
		departureTime: ISO_IST('2025-09-30T21:30:00+05:30'),
		baselinePolicy: { advanceClosureSec: 45, closureType: 'signal_hold' },
		seed: 202509301,
		nReplications: 12,
		horizonMin: 60,
		phases: [
			{
				label: 'Puja nights (Saptami–Navami, 18:00–04:00 daily)',
				startTime: '2025-09-29T12:30:00.000Z',
				endTime: '2025-10-01T22:30:00.000Z',
				closurePolicy: null,
				state: 'planned',
			},
			...movementPhases('2025-09-30T21:30:00+05:30', 60, {
				advanceClosureSec: 45,
				closureType: 'signal_hold',
			}),
		],
		description:
			'FLAGSHIP. 21:30 on Maha Ashtami (30 Sep 2025, between Saptami and Navami), the busiest stretch of a Puja night. In the North Kolkata belt pandal-hoppers spill off the footpaths around Kumartuli Park and Bagbazar Sarbojanin, along Bidhan Sarani (Hatibagan), around College Square and Santosh Mitra Square; in the South belt the crowd around Deshapriya Park and Ekdalia Evergreen fills Rash Behari Avenue towards Gariahat. Goods vehicles are kept off the pandal belts for the night (the restriction is modelled as fewer heavy-vehicle breakdowns, breakdown x0.6) and food stalls load the kerbs (market x2.0). Ten minutes in, an ambulance (108) on an emergency call asks for a green corridor from the riverside north of Howrah Bridge up Strand Bank Road past Kumartuli, along Bagbazar Street to Shyambazar and down Bidhan Sarani to Kolkata Medical College. Closure policy signal_hold at 45 s: the crowd is regulated, not stopped. Two Kolkata Traffic Police beats and the ambulance are animated (EMULATED units). Crowd loads and speeds are modelled assumptions; the AI proposes each hold and a named officer decides.',
	},
	{
		id: 'gangasagar_transit',
		scenarioId: 'gangasagar_transit',
		name: 'Gangasagar Transit — Babughat Camp and the Bus Waves South',
		eventKind: 'mass_gathering',
		protectionClass: 'X',
		crowdClass: 'HIGH',
		routeSegmentIds: [1001, 1004, 1005, 1006, 1047, 1048],
		departureTime: ISO_IST('2027-01-12T06:00:00+05:30'),
		baselinePolicy: { advanceClosureSec: 90, closureType: 'signal_hold' },
		seed: 20270112,
		nReplications: 10,
		horizonMin: 60,
		phases: [
			{
				label: 'Babughat transit camp (multi-day schedule, bus waves south)',
				startTime: '2027-01-09T18:30:00.000Z',
				endTime: null,
				closurePolicy: null,
				state: 'planned',
			},
			...movementPhases('2027-01-12T06:00:00+05:30', 60, {
				advanceClosureSec: 90,
				closureType: 'signal_hold',
			}),
		],
		description:
			'SIMULATED. In the days before Makar Sankranti, pilgrims bound for Gangasagar on Sagar Island arrive at Howrah Station, cross Howrah Bridge and walk or ride along Strand Road to the transit camp at Babughat on the Hooghly bank, then leave by bus in waves towards the ferry crossings in the south: past Prinsep Ghat, through Hastings and Kidderpore and down Diamond Harbour Road over the Majerhat bridge. A morning wave: arrivals on the bridge and Strand Road, queues and boarding at the camp, stalls by Prinsep Ghat, and a pilgrim bus broken down on Diamond Harbour Road. Volumes and timings are modelled assumptions; signal_hold at 90 s keeps the bus waves moving.',
	},
	{
		id: 'kolkata_marathon',
		scenarioId: 'kolkata_marathon',
		name: 'Kolkata Marathon — Red Road and Riverside Loop',
		eventKind: 'race',
		protectionClass: 'X',
		crowdClass: 'HIGH',
		routeSegmentIds: [1012, 1013, 1014, 1006, 1005],
		departureTime: ISO_IST('2026-12-20T05:30:00+05:30'),
		baselinePolicy: { advanceClosureSec: 60, closureType: 'full_closure' },
		seed: 20261220,
		nReplications: 10,
		horizonMin: 60,
		phases: movementPhases('2026-12-20T05:30:00+05:30', 60, {
			advanceClosureSec: 60,
			closureType: 'full_closure',
		}),
		description:
			'SIMULATED. A city marathon on a winter Sunday morning on a modelled loop (not an official route map): the gun at 05:30 by Eden Gardens on Sahid Khudiram Bose Road, down Red Road along the Maidan, out on Kidderpore Road to Hastings and back north along the river on Strand Road past Prinsep Ghat to Babughat. The field and its spectators hold each stretch in turn and the loop reopens in stages behind the sweep vehicle. Full closure at 60 s advance; the lead vehicle runs at race pace (12 km/h). Field size and timings are modelled assumptions.',
	},
	{
		id: 'red_road_parade',
		scenarioId: 'red_road_parade',
		name: 'Red Road Parade — Republic Day / Independence Day',
		eventKind: 'ceremonial',
		protectionClass: 'Z',
		crowdClass: 'HIGH',
		routeSegmentIds: [1016, 1011, 1013],
		departureTime: ISO_IST('2027-01-26T08:30:00+05:30'),
		baselinePolicy: { advanceClosureSec: 150, closureType: 'full_closure' },
		seed: 20270126,
		nReplications: 10,
		horizonMin: 60,
		phases: movementPhases('2027-01-26T08:30:00+05:30', 60, {
			advanceClosureSec: 150,
			closureType: 'full_closure',
		}),
		description:
			'SIMULATED. The ceremonial parade on Red Road on a national day (Republic Day 26 Jan, Independence Day 15 Aug). The dignitaries\' ceremonial movement to the dais is a Z-class protected movement (no person is named): from Esplanade along Jawaharlal Nehru Road and the Old Court House Street link to the north end of Red Road, then down Red Road to the dais. Red Road is held for the parade and the contingents; spectators and their parking load Sahid Khudiram Bose Road and Queensway. Full closure at 150 s advance; crowd loads are modelled.',
	},
	{
		id: 'eden_gardens_egress',
		scenarioId: 'eden_gardens_egress',
		name: 'Eden Gardens — Match-Night Egress',
		eventKind: 'egress_surge',
		protectionClass: 'X',
		crowdClass: 'EXTREME',
		routeSegmentIds: [1012, 1004, 1001],
		departureTime: ISO_IST('2026-04-18T22:50:00+05:30'),
		baselinePolicy: { advanceClosureSec: 60, closureType: 'signal_hold' },
		seed: 20260418,
		nReplications: 12,
		horizonMin: 60,
		phases: movementPhases('2026-04-18T22:50:00+05:30', 60, {
			advanceClosureSec: 60,
			closureType: 'signal_hold',
		}),
		description:
			'SIMULATED. A full house leaves Eden Gardens after a night match (the crowd is modelled from a full stadium; no fixture or attendance figure is claimed). The dispersal wave pours out onto Sahid Khudiram Bose Road and splits: north along Strand Road past Babughat and over Howrah Bridge to Howrah Station for the last trains, and east along Rani Rashmoni Avenue to Esplanade and its Metro station. A stalled app cab blocks a dispersal lane on Strand Road twenty minutes in. Two ambulance (108) green-corridor requests (the profile) cut through the wave. Closure policy signal_hold at 60 s; crowd loads are modelled assumptions.',
	},
	{
		id: 'cloudburst_high_tide',
		scenarioId: 'cloudburst_high_tide',
		name: 'Cloudburst at High Tide — Waterlogging, Pumps and Live-Wire Hazard',
		eventKind: 'emergency_evacuation',
		protectionClass: 'X',
		crowdClass: 'HIGH',
		routeSegmentIds: [1039, 1062, 1058],
		departureTime: ISO_IST('2026-08-18T17:30:00+05:30'),
		baselinePolicy: { advanceClosureSec: 60, closureType: 'signal_hold' },
		seed: 20260818,
		nReplications: 10,
		horizonMin: 60,
		phases: movementPhases('2026-08-18T17:30:00+05:30', 60, {
			advanceClosureSec: 60,
			closureType: 'signal_hold',
		}),
		description:
			'SIMULATED. A monsoon evening (a scenario date, not a forecast): a cloudburst-class cell (rain modelled at 100 mm/h) breaks over North and Central Kolkata at 17:30 while the Hooghly is at high water (MODELLED tide phase). With the outfall gates shut against the river the drains cannot empty by gravity and KMC\'s pumping stations carry the whole load (pump capacity modelled), so the water spreads instead of draining: Thanthania on Bidhan Sarani first, then the Ultadanga approaches, MG Road by College Street, APC Road at Maniktala, AJC Bose Road at Moulali and Park Circus. A car stalls in standing water; signals at Ultadanga go dark (a modelled precautionary power cut). Where water stands around street-light poles and overhead lines the risk is electrocution: the stack may PROPOSE a live-wire hazard advisory to the power utility (CESC / WBSEDCL) — a proposal a named duty officer approves or rejects; nothing is sent by itself. An ambulance (108) from Lake Town to Kolkata Medical College needs windows through the water. Rain rate, tide, pump capacity and spread times are modelled assumptions, not measurements.',
	},
	{
		id: 'metro_work_zone',
		scenarioId: 'metro_work_zone',
		name: 'Metro Work Zone — Diamond Harbour Road',
		eventKind: 'work_zone',
		protectionClass: 'X',
		crowdClass: 'MODERATE',
		routeSegmentIds: [1050, 1049, 1048],
		departureTime: ISO_IST('2026-11-10T09:15:00+05:30'),
		baselinePolicy: { advanceClosureSec: 60, closureType: 'partial_closure' },
		seed: 20250814,
		nReplications: 8,
		horizonMin: 60,
		phases: [
			{
				label: 'published lane loss — Diamond Harbour Road (Metro works, 1 Oct – 31 Dec)',
				startTime: '2026-09-30T18:30:00.000Z',
				endTime: '2026-12-30T18:30:00.000Z',
				closurePolicy: { advanceClosureSec: null, closureType: 'partial_closure' },
				state: 'planned',
			},
			...movementPhases('2026-11-10T09:15:00+05:30', 60, {
				advanceClosureSec: 60,
				closureType: 'partial_closure',
			}),
		],
		description:
			'SIMULATED. A planned, published work zone: metro construction along Diamond Harbour Road holds barricaded lanes for weeks between Behala Chowrasta, Taratala and Kidderpore (a modelled work zone; no project timeline is claimed). On a weekday morning an inspection convoy runs the stretch from Behala over the Majerhat bridge to Kidderpore while the barricades pinch the carriageway and the Behala bazaar\'s traffic squeezes the remaining lanes. Partial closure at 60 s advance; lane losses and loads are modelled.',
	},
	{
		id: 'burrabazar_market_fire',
		scenarioId: 'burrabazar_market_fire',
		name: 'Burrabazar Market Fire — Fire-Tender Access and Ambulance Window',
		eventKind: 'emergency_evacuation',
		protectionClass: 'X',
		crowdClass: 'HIGH',
		routeSegmentIds: [1017, 1016, 1051, 1054, 1008],
		departureTime: ISO_IST('2026-11-18T14:40:00+05:30'),
		baselinePolicy: { advanceClosureSec: 45, closureType: 'signal_hold' },
		seed: 20261118,
		nReplications: 10,
		horizonMin: 60,
		phases: movementPhases('2026-11-18T14:40:00+05:30', 60, {
			advanceClosureSec: 45,
			closureType: 'signal_hold',
		}),
		description:
			'SIMULATED. A weekday afternoon in Burrabazar (Wednesday 18 Nov 2026, 14:40; a scenario date, not a record): a fire breaks out in a market building in the narrow lanes between Mahatma Gandhi Road and Brabourne Road, a short walk from the Kolkata end of Howrah Bridge. The nearest fire tender, from C R Avenue Fire Station at the Chittaranjan Avenue crossing, needs a window west along MG Road (one-way towards the bridge); a second tender line from the West Bengal Fire & Emergency Services headquarters near Park Street needs a green corridor up Jawaharlal Nehru Road to Esplanade, along Chittaranjan Avenue and MG Road, round the Howrah Bridge end and into Brabourne Road (one-way towards BBD Bag). Once the tenders are in, parked tenders and hose lines take lanes on MG Road and Brabourne Road, a police cordon narrows Strand Road at the lane mouths, handcarts are pushed out onto Chittaranjan Avenue, diverted traffic loads Strand Road north and the afternoon goods traffic queues on Howrah Bridge. The AI proposes each tender window, a goods-vehicle hold on the Howrah Bridge approaches (Howrah City Police at the Howrah end, Kolkata Traffic Police at the Kolkata end), a request to the power utility to isolate supply to the block, and the staged reopening of the cordoned roads; a named officer approves or rejects each, and nothing is sent by itself. Twenty-five minutes in, an ambulance (108) standing by at the east cordon needs a window along MG Road to Kolkata Medical College (no casualty details are modelled). Fire spread, turnout and travel times, lane losses and loads are modelled assumptions, not measurements.',
	},
	{
		id: 'dvc_release_howrah_waterlogging',
		scenarioId: 'dvc_release_howrah_waterlogging',
		name: 'DVC Release and Howrah Waterlogging — Cross-River Diversion',
		eventKind: 'emergency_evacuation',
		protectionClass: 'X',
		crowdClass: 'MODERATE',
		routeSegmentIds: [1003, 1007, 1006, 1005, 1004, 1001],
		departureTime: ISO_IST('2027-09-14T08:45:00+05:30'),
		baselinePolicy: { advanceClosureSec: 60, closureType: 'signal_hold' },
		seed: 20270914,
		nReplications: 10,
		horizonMin: 60,
		phases: movementPhases('2027-09-14T08:45:00+05:30', 60, {
			advanceClosureSec: 60,
			closureType: 'signal_hold',
		}),
		description:
			'SIMULATED. A monsoon weekday morning (Tuesday 14 Sep 2027, 08:45; a scenario, not a forecast and not a record of any real release). Damodar Valley Corporation (DVC) has announced a release from its Maithon and Panchet reservoirs; the release figure in this scenario is a SIMULATED input, not a DVC figure. The scenario assumes that, with the lower Damodar high, steady rain (modelled at 12 mm/h) and a high tide on the Hooghly (MODELLED tide phase), Howrah\'s drains back up: Grand Trunk Road between Nabanna and Howrah Station goes under water and a bus stalls in it, and water stands on the Howrah Station approach and at the foot of the Nabanna approach to Vidyasagar Setu. On the network Sahoshi models, the only dry way from Nabanna to Howrah Station is across the river twice: over Vidyasagar Setu, along Strand Road past Prinsep Ghat and Babughat, and back over Howrah Bridge, so diverted traffic loads both bridges. A WBSDMA pump-and-relief column runs that diversion behind a Howrah City Police pilot vehicle. The AI proposes the diversion, signal holds on Strand Road, a bus re-routing note for WBTC and a three-language traffic advisory; named officers of Howrah City Police and Kolkata Traffic Police each decide on their side of the river, and nothing is published by itself. Rain, tide, water depth, spread and loads are modelled assumptions.',
	},
	{
		id: 'kali_puja_air_quality',
		scenarioId: 'kali_puja_air_quality',
		name: 'Kali Puja Night — Air-Quality Advisory, Kalighat Crowd and Ambulance Priority',
		eventKind: 'mass_gathering',
		protectionClass: 'X',
		crowdClass: 'HIGH',
		routeSegmentIds: [1022, 1021, 1020, 1019],
		departureTime: ISO_IST('2026-11-08T21:30:00+05:30'),
		baselinePolicy: { advanceClosureSec: 45, closureType: 'signal_hold' },
		seed: 20261108,
		nReplications: 10,
		horizonMin: 60,
		phases: movementPhases('2026-11-08T21:30:00+05:30', 60, {
			advanceClosureSec: 45,
			closureType: 'signal_hold',
		}),
		description:
			'SIMULATED. Kali Puja night (Sunday 8 Nov 2026, 21:30, the Amavasya night; a scenario, not a forecast). Firecrackers across the city push fine-particle pollution up through the evening: the scenario\'s PM2.5 readings (SIMULATED, not measurements) climb from the Moderately Polluted band at 18:00 to the Very Poor band by 21:00 and touch Severe near midnight, banded indicatively against India\'s National Air Quality Index (whose bands are defined on 24-hour averages). Devotees fill SP Mukherjee Road around Kalighat temple, flower, lamp and sweet stalls line the road from Hazra to Rashbehari and pandal stalls load Rash Behari Avenue, so traffic slows along the whole stretch. Breathing-difficulty calls rise (modelled as ambulance x1.5). Fifteen minutes in, an ambulance (108) on a breathing-difficulty call needs windows from Tollygunge past Kalighat, Rashbehari and Hazra to Exide crossing, a short run from SSKM Hospital. The AI proposes each window, a priority flag for breathing-difficulty calls and a public health advisory in Bengali, English and Hindi; a named duty officer approves or rejects each, and nothing is published by itself. Crowd loads, readings and speeds are modelled assumptions; no individual is identified.',
	},
	{
		id: 'pre_monsoon_heatwave',
		scenarioId: 'pre_monsoon_heatwave',
		name: 'Pre-Monsoon Heatwave Afternoon — Overheated Vehicles and Duty Rotations',
		eventKind: 'work_zone',
		protectionClass: 'X',
		crowdClass: 'LOW',
		routeSegmentIds: [1003, 1028, 1029, 1036, 1037, 1038],
		departureTime: ISO_IST('2027-04-27T14:00:00+05:30'),
		baselinePolicy: { advanceClosureSec: 30, closureType: 'signal_hold' },
		seed: 20270427,
		nReplications: 10,
		horizonMin: 60,
		phases: movementPhases('2027-04-27T14:00:00+05:30', 60, {
			advanceClosureSec: 30,
			closureType: 'signal_hold',
		}),
		description:
			'SIMULATED. A pre-monsoon heatwave afternoon (Tuesday 27 Apr 2027, 14:00; a scenario, not a forecast). The scenario assumes IMD\'s heatwave criteria for the plains are met: a SIMULATED maximum of 41.8 °C against a SIMULATED normal of 36.2 °C (departure +5.6 °C; the criteria are a maximum of at least 40 °C with a departure of at least 4.5 °C, or a maximum of at least 45 °C). No real IMD bulletin is quoted. Vehicles overheat: a bus stalls on Vidyasagar Setu, a car with a burst tyre stops on the Maa Flyover, a goods vehicle overheats on EM Bypass between Science City and Chingrighata and a car stalls near Ultadanga (breakdowns modelled at x1.6). Pedestrian flows and street trading thin out in the heat (modelled crowd LOW, market x0.7) and heat-illness calls rise (ambulance x1.3). A Kolkata Traffic Police recovery van runs the corridor from the Nabanna end of Vidyasagar Setu over the AJC Bose Road flyover and the Maa Flyover and up EM Bypass to Ultadanga, clearing each breakdown. The AI proposes where to pre-position recovery vans, shorter duty rotations with shade and water for traffic staff at the most exposed crossings (Esplanade, Park Street, Shyambazar, Ultadanga) and a heat advisory for road users in Bengali, English and Hindi; a named duty officer approves or rejects each. Temperatures, breakdown rates and loads are modelled assumptions.',
	},
	{
		id: 'norwester_squall_treefall',
		scenarioId: 'norwester_squall_treefall',
		name: 'Nor\'wester Squall — Tree-Falls, Live-Wire Hazard and Staged Reopening',
		eventKind: 'work_zone',
		protectionClass: 'X',
		crowdClass: 'LOW',
		routeSegmentIds: [1038, 1037, 1036, 1035],
		departureTime: ISO_IST('2027-05-06T17:40:00+05:30'),
		baselinePolicy: { advanceClosureSec: 60, closureType: 'partial_closure' },
		seed: 20270506,
		nReplications: 8,
		horizonMin: 60,
		phases: movementPhases('2027-05-06T17:40:00+05:30', 60, {
			advanceClosureSec: 60,
			closureType: 'partial_closure',
		}),
		description:
			'SIMULATED. A Nor\'wester (Kalbaishakhi) evening (Thursday 6 May 2027; a scenario, not a forecast). A squall line crossed the city at about 17:20 with gusts SIMULATED at 70-90 km/h and heavy rain (modelled at 25 mm/h, STORM). At 17:40 the rain lingers and trees are down across the arterials: EM Bypass between Ultadanga and Ruby in three places (a weakened tree falls in a later gust), Red Road along the Maidan, AJC Bose Road between Exide and Moulali, and Rash Behari Avenue, where an overhead wire is also down across the road near Gariahat (live-wire hazard). Signals at Ultadanga are dark after a feeder trips (MODELLED). A KMC tree-clearing crew with a West Bengal Fire & Emergency Services rescue tender, escorted by Kolkata Traffic Police (and the Bidhannagar Police Commissionerate on its stretch), works south along EM Bypass from Ultadanga, so the corridor reopens in stages behind it. The stack may PROPOSE a request to the power utility (and to WBTC if it is a tram overhead line) to isolate the wire on Rash Behari Avenue — a proposal a named duty officer approves or rejects; nothing is sent by itself. Twenty minutes in, an ambulance (108) from Gariahat to Ruby General Hospital needs a window over the Bijon Setu connector. Every reopening is proposed by the AI and decided by a named officer. Gusts, rain, clearance times and loads are modelled assumptions.',
	},
];

export function useCaseById(id: string): UseCaseProfile | undefined {
	return USE_CASES.find((u) => u.id === id || u.scenarioId === id);
}
