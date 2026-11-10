# Campus Connect — Reusable E2E Suite

Automated end-to-end checks that drive the real running app over HTTP with
per-user sessions (mimicking a browser), covering: signup → email OTP verify →
profile setup → questionnaire → matching → connection request/accept → chat,
plus communities, events, notifications, and AI-insight graceful degradation.

## How to run
1. Start the server with the **console** email backend so OTPs are captured:
   `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend python manage.py runserver 8010`
2. Seed questionnaire questions + demo data first:
   `python manage.py seed_questionnaire --replace` and `python manage.py seed_demo_data`
3. Point the suite at your server and run:
   `CC_BASE=http://127.0.0.1:8010 CC_SERVER_LOG=server.log python e2e_main.py`

The helpers create 5 fresh accounts, answer the 24 questions with different
patterns, compute real compatibility percentages, and verify the full
request → accept → chat loop. Results are printed and written to
`e2e_results.json`.

## Notes
- Uses the console email backend to read signup OTP codes from the server log.
- AI compatibility insights intentionally return 503 "Groq is not configured"
  when `GROQ_API_KEY` is absent; with a real key they call the Groq API.
