# Campus Connect AI

Django 4.2 LTS mobile AI student-matching application.

## Local Development

```bash
python manage.py migrate
python manage.py runserver
```

## Local Google Authentication Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create / select a project
3. Configure OAuth consent screen (External or Internal)
4. Create OAuth credentials (Web application)
5. Authorized JavaScript origins:
   - `http://localhost:8000`
   - `http://127.0.0.1:8000`
6. Authorized redirect URIs:
   - `http://localhost:8000/accounts/google/login/callback/`
   - `http://127.0.0.1:8000/accounts/google/login/callback/`
7. Copy Client ID and Client Secret
8. Add them to `.env`:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```
9. Run `python manage.py runserver`
10. Click "Continue with Google" on Login / Signup pages and complete OAuth.

## Environment Variables

Copy `.env.example` to `.env` and fill in values. Never commit `.env`.
