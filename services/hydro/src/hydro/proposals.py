"""Waterlogging PROPOSALS — never actions. A named officer approves each one; if no one answers, nothing
changes.

The shape follows the platform's decision-support vocabulary (osint_common C-U): ``state: proposed``,
actions as ``CoaAction`` (verb, target_urn, params, requires_officer, reversible), ``recommendation.decision:
await_officer`` and a ``human_gate`` naming the deciding role with no officer and no decision time.

* **reroute** (risk ≥ 2) — a diversion around the segment on the city network, avoiding other flagged
  segments where it can;
* **ambulance window** (risk ≥ 2) — a note for ambulance (108) crews: how long the road stays passable
  (the lead time before it turns deep) and the detour;
* **advisory draft** — one public advisory in Bengali and English naming the flagged places (Western
  digits; the public page's formatter renders Bengali digits);
* **live-wire hazard** (risk ≥ 2) — a request to the power utility (CESC / WBSEDCL) to inspect and, where
  needed, isolate supply along the flagged road. On 22–23 Sep 2025 most of the deaths in Kolkata were
  electrocutions (PTI). Proposal for officer approval.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from hydro.network import Network

__all__ = ["reroute", "ambulance_window", "advisory_draft", "live_wire", "GATE"]

GATE = {"state": "proposed", "required_role": "duty_officer", "officer": None, "decided_at": None}


def _base(pid: str, kind: str, subject: str, at: datetime, summary: str, actions: list[dict],
          labels: list[str]) -> dict[str, Any]:
    return {"proposal_id": pid, "kind": kind, "subject_urn": subject, "state": "proposed",
            "generated_at": at.isoformat(), "summary": summary, "actions": actions,
            "recommendation": {"decision": "await_officer"}, "human_gate": dict(GATE), "labels": labels}


def _via(net: Network, path: list[int]) -> list[str]:
    names: list[str] = []
    for p in path:
        n = net.segments[p].road_name
        if not names or names[-1] != n:
            names.append(n)
    return names


def reroute(net: Network, r: dict, flagged: set[int], at: datetime, labels: list[str]) -> dict[str, Any]:
    sid = r["segment_id"]
    path = net.alternative_path(sid, avoid=flagged - {sid})
    stamp = at.strftime("%Y%m%dT%H%MZ")
    deep = r.get("lead_time_deep_min")
    deep = r["lead_time_min"] if deep is None else deep
    when = "deep water now" if deep == 0 else f"deep water in about {deep} min"
    head = (f"{r['place']} ({r['road_name']}): waterlogging risk {r['risk_class']} "
            f"({r['expected_depth_band']}), {when}")
    if path:
        via = _via(net, path)
        summary = f"{head}; propose diverting traffic via {' → '.join(via)}."
        act = {"verb": "diversion", "target_urn": f"segment:{sid}",
               "params": {"via_segment_ids": path, "via_names": via,
                          "detour_length_m": round(sum(net.segments[p].length_m for p in path)),
                          "reason": "waterlogging"},
               "requires_officer": True, "reversible": True}
    else:
        summary = f"{head}; no detour on the city network that avoids flagged roads — propose closing to " \
                  "small vehicles with officer judgement on site."
        act = {"verb": "monitor", "target_urn": f"segment:{sid}", "params": {"reason": "waterlogging"},
               "requires_officer": True, "reversible": True}
    p = _base(f"hy-reroute-{sid}-{stamp}", "waterlogging_reroute", f"segment:{sid}", at, summary, [act], labels)
    p["situation"] = {k: r[k] for k in ("segment_id", "road_name", "place", "risk_class", "expected_depth_band",
                                        "lead_time_min", "lead_time_deep_min")}
    return p


def ambulance_window(net: Network, r: dict, flagged: set[int], at: datetime, labels: list[str]) -> dict[str, Any]:
    sid = r["segment_id"]
    path = net.alternative_path(sid, avoid=flagged - {sid})
    stamp = at.strftime("%Y%m%dT%H%MZ")
    lead = r.get("lead_time_deep_min")
    lead = r["lead_time_min"] if lead is None else lead
    window = f"passable for about {lead} min more" if lead > 0 else "already deep"
    detour = f"; use {' → '.join(_via(net, path))}" if path else "; no detour avoiding flagged roads"
    summary = f"Ambulance (108) note — {r['place']} ({r['road_name']}): {window}{detour}."
    act = {"verb": "advisory", "target_urn": f"segment:{sid}",
           "params": {"to_agency": "amb108", "passable_for_min": lead,
                      "via_segment_ids": path or [], "note": summary},
           "requires_officer": True, "reversible": True}
    return _base(f"hy-amb-{sid}-{stamp}", "ambulance_window", f"segment:{sid}", at, summary, [act], labels)


def advisory_draft(results: list[dict], at: datetime, horizon_min: int, labels: list[str]) -> dict[str, Any] | None:
    hit = [r for r in results if r["risk_class"] >= 2]
    if not hit:
        return None
    hit.sort(key=lambda r: (-r["risk_class"], r["lead_time_min"]))
    places_en: list[str] = []
    places_bn: list[str] = []
    for r in hit:
        if r["place"] not in places_en:
            places_en.append(r["place"])
            places_bn.append(r.get("place_bn") or r["place"])
        if len(places_en) == 6:
            break
    en = (f"Traffic advisory (draft): waterlogging is likely within the next {horizon_min} minutes at these "
          f"places: {', '.join(places_en)}. Please avoid these roads if you can. Do not touch electric poles or "
          "wires in standing water. Emergency: 112; ambulance (108).")
    bn = (f"ট্রাফিক পরামর্শ (খসড়া): আগামী {horizon_min} মিনিটের মধ্যে এই জায়গাগুলিতে জল জমার আশঙ্কা: "
          f"{', '.join(places_bn)}। সম্ভব হলে এই পথগুলি এড়িয়ে চলুন। জমা জলে বিদ্যুতের খুঁটি বা তার ছোঁবেন না। "
          "জরুরি প্রয়োজনে 112; অ্যাম্বুলেন্স (108)।")
    stamp = at.strftime("%Y%m%dT%H%MZ")
    act = {"verb": "advisory", "target_urn": "place:kolkata",
           "params": {"text_en": en, "text_bn": bn, "channel": "public advisory (after officer approval)",
                      "segment_ids": [r["segment_id"] for r in hit]},
           "requires_officer": True, "reversible": True}
    p = _base(f"hy-advisory-{stamp}", "public_advisory_draft", "place:kolkata", at,
              f"Public advisory draft (Bengali + English) for {len(places_en)} place(s).", [act], labels)
    p["text"] = {"en": en, "bn": bn}
    return p


def live_wire(r: dict, at: datetime, labels: list[str]) -> dict[str, Any]:
    sid = r["segment_id"]
    stamp = at.strftime("%Y%m%dT%H%MZ")
    summary = (f"Live-wire hazard — {r['place']} ({r['road_name']}): waterlogging risk {r['risk_class']} "
               f"({r['expected_depth_band']}). Propose asking the power utility (CESC / WBSEDCL) to inspect and, "
               "where needed, isolate street-light and overhead supply along this road.")
    act = {"verb": "advisory", "target_urn": f"segment:{sid}",
           "params": {"to_agency": "power", "request": "inspect and, where needed, isolate supply",
                      "why": "standing water; electrocution was the main cause of death on 22-23 Sep 2025 (PTI)"},
           "requires_officer": True, "reversible": True}
    p = _base(f"hy-wire-{sid}-{stamp}", "live_wire_hazard", f"segment:{sid}", at, summary, [act], labels)
    p["for_officer_approval"] = True
    return p
