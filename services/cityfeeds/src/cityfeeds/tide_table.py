"""The PUBLISHED Hooghly tide table (Garden Reach / Kolkata) — and why it is not here yet.

Syama Prasad Mookerjee Port, Kolkata publishes the river's tide tables (prepared with the Survey of India from the
port's gauges at Tribeni, Garden Reach, Diamond Harbour and Haldia). Checked from this box on 28 Oct 2026:

* ``https://smp.smportkolkata.in/`` presents a TLS certificate this box cannot verify (curl exit 60), and the
  plain-http address answers 503 from an upstream proxy; the old ``kolkataporttrust.gov.in`` does not answer.
  Certificate checks are never switched off to get round that.
* No other machine-readable copy published by the port or the Survey of India was found.

So ``GET /feeds/tide-table`` says PUBLISHED: UNAVAILABLE with the reason, and shows the hydro service's MODELLED
high and low waters (``GET /hydro/tide``, Garden Reach transferred from Diamond Harbour constants) as the reference
the city works from today. ``compare()`` is ready for the day a published table can be read: it pairs each
published high/low water with the nearest modelled one of the same kind and reports the time and height errors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

__all__ = ["fetch_hydro_tide", "tide_table_view", "compare", "PORT_CHECK"]

PORT_CHECK = {
    "publisher": "Syama Prasad Mookerjee Port, Kolkata",
    "urls_checked": ["https://smp.smportkolkata.in/", "http://smp.smportkolkata.in/", "https://kolkataporttrust.gov.in/"],
    "checked_on": "2026-10-28",
    "result": "not readable from this box: the https site's certificate cannot be verified (curl exit 60); http "
              "answers 503 from a proxy; the old domain does not answer",
}


async def fetch_hydro_tide(client: httpx.AsyncClient, hydro_url: str) -> Any:
    r = await client.get(f"{hydro_url.rstrip('/')}/hydro/tide", params={"hours": 48})
    r.raise_for_status()
    return r.json()


def compare(published: list[dict], modelled: list[dict]) -> dict[str, Any]:
    """Each published extreme vs the nearest modelled extreme of the same kind: minutes and metres apart."""
    pairs = []
    for p in published:
        pt = datetime.fromisoformat(p["at"])
        same = [m for m in modelled if m["kind"] == p["kind"]]
        if not same:
            continue
        m = min(same, key=lambda m: abs((datetime.fromisoformat(m["at"]) - pt).total_seconds()))
        pairs.append({"kind": p["kind"], "published_at": p["at"], "modelled_at": m["at"],
                      "dt_min": round((datetime.fromisoformat(m["at"]) - pt).total_seconds() / 60),
                      "published_m": p["level_m"], "modelled_m": m["level_m"],
                      "dh_m": round(m["level_m"] - p["level_m"], 2)})
    if not pairs:
        return {"pairs": [], "mean_abs_dt_min": None, "mean_abs_dh_m": None}
    return {"pairs": pairs,
            "mean_abs_dt_min": round(sum(abs(x["dt_min"]) for x in pairs) / len(pairs)),
            "mean_abs_dh_m": round(sum(abs(x["dh_m"]) for x in pairs) / len(pairs), 2)}


def tide_table_view(hydro: dict | None, hydro_error: str | None = None) -> dict[str, Any]:
    extremes = (hydro or {}).get("extremes") or []
    return {
        "published": {"label": "UNAVAILABLE", **PORT_CHECK, "highs_lows": []},
        "modelled": {"label": "MODELLED", "source": "Sahoshi hydro service, GET /hydro/tide (Garden Reach, approximate)",
                     "station": (hydro or {}).get("station"), "now": (hydro or {}).get("now"),
                     "highs_lows": extremes, "error": hydro_error},
        "comparison": {"status": "not possible: no published table could be read",
                       "method": "nearest modelled extreme of the same kind; minutes and metres apart"},
    }
