#!/usr/bin/env python3
"""Nightly doc refresh — keeps SPEC.md + wiki context docs in sync with
the last 24h of structural commits on the togetherbook repo.

Designed to run unattended from a GitHub Actions cron at 02:00 UK local.
Companion workflow: .github/workflows/nightly-doc-refresh.yml.

"Structural" excludes data-refresh commits (Refresh *, Wall:, Admins:,
People: update #, Payroll:, Workspace:, ...) so the docs don't churn
nightly with noise."""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
import zoneinfo
from pathlib import Path

UK = zoneinfo.ZoneInfo("Europe/London")

EXCLUDE_PREFIXES = (
    "refresh", "wall:", "admins:", "people:", "payroll:",
    "workspace:", "auth0:", "trustpilot:", "discord:", "telegram:",
    "hibp:", "groups:", "directory:", "lookalikes:", "1st-contact:",
    "first-contact:", "comms:", "source-quality:", "row counts:",
    "row-counts:", "lookalike:", "pipeline samples:", "brokers:",
    "yesterday:", "payouts:", "top-ups:", "topups:", "brandwatch:",
    "pending-transfers:", "auto:",
)

START_MARK = "<!-- NIGHTLY-DOC-REFRESH:BEGIN -->"
END_MARK   = "<!-- NIGHTLY-DOC-REFRESH:END -->"
KEEP_DAYS  = 14


def run(cmd, cwd=None):
    out = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return out.stdout


def is_structural(subject):
    s = subject.strip().lower()
    return not any(s.startswith(p) for p in EXCLUDE_PREFIXES)


def recent_structural_commits(repo, since_iso):
    log = run(["git", "log", f"--since={since_iso}", "--no-merges",
               "--pretty=%h\t%s"], cwd=repo)
    rows = []
    for line in log.splitlines():
        if "\t" not in line:
            continue
        h, subj = line.split("\t", 1)
        if is_structural(subj):
            rows.append((h.strip(), subj.strip()))
    return rows


def render_activity_block(commits, today):
    if not commits:
        body = "_No structural changes._"
    else:
        body = "\n".join(f"- `{h}` {subj}" for h, subj in commits)
    return (
        f"{START_MARK}\n"
        f"\n"
        f"### Recent activity — {today.isoformat()}\n"
        f"\n"
        f"{body}\n"
        f"\n"
        f"{END_MARK}\n"
    )


def upsert_activity_block(file_path, block, today):
    if not file_path.exists():
        return False
    original = file_path.read_text()

    pattern = re.compile(
        re.escape(START_MARK) + r".*?" + re.escape(END_MARK) + r"\n?",
        re.DOTALL,
    )
    existing_blocks = pattern.findall(original)
    stripped = pattern.sub("", original)

    cutoff = today - _dt.timedelta(days=KEEP_DAYS)
    date_re = re.compile(r"### Recent activity — (\d{4}-\d{2}-\d{2})")
    kept = []
    for b in existing_blocks:
        m = date_re.search(b)
        if not m:
            continue
        d = _dt.date.fromisoformat(m.group(1))
        if d == today:
            continue
        if d >= cutoff:
            kept.append(b)

    new_blocks = [block] + kept
    new_section = "\n".join(new_blocks).rstrip() + "\n"

    if "\n---\n" in stripped:
        head, rest = stripped.split("\n---\n", 1)
        new_text = f"{head}\n---\n\n{new_section}\n{rest.lstrip()}"
    else:
        lines = stripped.splitlines(keepends=True)
        h1_idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), 0)
        new_text = "".join(lines[: h1_idx + 1]) + "\n" + new_section + "\n" + "".join(lines[h1_idx + 1 :])

    if new_text == original:
        return False
    file_path.write_text(new_text)
    return True


def touch_spec_last_reviewed(spec, today, commits):
    if not spec.exists() or not commits:
        return False
    txt = spec.read_text()
    line_re = re.compile(r"^\*\*Last reviewed:\*\*.*$", re.MULTILINE)
    if not line_re.search(txt):
        return False
    summary = "; ".join(s for _, s in commits[:5])
    if len(commits) > 5:
        summary += f"; +{len(commits) - 5} more"
    new_line = f"**Last reviewed:** {today.isoformat()} (nightly auto-refresh) — {summary}"
    new_txt, n = line_re.subn(new_line, txt, count=1)
    if n == 0 or new_txt == txt:
        return False
    spec.write_text(new_txt)
    return True


def commit_and_push(repo, files, message):
    rels = [str(f.relative_to(repo)) for f in files]
    run(["git", "add", "--"] + rels, cwd=repo)
    status = run(["git", "status", "--porcelain", "--"] + rels, cwd=repo)
    if not status.strip():
        return False
    run(["git", "commit", "-m", message], cwd=repo)
    run(["git", "push"], cwd=repo)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--togetherbook", required=True, type=Path)
    ap.add_argument("--wiki", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    now_uk = _dt.datetime.now(UK)
    if not args.force and now_uk.hour != 2:
        print(f"nightly doc refresh: skipped (UK hour is {now_uk.hour:02d}, gate is 02)")
        return 0

    today = now_uk.date()
    since_iso = (now_uk - _dt.timedelta(hours=24)).isoformat(timespec="seconds")

    commits = recent_structural_commits(args.togetherbook, since_iso)
    block = render_activity_block(commits, today)

    changed_tb = []
    changed_wiki = []

    spec = args.togetherbook / "SPEC.md"
    if touch_spec_last_reviewed(spec, today, commits):
        changed_tb.append(spec)

    if args.wiki:
        for relname in ("CLAUDE_CONTEXT.md", "Overview/07_TogetherBook_Site.md"):
            target = args.wiki / relname
            if upsert_activity_block(target, block, today):
                changed_wiki.append(target)

    if args.dry_run:
        print(f"DRY RUN - would change {len(changed_tb)} togetherbook file(s) "
              f"and {len(changed_wiki)} wiki file(s).")
        print(f"Structural commits in last 24h: {len(commits)}")
        for h, s in commits:
            print(f"  {h} {s}")
        return 0

    sha = "(none)"
    if changed_tb:
        if commit_and_push(args.togetherbook, changed_tb,
                           f"docs: nightly refresh {today.isoformat()}"):
            sha = run(["git", "rev-parse", "--short", "HEAD"],
                      cwd=args.togetherbook).strip()
    if changed_wiki and args.wiki:
        commit_and_push(args.wiki, changed_wiki,
                        f"docs: nightly refresh {today.isoformat()}")

    print(f"nightly doc refresh: {len(commits)} structural commits scanned; "
          f"togetherbook updated: {bool(changed_tb)} ({sha}); "
          f"wiki updated: {bool(changed_wiki)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
