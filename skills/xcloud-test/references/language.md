# Language testing — what non-English customers actually see

xCloud ships 20 languages: en, bn, da, de, es, fr, hi, hu, id, it, ja, ko, nl, no, pt, ru, sc (Simplified
Chinese), tc (Traditional Chinese), th, vi. None is right-to-left. Facts the checks rely on (verified 2026-10-07):

| Layer | How it is chosen | What a gap looks like |
|---|---|---|
| Dashboard (Vue) | `users.language`, else the white-label brand's language; vue-i18n loads `resources/lang/<lang>.json` lazily; keys are the English text | **silent English** (warnings are switched off) |
| Server messages (PHP `__()`, flashes, validation) | same locale per request (`SetLanguage` middleware) | English, or a **raw key** (`emails.subject`) for dotted group keys |
| Validation messages | `resources/lang/<lang>/validation.php`; most languages have no such file | English validation text inside a translated page |
| Notifications (mail, Slack, Telegram, WhatsApp, alerts) | `teams.notification_language`, or the brand's language for white-label teams: **not** the user's language | email in the wrong language, or mixed |

Baseline facts on `dev` (2026-10-07): every language misses the same 494 of 4,938 keys; 7 translations drop
placeholders (e.g. hi `":list and :extra more"` → no `:list`, no `:extra`). These are pre-existing: report only
what this PR adds or makes worse.

## 1. Static audit (main session, Phase 1; free)

```bash
python3 ~/.claude/skills/xcloud-test/scripts/lang_audit.py --base origin/<base> --head origin/pr/<N>
```

| Finding | Severity | Meaning |
|---|---|---|
| `PLACEHOLDER_MISMATCH` | high | a translation drops or renames `:name` / `{count}`: values vanish or print literally |
| `MISSING_GROUP_KEY` | high (en) / medium | a dotted key (`emails.x`) missing: the raw key is shown |
| `NOT_IN_LANG_FILES` | medium | new string never added to `en.json`: no language can translate it |
| `UNTRANSLATED` | medium | in `en.json`, missing in some languages: silent English for them |
| `HARDCODED_CANDIDATE` | medium | literal text in a template, no `$t()`/`__()`: never translatable |

Each finding is a lead. Turn the ones on customer-visible paths into `[lang]` checks and confirm them on the
running page or email. A string the PR adds that nobody can see (log line, admin-only Nova text) is not a finding.

## 2. Live checks (executors, `[lang]` checks)

Switch the account's language for the check, then **put it back** (it is a stored user setting):

```
app_tinker: echo \App\Models\User::where('email','user1@xcdev.test')->value('language') ?? 'null';   # remember it
app_call {environment, method: "POST", path: "/user/language", body: {"lang": "de"}, as: "user1@xcdev.test"}
... checks ...
app_call {..., body: {"lang": "<previous or en>"}, as: "user1@xcdev.test"}
```

Pick languages by what can break, not all 20:
- **de** (or hu, ru): long words and longer strings: truncation, overflow, buttons that wrap or clip.
- **ja** or **sc/tc**: no spaces between words: line breaking, ellipsis, CJK glyphs.
- **th**, **hi**, **bn**: complex scripts: missing glyphs (tofu boxes), clipped diacritics in tight line heights.
- every language the static audit flagged.

On each changed page (`page_check {path, as, viewport: {"width": 1280, "height": 1400}}`, plus `viewport: "mobile"` for one long language):
1. **Silent English**: English words inside a translated page, especially the PR's new strings, toasts and
   empty states. Trigger the toasts, errors and empty states the PR adds; they are the strings most often missed.
2. **Raw keys or placeholders**: text like `emails.subject`, `messages.foo`, `:count`, `{name}` on screen.
3. **Layout**: text clipped, overlapping, or pushed out of buttons, table headers, badges, modals; horizontal
   scroll at mobile width.
4. **Glyphs**: boxes or missing characters in th/hi/bn/ja.
5. **Formats**: dates, numbers, sizes and currency on the changed page: consistent with the rest of the page
   in that language (xCloud may keep some formats English; flag inconsistency within the page, not English itself).
6. **Plurals**: 0, 1 and many of whatever the PR counts (`1 sites`, `0 servers`).
7. **Validation**: submit a changed form with invalid input in that language; note which messages come back in
   English.

Emails and notifications (when the PR sends or changes one): set the team's `notification_language` (remember and
restore it), trigger the notification, then read it from the environment's Mailpit:

```
cp_exec: curl -s 'http://127.0.0.1:8025/api/v1/messages?limit=5' | python3 -c 'import json,sys; [print(m["ID"], m["Subject"]) for m in json.load(sys.stdin)["messages"]]'
cp_exec: curl -s 'http://127.0.0.1:8025/api/v1/message/<ID>' | python3 -c 'import json,sys; m=json.load(sys.stdin); print(m["Subject"]); print(m["Text"][:2000])'
```

Check: subject and body in the team's language, not the acting user's; no raw keys; placeholders filled; a
white-label team's mail uses the brand's language and name, never "xCloud".

## 3. Recording

`[lang]` results use the executor schema. Evidence: the screenshot showing the English/raw/clipped text with the
language named in `summary`, or the Mailpit subject and body excerpt. `pre_existing: true` when the same gap is
on the base branch (most of the 494 missing keys are).
