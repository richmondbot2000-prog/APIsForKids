"""
Trustpilot-only retry: re-runs `fetch_trustpilot` against every brand and
merges any new reviews into the existing brandwatch.json. Used when the
morning brandwatch run logged `source_status.trustpilot.ok = false` (e.g.
a transient ScraperAPI 500) so the snapshot is otherwise complete but TP
is missing fresh reviews.

Bypasses the same-day guard because it only touches Trustpilot fields:
- merges new mentions into the existing list (dedup by id)
- updates totals.all + totals.by_source.trustpilot + totals.by_brand
- rewrites source_status.trustpilot
- bumps updated_at
- preserves snapshot_date (this is NOT a fresh snapshot)

Auth: same SCRAPERAPI_KEY as scan_brandwatch.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Reuse the production scanner module so the brand list, fetch helper,
# precision filters, and ScraperAPI retry logic stay in lockstep.
sys.path.insert(0, str(Path(__file__).parent))
import scan_brandwatch as bw  # noqa: E402


BRANDWATCH_PATH = Path("brandwatch.json")


def main() -> int:
    if not os.environ.get("SCRAPERAPI_KEY"):
        print("SCRAPERAPI_KEY not set — cannot retry Trustpilot", file=sys.stderr)
        return 1
    if not BRANDWATCH_PATH.exists():
        print("brandwatch.json missing — run scan_brandwatch.py first", file=sys.stderr)
        return 1

    data = json.loads(BRANDWATCH_PATH.read_text(encoding="utf-8"))
    mentions: list[dict] = data.get("mentions") or []
    known_tp_ids: set[str] = {m["id"] for m in mentions if m.get("source") == "trustpilot" and m.get("id")}
    print(f"loaded brandwatch.json: snapshot={data.get('snapshot_date')} TP archive={len(known_tp_ids)}")

    fresh: list[dict] = []
    fatal_error: str | None = None
    for brand in bw.BRANDS:
        try:
            rows = bw.fetch_trustpilot(brand, known_ids=known_tp_ids)
            print(f"  {brand['key']}: fetched {len(rows)} new TP review(s)")
            fresh.extend(rows)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            # Match the scanner's own redaction: never leak the api_key query.
            import re
            msg = re.sub(r"(api\.scraperapi\.com/?\?)[^ ]+", r"\1<redacted>", msg)
            print(f"  {brand['key']}: FAILED — {msg}")
            fatal_error = msg
            break

    if fatal_error:
        data.setdefault("source_status", {})["trustpilot"] = {
            "ok": False,
            "fetched": 0,
            "error": fatal_error[:200],
        }
        data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        BRANDWATCH_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("Trustpilot retry failed — source_status updated, totals untouched")
        return 2

    if fresh:
        # Dedup belt-and-braces (fetch_trustpilot already filters by known_ids,
        # but a brand's fresh set could overlap another brand's).
        new_ids = {m["id"] for m in fresh if m.get("id")}
        merged = [m for m in mentions if m.get("id") not in new_ids] + fresh
        merged.sort(key=lambda m: (m.get("date") or ""), reverse=True)
        data["mentions"] = merged

        # Recount Trustpilot total + grand total
        totals = data.setdefault("totals", {})
        by_source = totals.setdefault("by_source", {})
        by_brand  = totals.setdefault("by_brand", {})
        by_source["trustpilot"] = sum(1 for m in merged if m.get("source") == "trustpilot")
        for b in bw.BRANDS:
            by_brand[b["key"]] = sum(1 for m in merged if m.get("brand") == b["key"])
        totals["all"] = len(merged)

    data.setdefault("source_status", {})["trustpilot"] = {
        "ok": True,
        "fetched": len(fresh),
        "error": None,
    }
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    BRANDWATCH_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"updated brandwatch.json: +{len(fresh)} TP review(s), "
        f"TP total now {data['totals']['by_source']['trustpilot']}, "
        f"grand total {data['totals']['all']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
