#!/usr/bin/env python3
"""Daily birthday post generator.

Scans people.json for anyone whose date_of_birth's month+day matches
today's UK date, and adds a "Happy Birthday <name>" post (authored by
TogetherBook) to wall.json. Deduped via stable post IDs of the form
`post_birthday_<YYYY>_<url_slug>` so the daily GH-Action re-run is
idempotent and one post per person per year is the steady state.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
PEOPLE_JSON = ROOT / "people.json"
WALL_JSON = ROOT / "wall.json"

# A public happy-birthday GIF served from Giphy's CDN. Used as the
# post's only photo so the wall renders it inline at full width.
BIRTHDAY_GIF = "https://media.giphy.com/media/g5R9dok94mrIvplmZd/giphy.gif"

SYSTEM_EMAIL = "togetherbook@system"
SYSTEM_NAME = "TogetherBook"


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main() -> int:
    london = ZoneInfo("Europe/London")
    now_uk = datetime.now(london)
    md = now_uk.strftime("%m-%d")
    year = now_uk.year

    people_doc = json.loads(PEOPLE_JSON.read_text())
    people = people_doc.get("people", [])

    birthday_people = []
    for p in people:
        if p.get("suspended") or p.get("deletion_time"):
            continue
        dob = p.get("date_of_birth") or ""
        if len(dob) >= 10 and dob[5:10] == md:
            birthday_people.append(p)

    if not birthday_people:
        print(f"No birthdays on {now_uk.date().isoformat()}")
        return 0

    wall_doc = json.loads(WALL_JSON.read_text())
    posts = wall_doc.setdefault("posts", [])
    existing_ids = {p.get("id") for p in posts}

    # Stamp every post for "today" at 07:00 UK local time so the wall
    # orders them just above the start of the work day.
    created_at = iso_z(now_uk.replace(hour=7, minute=0, second=0, microsecond=0))

    added = 0
    for person in birthday_people:
        slug = (person.get("url_slug") or person.get("id") or "unknown").lower()
        post_id = f"post_birthday_{year}_{slug}"
        if post_id in existing_ids:
            continue
        name = person.get("name") or slug
        post = {
            "id": post_id,
            "author_email": SYSTEM_EMAIL,
            "author_name": SYSTEM_NAME,
            "created_at": created_at,
            "body": (
                f"Happy Birthday {name}! \U0001F382\U0001F388\U0001F389\n\n"
                "Wishing you a wonderful day from everyone at TogetherBook."
            ),
            "photos": [BIRTHDAY_GIF],
            "channel": None,
            "reactions": {},
            "comments": [],
        }
        posts.insert(0, post)
        added += 1
        print(f"Added birthday post for {name} ({post_id})")

    if added:
        wall_doc["updated_at"] = iso_z(datetime.now(timezone.utc))
        WALL_JSON.write_text(json.dumps(wall_doc, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote {added} new birthday post(s) to wall.json")
    else:
        print(f"All {len(birthday_people)} birthday post(s) already exist for {now_uk.date().isoformat()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
