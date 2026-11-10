# Campus Connect — End-to-End Test Report

Date: 2026-11-04 · Runner: Django 5.2.6, fresh SQLite, console email backend (OTP read from server log — no real email sent).

## Scope
Real HTTP flows driven with per-user sessions that mirror the browser (forms + CSRF, JSON APIs, multipart chat). 10 users in play: 5 freshly signed up (Mani, Divya, Arjun, Sara, Vikram) + 5 seeded demo profiles, so matching had a rich candidate pool.

## Result: all major flows PASS. 1 genuine UX bug + 2 minor nits found. No server-side crashes.

### 1. Signup & onboarding — PASS
All 5 accounts: signup form -> email OTP (a deliberately wrong code was rejected with attempt countdown; the correct code from the email was accepted) -> profile setup -> AI-consent intro -> all 24 questions answered -> 100% complete. Duplicate email and mismatched passwords both rejected with clear errors.

### 2. Login — PASS (with 1 bug)
Logout -> login as each account -> lands on /home/. A failed login creates no session (confirmed by redirect back to login).
- BUG (minor UX): templates/accounts/login.html does not render the Django `messages` context. The view correctly adds messages.error('Invalid email or password.'), but the user sees no visible error - the form just re-renders silently. Add a small {% if messages %} block (the pattern already exists in verify_email.html and home.html).

### 3. Matching (percentage -> request -> accept -> visibility) — PASS
- Match list returns percentage-sorted candidates: Divya (identical answers + same university + shared interests) = 100%, demo users 50/35%, other fresh users 33/25/10% - the 0.70 questionnaire + 0.30 profile weighting in settings.MATCHING computes exactly as designed.
- Unconnected profiles display as "??? ???" with the card staying private (verified no name/interests/city/major leak in the rendered HTML).
- Request -> recipient gets "New connection request" notification -> recipient accepts via the notification endpoint -> connection ACCEPTED on both sides -> name, university, major and interests unlock on the match list AND the full profile page.
- Minor API inconsistency: /api/matches/<id>/compatibility/ returns reasons/shared_interests as null when there are none (the match-list endpoint always returns arrays). Frontend should null-coalesce.

### 4. Chat — PASS
Text messages both directions (multipart, same as the UI's FormData), messages appear in both participants' poll endpoint, unread counts correct. PNG image message accepted (with image_url); a .txt uploaded as an image rejected with a clear 400; empty message rejected 400. Chat home lists the accepted contact with the latest message; unconnected users get 403 on the send API and 404 on the conversation page.

### 5. Communities / Events / Notifications — PASS
Communities list (5 seeded) and join/leave via POST. Events list and registration: valid registration creates a success notification; an invalid 2-digit phone is rejected with the "Please enter a valid name, email, and phone number." toast on /home/ (verified via DB: no registration row was created). Notifications inbox renders with the connection + event notifications.

### 6. Questionnaire summary & AI insights — PASS
Summary API + page work after completion. Without GEMINI_API_KEY the insights endpoint degrades gracefully: 503 "Gemini is not configured yet." (with a key present it calls the Gemini API - not exercised here by design).

## How to re-run
See README.md in this folder.
