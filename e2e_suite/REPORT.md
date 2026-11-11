# Campus Connect — End-to-End Test Report

Date: 2026-11-10 (re-run) · Runner: Django 5.2.6, fresh SQLite, console email backend (OTP read from server log — no real email sent).
First run: 2026-11-04.

## Scope
Real HTTP flows driven with per-user sessions that mirror the browser (forms + CSRF, JSON APIs, multipart chat). 10 users in play: 5 freshly signed up (Mani, Divya, Arjun, Sara, Vikram) + 5 seeded demo profiles, so matching had a rich candidate pool.

## Result: 38/38 checks PASS. No server-side crashes.

The 1 genuine UX bug found on 2026-11-04 (login errors invisible) was **fixed on 2026-11-10**
(messages loop added to `templates/accounts/login.html` + regression unit test in `accounts/tests.py`),
so the planted "BUG CHECK" now passes. The 2 minor nits from the first run remain open (see matching §3).

### 1. Signup & onboarding — PASS
All 5 accounts: signup form -> email OTP (a deliberately wrong code was rejected with attempt countdown; the correct code from the email was accepted) -> profile setup -> AI-consent intro -> all 24 questions answered -> 100% complete. Duplicate email and mismatched passwords both rejected with clear errors.

### 2. Login — PASS (bug from 2026-11-04 now fixed)
Logout -> login as each account -> lands on /home/. A failed login creates no session (confirmed by redirect back to login).
- FIXED 2026-11-10: `templates/accounts/login.html` now renders the Django messages framework (a red flash banner above the form). A wrong password shows "Invalid email or password." on the page; a successful login redirects home with no error. Locked in by `LoginErrorVisibilityTests` in `accounts/tests.py` (2 regression tests). The planted E2E "BUG CHECK" now passes.

### 3. Matching (percentage -> request -> accept -> visibility) — PASS
- Match list returns percentage-sorted candidates: Divya (identical answers + same university + shared interests) = 100%, demo users 50/35%, other fresh users 33/25/10% - the 0.70 questionnaire + 0.30 profile weighting in settings.MATCHING computes exactly as designed.
- Unconnected profiles display as "??? ???" in the **match list API** (names masked; verified via the match-list entry). On the **profile detail page** the same privacy is enforced differently: the page renders a "Compatibility Profile" private preview with name/photo/age/city/gender/languages/bio/university/major/year/interests all blanked server-side, and only the questionnaire-based category similarity scores are shown. No personal data leaks either way (verified no interests/city/university text in the rendered HTML).
- Request -> recipient gets "New connection request" notification -> recipient accepts via the notification endpoint -> connection ACCEPTED on both sides -> name, university, major and interests unlock on the match list AND the full profile page.
- Minor API inconsistency: /api/matches/<id>/compatibility/ returns reasons/shared_interests as null when there are none (the match-list endpoint always returns arrays). Frontend should null-coalesce.

### 4. Chat — PASS
Text messages both directions (multipart, same as the UI's FormData), messages appear in both participants' poll endpoint, unread counts correct. PNG image message accepted (with image_url); a .txt uploaded as an image rejected with a clear 400; empty message rejected 400. Chat home lists the accepted contact with the latest message; unconnected users get 403 on the send API and 404 on the conversation page.

### 5. Communities / Events / Notifications — PASS
Communities list (5 seeded) and join/leave via POST. Events list and registration: valid registration creates a success notification; an invalid 2-digit phone is rejected with the "Please enter a valid name, email, and phone number." toast on /home/ (verified via DB: no registration row was created). Notifications inbox renders with the connection + event notifications.

### 6. Questionnaire summary & AI insights — PASS
Summary API + page work after completion. The compatibility-insights endpoint is for **unconnected public profiles** (a connected pair correctly returns 404 — their AI reflections live on the profile page instead). Graceful degradation verified: no `GROQ_API_KEY` -> 503 "not configured yet"; key set but the Groq call unreachable (e.g. proxy-blocked) -> 502 friendly "try again later" message; a working key would return 200 with generated summaries. No 500 crash in any path.

## How to re-run
See README.md in this folder.
