"""Agency registry — the closed set of dispatchable agencies.

Civic Volunteers (সিভিক ভলান্টিয়ার) work alongside the Kolkata Police and
the Kolkata Traffic Police at crossings, ghats and crowded places — the
ground-level eyes-and-ears arm beside the police.  Making them a
first-class AGENCY ACTOR means: they are dispatchable through the same
channel as police/traffic, their units are emulated on the same graph, and
every dispatch of a civic-volunteer unit carries the same human-approval and
audit trail as any other agency — Sahoshi strengthens government capability;
volunteers are coordinated, never automated.  The agency CODE stays
``jan_rakshak`` (the migration 011 CHECK value and the API value); only its
labels say "Civic Volunteers".

The registry is deliberately CLOSED (mirrors the migration 011 CHECK):
every unit surfaced anywhere carries one of these codes and labels, so
the canvas/ops board can badge deterministically.

Ethics (C6): agencies and units — never persons.  No name/face fields.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Agency:
    code: str          # migration 011 CHECK value
    label: str         # UI label (EN)
    label_native: str  # UI label (Bengali)
    role: str


JAN_RAKSHAK = Agency(
    code="jan_rakshak",
    label="Civic Volunteers",
    label_native="সিভিক ভলান্টিয়ার",
    role="citizen volunteer coordination, first responder support",
)

AGENCIES: dict[str, Agency] = {
    a.code: a
    for a in (
        JAN_RAKSHAK,
        Agency("police", "Police Control", "পুলিশ কন্ট্রোল", "law & order"),
        Agency("traffic", "Traffic Police", "ট্রাফিক পুলিশ", "traffic management"),
        Agency("ambulance", "Ambulance (108)", "অ্যাম্বুলেন্স (১০৮)", "emergency medical"),
        Agency("fire", "Fire & Emergency", "দমকল ও জরুরি পরিষেবা", "fire & rescue"),
    )
}


def agency_label(code: str) -> str:
    agency = AGENCIES.get(code)
    return agency.label if agency else code


def is_agency(code: str) -> bool:
    return code in AGENCIES


__all__ = ["AGENCIES", "JAN_RAKSHAK", "Agency", "agency_label", "is_agency"]
