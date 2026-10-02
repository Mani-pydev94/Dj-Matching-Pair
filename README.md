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
