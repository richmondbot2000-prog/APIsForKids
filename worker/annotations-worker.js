// annotations-worker.js — Cloudflare Worker that proxies Directory-page note
// saves to a commit on annotations.json in the GitHub repo.
//
// Deploy: see worker/SETUP.md for the dashboard walkthrough.
// Route:  book.togetherbook.net/api/annotations* (POST only — GET annotations
//         is served as a static file from the repo via GitHub Pages).
//
// Body:   { "key": "<email-or-username>", "phone": "+44 7…", "start_date": "2026-05-12" }
//         If both phone and start_date are empty/missing, the key is removed.
//
// Auth:   The route is gated by Cloudflare Access at the edge, so any request
//         that reaches the Worker has already passed @letme.com login. We
//         additionally require the Cf-Access-Jwt-Assertion header as a cheap
//         "did this really come through Access?" check.

const OWNER = "richmondbot2000-prog";
const REPO = "togetherbook";
const FILE_PATH = "annotations.json";
const BRANCH = "main";

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(req),
      });
    }
    if (req.method !== "POST") {
      return json({ error: "method not allowed" }, 405, req);
    }
    if (!req.headers.get("Cf-Access-Jwt-Assertion")) {
      return json({ error: "not authenticated via Cloudflare Access" }, 401, req);
    }
    if (!env.GITHUB_TOKEN) {
      return json({ error: "worker GITHUB_TOKEN secret not configured" }, 500, req);
    }

    let body;
    try { body = await req.json(); }
    catch { return json({ error: "invalid JSON body" }, 400, req); }
    const { key, phone, start_date, payroll_match } = body || {};
    if (!key || typeof key !== "string") {
      return json({ error: "missing 'key' (email or username)" }, 400, req);
    }

    const ghHeaders = {
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "apifk-annotations-worker",
    };

    // 1. Read current annotations.json (need the SHA for the PUT).
    const getRes = await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}?ref=${BRANCH}`,
      { headers: ghHeaders },
    );
    let current = { schema_version: 1, updated_at: null, annotations: {} };
    let sha = null;
    if (getRes.ok) {
      const data = await getRes.json();
      sha = data.sha;
      try {
        const parsed = JSON.parse(atob(data.content.replace(/\s/g, "")));
        if (parsed && typeof parsed === "object") current = parsed;
      } catch (e) { /* malformed file — treat as fresh */ }
    } else if (getRes.status !== 404) {
      const err = await getRes.text();
      return json({ error: "failed to read annotations.json", status: getRes.status, details: err.slice(0, 200) }, 502, req);
    }

    const annotations = (current.annotations && typeof current.annotations === "object")
      ? current.annotations
      : {};

    const cleanPhone = (phone || "").trim();
    const cleanStart = (start_date || "").trim();
    // payroll_match is either an object {employee_number, first_name, last_name, employer}
    // or null (explicit unlink). Treat any non-object as "not set", so the
    // existing phone+start_date-only callers don't accidentally clobber a link.
    const hasMatchKey = Object.prototype.hasOwnProperty.call(body || {}, "payroll_match");
    const cleanMatch = (payroll_match && typeof payroll_match === "object") ? payroll_match : null;
    const existing = (annotations[key] && typeof annotations[key] === "object") ? annotations[key] : {};
    const next = {};
    if (cleanPhone) next.phone = cleanPhone;
    if (cleanStart) next.start_date = cleanStart;
    // Preserve an existing payroll_match unless the caller explicitly set the
    // field (to either a new value or null).
    if (hasMatchKey) {
      if (cleanMatch) next.payroll_match = cleanMatch;
    } else if (existing.payroll_match) {
      next.payroll_match = existing.payroll_match;
    }
    if (Object.keys(next).length === 0) {
      delete annotations[key];
    } else {
      annotations[key] = next;
    }

    const out = {
      schema_version: 1,
      updated_at: new Date().toISOString(),
      annotations,
    };
    const newContent = b64Encode(JSON.stringify(out, null, 2) + "\n");
    const action = !annotations[key]
      ? "clear"
      : hasMatchKey && cleanMatch
        ? "link payroll"
        : hasMatchKey && !cleanMatch
          ? "unlink payroll"
          : "set";
    const commitMsg = `Directory note: ${action} ${key}`;

    const putRes = await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}`,
      {
        method: "PUT",
        headers: { ...ghHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({
          message: commitMsg,
          content: newContent,
          branch: BRANCH,
          sha: sha || undefined,
        }),
      },
    );
    if (!putRes.ok) {
      const err = await putRes.text();
      return json({ error: "failed to commit", status: putRes.status, details: err.slice(0, 200) }, 502, req);
    }

    return json({ ok: true, key, value: annotations[key] || null, all: out }, 200, req);
  },
};

function corsHeaders(req) {
  const origin = req.headers.get("Origin") || "*";
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Cf-Access-Jwt-Assertion",
    "Vary": "Origin",
  };
}

function json(obj, status, req) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...corsHeaders(req),
    },
  });
}

// btoa() encodes Latin-1. JSON might contain non-ASCII (e.g. accented names),
// so go through UTF-8 first.
function b64Encode(s) {
  const bytes = new TextEncoder().encode(s);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}
