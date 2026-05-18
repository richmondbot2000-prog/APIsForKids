---
name: session-end
description: Close a coordinated TogetherBook work session. Removes your row from _inflight.md so the other session sees you've moved on.
---

# /session-end

Run when you've shipped (or paused) your session's work. Quick — removes your row from `_inflight.md` and commits.

## What to do

1. **Pull latest.** `cd /Users/richmondrobot/Desktop/togetherbook && git pull --rebase --quiet`. If conflicts, stop — surface them to the user.

2. **Identify your session ID.** From context (you should remember it from `/session-start`), or by grep — `grep "session=" _inflight.md` and pick yours by scope/note.

3. **Remove your row from `_inflight.md`.** If yours was the only row, restore the `| _no active sessions_ | | | |` placeholder.

4. **Commit + push** with your Session-Id footer:
   ```
   git add _inflight.md && git commit -m "inflight: session=$SID done

   Session-Id: $SID
   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>" && git push
   ```

5. **Report back to the user.** One line: "Session `<id>` closed. Shipped: <one-line recap>." Optionally remind them they can find everything this session shipped with `git log --grep='Session-Id: <id>'`.

## When NOT to run this

- If you're about to step away briefly (under an hour) and plan to come back to the same scope, leave your row up. Other session won't pile in.
- If the user explicitly says "we're pausing, I'll come back to this." Leave the row + maybe append `(paused HH:MM)` to your note so it's obvious.

## Stale-row cleanup

If you `/session-start` and see a row older than 4 hours that doesn't look like an actual in-flight session (no commits with that Session-Id in the last hour), it's safe to remove as part of your own session-start.
