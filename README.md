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

The application currently uses traditional email/password authentication.

Create an administrator account with:

```bash
python manage.py createsuperuser
```

Google authentication is intentionally disabled for now. It can be added later
without changing the existing profile data.

## Environment Variables

Copy `.env.example` to `.env` and fill in values. Never commit `.env`.
