---
name: session-start
description: Start a coordinated TogetherBook work session. Generates a per-session ID, claims a scope in _inflight.md, and pulls the latest from main so you start fresh.
---

# /session-start

Run when you sit down to a non-trivial chunk of work on the TogetherBook repo. Cheap, takes ~10 seconds, kills mid-task file collisions with the other Claude Code session.

## What to do

1. **Pull latest.** `cd /Users/richmondrobot/Desktop/togetherbook && git pull --rebase --quiet`. If the rebase has conflicts, stop — surface them to the user and don't proceed.

2. **Read `_inflight.md`.** If another session has a row that overlaps with what you're about to do, tell the user and ask whether to coordinate (work on something else, or proceed anyway). Don't silently double-up.

3. **Generate a session ID.** Six lowercase alphanumeric characters. Bash one-liner:
   ```
   SID=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_lowercase+string.digits) for _ in range(6)))")
   echo "$SID"
   ```
   **Remember this ID for the rest of the session** — every commit footer should carry `Session-Id: <SID>`. If you're unsure later, grep `_inflight.md` for your row.

4. **Recent activity sweep.** `git log --since='6 hours ago' --pretty='%h %an %s' --no-merges` — see what the other session shipped in the last 6 hours so you have context. Mention anything surprising in your first reply.

5. **Ask the user for the scope** (one sentence — "what are you about to do?") UNLESS the user has already told you in the message that triggered this skill. Examples: "wire the Display name editor on the profile page", "fix the Wall pagination bug", "audit the docs".

6. **Append your row to `_inflight.md`.** Edit the file: replace `| _no active sessions_ | | | |` with your row (or, if other rows exist, add yours below). Use `date -u +%H:%M` for the timestamp. The row format:
   ```
   | 15:42 UTC | session=abc123 | <scope keyword> | <one-line note> |
   ```
   `<scope keyword>` should be one of: `worker`, `ui`, `scanner`, `docs`, `infra`, `data` — so the other session can grep quickly.

7. **Commit + push.**
   ```
   git add _inflight.md && git commit -m "inflight: session=$SID starting on $SCOPE

   Session-Id: $SID
   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>" && git push
   ```

8. **Report back to the user.** One line: "Session `abc123` open — claimed `<scope>`. <Anything noteworthy from the last 6 hours of commits>."

## Notes

- The session ID is intentionally short (6 chars) so the commit footer line stays one line. `git log --grep="Session-Id: abc123"` lists every commit you shipped this session.
- If you forget to `/session-start`, you can still hand-craft `Session-Id: <id>` footers — but the `_inflight.md` claim won't be there, so the other session can't see what you're touching.
- This skill is committed at `.claude/skills/session-start/SKILL.md` in the togetherbook repo, so both Claude Code sessions sharing the repo see the same definition.
