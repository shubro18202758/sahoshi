-- 008_event_profiles.sql
-- Per-use-case corridor-event profile templates (core stream).
--
-- Seeds the eight canonical use-case profiles (from the scenario library
-- configs) as events.event_profiles: the archetypes the emulator and the
-- ops board instantiate corridor_events from.  A profile is a template —
-- event_kind + protection_class + crowd_class + representative route spine,
-- departure, closure policy and simulation knobs — never a live event row.
--
-- Idempotent: ON CONFLICT (profile_id) DO NOTHING (re-running never
-- overwrites operator edits to the template table).
--
-- GRAMMAR CONSTRAINT: no ';' inside string literals and no dollar-quoted
-- bodies — these files are also applied statement-by-statement by naive
-- `;`-splitters (see 007's header and tests/test_migration_pgvector).

CREATE TABLE IF NOT EXISTS events.event_profiles (
    profile_id       TEXT PRIMARY KEY,           -- e.g. 'durga_puja_north'
    event_kind       TEXT NOT NULL CHECK (event_kind IN (
                         'protected_movement', 'procession', 'mass_gathering',
                         'race', 'ceremonial', 'egress_surge',
                         'emergency_evacuation', 'work_zone'
                     )),
    protection_class TEXT NOT NULL CHECK (protection_class IN (
                         'Z+', 'Z', 'Y', 'X', 'none'
                     )),
    crowd_class      TEXT NOT NULL CHECK (crowd_class IN (
                         'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
                     )),
    name             TEXT NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    scenario_id      TEXT,                        -- twin scenario library key
    route_segment_ids BIGINT[] NOT NULL,
    departure_time   TIMESTAMPTZ NOT NULL,
    closure_policy   JSONB NOT NULL,
    horizon_min      SMALLINT NOT NULL CHECK (horizon_min BETWEEN 1 AND 60),
    duration_class   TEXT NOT NULL DEFAULT 'minutes' CHECK (duration_class IN (
                         'minutes', 'hours', 'multi_day', 'multi_week'
                     )),
    template         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO events.event_profiles (
    profile_id, event_kind, protection_class, crowd_class, name, description,
    scenario_id, route_segment_ids, departure_time, closure_policy,
    horizon_min, duration_class, template
) VALUES
    ('vvip_convoy_base', 'protected_movement', 'Z+', 'LOW',
     'VIP Movement — Nabanna to Kolkata Airport (base case)',
     'BASE CASE. A protected movement from Nabanna over Vidyasagar Setu, the '
     'AJC Bose Road and Maa flyovers, EM Bypass and VIP Road to the airport. '
     'Maximum-protocol closure (180 s advance, full closure), default event '
     'rates, no weather — the reference every other use case generalizes.',
     'vvip_convoy_base', ARRAY[1003,1028,1029,1036,1037,1038,1039,1040,1041,1042,1043,1065],
     '2026-11-02T04:40:00Z'::timestamptz,
     '{"advance_closure_sec": 180, "closure_type": "full_closure"}'::jsonb,
     45, 'minutes',
     '{"convoy_speed_kmh": 60, "n_replications": 10, "seed": 20261102}'::jsonb),
    ('durga_puja_north', 'procession', 'X', 'EXTREME',
     'Durga Puja Night — North Kolkata Pandal Belt',
     'Saptami to Navami nights: pandal-hopping crowds at walking pace through '
     'Bagbazar, Shyambazar and the Maniktala - Girish Park belt, with '
     'ad-hoc one-ways and a goods-vehicle restriction.',
     'durga_puja_north', ARRAY[1060,1057,1059,1052],
     '2026-10-18T13:30:00Z'::timestamptz,
     '{"advance_closure_sec": 120, "closure_type": "full_closure"}'::jsonb,
     60, 'hours',
     '{"convoy_speed_kmh": 8, "n_replications": 12, "seed": 20261018, '
     '"event_overrides": {"market": 2.5}}'::jsonb),
    ('gangasagar_transit', 'mass_gathering', 'X', 'EXTREME',
     'Gangasagar Transit — Babughat Camp and the Riverside',
     'Pilgrim transit through the Babughat transit camp: Howrah Bridge and '
     'Strand Road carry the bus and pedestrian surge while the riverside '
     'perimeter is managed in stages.',
     'gangasagar_transit', ARRAY[1001,1004,1005],
     '2027-01-12T23:00:00Z'::timestamptz,
     '{"advance_closure_sec": 90, "closure_type": "signal_hold"}'::jsonb,
     60, 'multi_day',
     '{"convoy_speed_kmh": 40, "n_replications": 12, "seed": 20270113}'::jsonb),
    ('kolkata_marathon', 'race', 'X', 'HIGH',
     'Kolkata Marathon — Red Road and Riverside Loop',
     'Early-morning gun start: the race loop over Red Road, Kidderpore Road '
     'and Strand Road is closed in the dark and reopens in stages behind the '
     'sweep (pace/sweep convoy at 12 km/h).',
     'kolkata_marathon', ARRAY[1012,1013,1014,1006,1005],
     '2026-12-20T00:15:00Z'::timestamptz,
     '{"advance_closure_sec": 60, "closure_type": "full_closure"}'::jsonb,
     60, 'hours',
     '{"convoy_speed_kmh": 12, "n_replications": 10, "seed": 20261220}'::jsonb),
    ('red_road_parade', 'ceremonial', 'Z', 'HIGH',
     'Republic Day / Independence Day — Red Road Parade',
     'Dignitaries reach the Red Road parade strip from Esplanade before the '
     'flag while spectators fill the strip.',
     'red_road_parade', ARRAY[1016,1011,1013],
     '2027-01-26T03:05:00Z'::timestamptz,
     '{"advance_closure_sec": 150, "closure_type": "full_closure"}'::jsonb,
     60, 'minutes',
     '{"convoy_speed_kmh": 40, "n_replications": 10, "seed": 20270126}'::jsonb),
    ('eden_gardens_egress', 'egress_surge', 'X', 'EXTREME',
     'Stadium Egress — Eden Gardens Match Night',
     'The 90-120 min egress surge after the last ball towards Howrah Bridge '
     'and Howrah Station: an ambulance with a green-corridor request moves '
     'against the dispersal wave under signal_hold.',
     'eden_gardens_egress', ARRAY[1012,1004,1001],
     '2026-03-08T14:35:00Z'::timestamptz,
     '{"advance_closure_sec": 60, "closure_type": "signal_hold"}'::jsonb,
     60, 'hours',
     '{"convoy_speed_kmh": 50, "n_replications": 12, "seed": 20260308}'::jsonb),
    ('cloudburst_high_tide', 'emergency_evacuation', 'X', 'MEDIUM',
     'Cloudburst at High Tide — Relief Corridor on EM Bypass',
     'Heavy rain meets a high tide on the Hooghly: the outfalls close and '
     'central Kolkata waterlogs while a relief column runs EM Bypass from '
     'Ruby to Ultadanga.',
     'cloudburst_high_tide', ARRAY[1035,1036,1037,1038],
     '2025-09-23T00:50:00Z'::timestamptz,
     '{"advance_closure_sec": 60, "closure_type": "signal_hold"}'::jsonb,
     60, 'hours',
     '{"convoy_speed_kmh": 40, "n_replications": 10, "seed": 20250923, '
     '"event_overrides": {"breakdown": 1.8, "waterlogging": 3}, '
     '"weather": {"monsoon": true, "rain_intensity_mm_h": 40}}'::jsonb),
    ('metro_work_zone', 'work_zone', 'X', 'LOW',
     'Planned Infrastructure Work Zone — Metro Works on Diamond Harbour Road',
     'Months-long published lane loss for metro construction: an inspection '
     'convoy runs Diamond Harbour Road from Behala Chowrasta over the '
     'Majerhat bridge to Kidderpore while the work zones hold barricaded lanes.',
     'metro_work_zone', ARRAY[1050,1049,1048],
     '2025-08-14T03:45:00Z'::timestamptz,
     '{"advance_closure_sec": 60, "closure_type": "partial_closure"}'::jsonb,
     60, 'multi_week',
     '{"convoy_speed_kmh": 40, "n_replications": 8, "seed": 20250814, '
     '"event_overrides": {"market": 1.5}}'::jsonb)
ON CONFLICT (profile_id) DO NOTHING;
