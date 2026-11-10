# Campus Connect AI

Django 4.2 LTS mobile AI student-matching application.

## Local Development

```bash
python manage.py migrate
python manage.py runserver
```

Local development uses SQLite by default. For production PostgreSQL, set
`DJANGO_DB_ENGINE=postgresql` plus `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` before running
migrations.

## Authentication

Email/password sign-up requires a one-time email code before the account is
activated. Codes contain six uppercase letters and digits, expire after ten
minutes, and allow up to five verification attempts. During local development,
the code is printed by Django's console email backend. Configure the `EMAIL_*`
environment variables in `.env` to deliver codes through your SMTP provider.

Create an administrator account with:

```bash
python manage.py createsuperuser
```

Google authentication is intentionally disabled for now. It can be added later
without changing the existing profile data.

## Environment Variables

Copy `.env.example` to `.env` and fill in values. Never commit `.env`.

Optional AI-written questionnaire and compatibility reflections use the Groq
API. Add `GROQ_API_KEY` to `.env` on the server (never in browser code);
optionally set `GROQ_MODEL` to a model enabled for your API key. The default is
`llama-3.3-70b-versatile`. Without a key, the personal
summary and answer snapshots still work. Users choose before starting whether
to enable automatic AI reflections after completing the questionnaire. Answers
are sent to Groq only for users who opt in. Existing opt-ins to the previous
provider do not carry over; users must choose again before their answers are
sent to Groq. Review Groq's current API terms and data-use policy before
enabling this for real users.
