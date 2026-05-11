#!/usr/bin/env python3
"""
Find brandwatch.json mentions we haven't notified about yet.

Reads brandwatch.json (the live snapshot) and brandwatch-seen.json
(IDs we've already emailed about). Emits:

  - notify-mentions.json    — list of new mentions to email about
                              (filtered to exclude BBB + Reviewcentre)
  - brandwatch-seen.json    — updated state file with new IDs added
  - prints "has_new=true|false" so the workflow can branch on it.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BRAND_FILE = ROOT / "brandwatch.json"
SEEN_FILE  = ROOT / "brandwatch-seen.json"
OUT_FILE   = ROOT / "notify-mentions.json"

# Sources we should NOT notify about. Lowercase, exact match on each
# mention's `source` field.
EXCLUDED_SOURCES = {"bbb", "reviewcentre", "review_centre"}


def main() -> int:
    if not BRAND_FILE.exists():
        print("has_new=false")
        print("brandwatch.json not present", file=sys.stderr)
        return 0

    brand = json.loads(BRAND_FILE.read_text())
    mentions = brand.get("mentions", [])
    seen_payload = (
        json.loads(SEEN_FILE.read_text()) if SEEN_FILE.exists() else {"ids": []}
    )
    seen = set(seen_payload.get("ids") or [])

    new = []
    new_ids: list[str] = []
    for m in mentions:
        mid = m.get("id")
        src = (m.get("source") or "").lower()
        if not mid:
            continue
        if mid in seen:
            continue
        new_ids.append(mid)               # mark as seen even if filtered
        if src in EXCLUDED_SOURCES:
            continue
        new.append(m)

    OUT_FILE.write_text(json.dumps(new, indent=2))
    # Persist seen with the union of old + every id observed this run, so
    # filtered-out sources don't re-trigger on the next pass.
    SEEN_FILE.write_text(
        json.dumps({"ids": sorted(seen | set(new_ids))}, indent=2)
    )

    print(f"has_new={'true' if new else 'false'}")
    print(f"new_total_including_filtered={len(new_ids)}")
    print(f"new_after_filter={len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
