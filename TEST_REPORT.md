# Campus Connect — Test & Feature-Working Report

Date: 2026-11-10 · Django 5.2.6 · SQLite · 104 unit tests + 38 end-to-end checks, all green.

## Test suites at a glance

| Layer | Location | Result |
|---|---|---|
| Unit tests | `accounts/tests.py` (9) | PASS |
| Unit tests | `matching/tests.py` (19) | PASS |
| Unit tests | `questionnaire/tests.py` (27) | PASS |
| Unit tests | `chat/tests.py` (7) | PASS |
| Unit tests | `notifications/tests.py` (5) | PASS |
| Unit tests | `profiles/tests.py` (11) | PASS |
| Unit tests | `admin_dashboard/tests.py` (7) | PASS |
| Unit tests | `events/tests.py` (11) — **new** | PASS |
| Unit tests | `communities/tests.py` (8) — **new** | PASS |
| End-to-end | `e2e_suite/e2e_main.py` (38 checks) | **38/38 PASS** |

How to run unit tests:
`python manage.py test accounts matching questionnaire connections chat notifications profiles admin_dashboard events communities`

How to run E2E: see `e2e_suite/README.md` (console email backend, seed commands, then the driver).

## How each feature is working (verified end-to-end, not just asserted)

### 1. Signup & onboarding — working
Full flow verified for 5 fresh accounts: signup form → 6-char email OTP (delivered via console
backend; a deliberately wrong code is rejected with an attempt countdown; the correct code from the
log activates the account and logs it in) → profile setup → AI-consent intro → all 24 questionnaire
questions answered → marked 100% complete and questionnaire-completed on the profile. Duplicate
email and mismatched passwords are both rejected with clear errors. On a delivery failure, no
pending account is created (regression-tested in `accounts/tests.py`).

### 2. Login / logout — working (previous bug fixed this session)
Logout → login returns to `/home/`; a failed login creates no session.
**Fixed:** `login.html` previously never rendered the Django messages framework, so a wrong
password re-rendered the page silently. It now shows a red "Invalid email or password." banner.
Locked in by `LoginErrorVisibilityTests` (2 new regression tests) and the E2E "BUG CHECK", which
now passes.

### 3. Matching — working
- Match list returns percentage-sorted candidates with the 0.70-questionnaire / 0.30-profile
  weighting: identical answers + same university + shared interests → 100%; divergent answer
  patterns → 33/25/10% tiers, exactly as the formula predicts.
- **Privacy masking works at two layers:** in the match-list API, unconnected profiles appear as
  "??? ???" with photo and details hidden; on the profile detail page, a "Compatibility Profile"
  private preview is rendered with name/photo/age/city/gender/languages/bio/university/major/
  year/interests all blanked **server-side** (verified: none of that text exists in the HTML)
  while questionnaire category scores are shown with conversation-starter reflections.
- Request → "New connection request" notification → accept via the notification endpoint →
  connection `ACCEPTED` on both sides → full name/university/major/interests unlock on the match
  list and the full profile page.
- Open nit (unchanged): `/api/matches/<id>/compatibility/` returns `reasons`/`shared_interests`
  as `null` when empty, while the match-list endpoint always returns arrays — frontend should
  null-coalesce.

### 4. Chat — working
Text messages flow both directions over the multipart form endpoint (same mechanism as the UI's
FormData). Polling shows both parties' messages; unread counts are correct; the chat home lists
the accepted contact with the latest message. A PNG image message is accepted (returns
`image_url`); uploading a `.txt` as an image is rejected with a clear 400 naming the accepted
types; an empty message (no text, no image) is 400; an unconnected user gets 403 on the send
endpoint and 404 on the conversation page.

### 5. Communities — working
Five seeded communities render with member counts and category chips; text search matches
name/description/category; the category filter treats "All" as no-filter; join/leave via the
POST toggle persists across requests; the "can create" flag is true only for superusers. All
covered by the new `communities/tests.py` (8 tests) and E2E checks.

### 6. Events — working
Demo events list on the home page; registration (name/email/phone, 7+ digits) creates an
`EventRegistration`, adds the attendee to the event, and creates a success notification; a
duplicate registration is blocked with an "already registered" flash message (form validation is
skipped by design — the guard runs first); a short phone number is rejected with a flashed error
and no row is created. Covered by the new `events/tests.py` (11 tests) and E2E checks.

### 7. Notifications — working
Connection requests, event registrations, and accept/cancel actions all produce inbox entries;
unread → mark-read works; accepting a request straight from the notification updates the
connection on both sides; either connected user can cancel a connection.

### 8. Questionnaire summary & AI insights — working
After completion, both the `/api/questionnaire/summary/` JSON and the summary page render with
per-category scores and strongest-category. AI category reflections: consent is required and
must be stored on the profile; category scores are hashed into a fingerprint so unchanged
answers never re-call the API; only **category names + scores** are sent to Groq (never answer
text, names, or personal data). Graceful degradation verified in all three states: no API key →
503 "not configured"; key set but call unreachable → 502 with a friendly "try again later";
working key → 200 with generated summaries. No 500 crash path found.

## What changed this session

New test files:
- `events/tests.py` — forms (hex color, phone validation), login-required pages,
  POST-only register, successful registration + notification + attendee, duplicate guard,
  invalid-form rejection.
- `communities/tests.py` — login-required pages, member counts, search & category filters,
  join/leave toggle, POST-only, 404 on unknown community, superuser `can_create` flag.

Repaired/extended existing files:
- `accounts/tests.py` — `LoginErrorVisibilityTests`: failed login must show the error on the
  page; successful login must redirect home.
- `questionnaire/tests.py` — the Groq model assertion now patches `GROQ_MODEL` instead of
  depending on the machine's `.env` (hermetic).
- `e2e_suite/e2e_main.py` — fixed a driver crash (non-string detail values broke the summary
  loop) and corrected 4 stale assertions: profile-masking check now targets the real
  "Compatibility Profile" preview behavior; communities check matches the HTML-escaped `&amp;`;
  event short-phone check now uses a *different* event (the duplicate guard would otherwise
  short-circuit) and reads the flashed message after the redirect; insights check now targets an
  *unconnected public* profile, since the endpoint returns 404 by design for connected pairs.
- `e2e_suite/e2e_helpers.py` — `dump_user_ids` no longer hardcodes a previous session's `/tmp`
  paths; it inherits the caller's environment and `CC_PROJECT` directory.

App code fix:
- `templates/accounts/login.html` — renders the Django messages framework (red flash banner for
  errors, green for success). This is the one genuine bug found on 2026-11-04; it is now fixed
  and regression-tested.

## Remaining known items

- Minor API inconsistency: compatibility detail returns `null` reasons/shared_interests when
  empty vs arrays in the list endpoint (cosmetic; null-coalesce on the client).
- E2E runs against a *fresh* database each time; re-seed with `seed_questionnaire --replace`
  and `seed_demo_data` before every run.
