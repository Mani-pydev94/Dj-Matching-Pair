# Campus Connect AI — Project Overview

This document summarizes the current product structure, design language, and feature set so future work can build on a single source of truth.

## 1. Product summary

Campus Connect AI is a Django-based mobile-first student matching platform. The product is structured around a questionnaire-first matching flow: users create a profile, complete a compatibility questionnaire, discover likely matches, connect with others, and then message or coordinate through the app.

The project currently serves as a prototype / MVP for student networking, compatibility discovery, and campus community engagement.

## 2. Tech stack

- Backend: Django 4.2 LTS
- Database: SQLite by default; PostgreSQL-ready via environment variables
- Auth: custom user model + Django auth + django-allauth
- API: Django REST Framework (used in app-level endpoints)
- Storage: local media uploads for profile photos and chat images
- Frontend: Django template rendering with custom inline CSS; mobile-first responsive templates

Key configuration is in:
- `campus_connect/settings.py`
- `campus_connect/urls.py`

## 3. Project architecture

The project is split into feature-focused Django apps. Main apps currently include:

### Core app modules

- `accounts`
  - authentication and account management
  - custom `User` model
  - login/signup flow and social auth configuration hooks

- `profiles`
  - student profile data model
  - public/private visibility logic
  - profile photo and profile metadata
  - profile API endpoints

- `questionnaire`
  - question categories and question bank
  - user responses with importance ratings
  - compatibility scoring input source for matching

- `matching`
  - compatibility engine and recommendation logic
  - score generation for candidate users
  - match discovery UI and API routes

- `connections`
  - friend / contact request state
  - pending, accepted, rejected, blocked, or connected logic

- `chat`
  - one-to-one direct messaging between connected users
  - message models and conversation views

- `notifications`
  - user-facing notifications for events, requests, or inbox updates

- `communities`
  - community / group-like discovery and participation features

- `events`
  - event browsing and event-related discovery

- `admin_dashboard`
  - operational dashboard and admin tooling

- `core`
  - landing/home experience and shell layout

- `demo_seed`
  - seed data generation for demo environments

## 4. Key data models

### User and profile model

Primary account and profile logic lives in the custom user model and the `Profile` model.

`profiles.models.Profile` includes:
- UUID primary key
- linked `User`
- `university`, `major`, `year`, `age`, `city`, `gender`
- `languages`, `bio`, `interests`
- `photo`
- `is_public`
- `questionnaire_completed`
- timestamps

Important behavior:
- profile privacy is a first-class concept (`is_public`)
- private preview compatibility screens are intentionally used when users are not connected yet
- profiles are student-centric, with social matching logic built around them

### Questionnaire model

`questionnaire.models` defines:
- `QuestionnaireCategory`
- `Question`
- `QuestionOption`
- `QuestionResponse`

This supports:
- category-based questions (values, learning style, communication, career goals, lifestyle, interests)
- user importance voting (`MOST_IMPORTANT`, `NEUTRAL`, `NOT_VERY_IMPORTANT`)
- per-question selected answers and open-text answers

### Match model / connection state

`connections.models.Connection` handles relationship state between users:
- `NONE`
- `PENDING`
- `ACCEPTED`
- `DECLINED`
- `BLOCKED`
- `CONNECTED`

This is the backbone for whether a user can see another user’s profile details or not.

## 5. Matching logic

The compatibility system is questionnaire-driven. The main logic exists in `matching/compatibility.py` and is weighted by category / importance.

Core ideas:
- matching begins from questionnaire responses
- question similarity is weighted by average importance assigned by both users
- category scoring is computed and returned alongside the overall score
- profile traits such as shared interests, university, and city also influence match quality

Important file:
- `matching/compatibility.py`
- `matching/services.py`
- `campus_connect/settings.py` (`MATCHING` settings block)

The system currently includes configuration like:
- `MATCHING_QUESTIONNAIRE_WEIGHT`
- `MATCHING_MINIMUM_SCORE`
- `MATCHING_SAME_UNIVERSITY_DISCOVERY_SCORE`

This makes score thresholds adjustable without changing the matching source logic.

## 6. User journeys

### Registration and onboarding

1. User signs up / logs in.
2. User creates or updates profile details.
3. User completes the questionnaire.
4. App marks the profile as completed and unlocks matching.

### Discovery flow

1. Home screen surfaces recommended matches and quick actions.
2. User sees cards with match score, shared relationship indicators, and maybe profile previews.
3. Private / locked preview is shown until a connection is accepted or established.
4. Accepted profiles reveal deeper information and communication options.

### Connection flow

1. User sends connection request to another student.
2. Recipient can accept or reject.
3. Accepted users can move into direct messaging, further profile visibility, and campus networking.

### Communication flow

1. Connected users can open conversation screens.
2. Chat supports text and image messages.
3. Notifications can surface new interactions or request updates.

## 7. Design language and UI system

The current UI is intentionally mobile-first and polished for a social / networking app.

### Visual style

- Purple primary accent color: `#7547F5`
- White / off-white cards with faint borders and soft shadows
- Rounded corners and pill badges
- Large headline typography with bold, compact spacing
- Clear division between “overview” and “detail” information blocks

### Observed design traits from templates

From the main app templates, especially:
- `templates/pages/home.html`
- `templates/profiles/student_profile.html`
- `templates/matching/explore_matches.html`

The design language emphasizes:
- a compact 430px-style mobile shell
- stacked cards with strong hierarchy
- match score pills and progress bars
- CTA buttons with gradient purple styling
- trust/restriction cues for private profile previews

### Private-profile design behavior

The profile page distinguishes between:
- a connected user profile (full details visible)
- a private preview/compatibility preview (limited information shown until connection)

This is a major part of the product design: matching is visible, but personal data is intentionally hidden until a relationship exists.

## 8. Routes and URLs

Main route groups currently include:

- `''` → core app
- `auth/` → accounts auth/login flows
- `profiles/` → profile pages
- `api/` → profile API endpoints
- `api/questionnaire/` → questionnaire API
- `api/matches/` → match APIs
- `api/connections/` → connection APIs
- `questionnaire/` → questionnaire pages
- `matches/` → match pages
- `connections/` → connection pages
- `communities/` → communities pages
- `events/` → events pages
- `chat/` → chat pages
- `notifications/` → notifications pages

This indicates a hybrid MVP structure: both server-rendered page views and API endpoints for frontend interactions.

## 9. Current product surface area

The project currently covers these primary product areas:

- Student authentication
- Profile creation and profile editing
- Questionnaire-driven compatibility scoring
- Match discovery and comparison
- Connection requests / approval flow
- Profile privacy rules
- Chat messaging
- Notifications
- Community and event discovery
- Admin dashboard / moderation tooling

## 10. Business and product intent

The product is clearly designed around campus relationship-building and student networking, not generic social networking. The intentional features include:
- compatibility-based matching
- academic / lifestyle context
- student-only profile framing
- privacy-first discovery UX
- campus networking activities (communities, events)

## 11. Current implementation strengths

- clear modular Django app architecture
- strong compatibility-focused product direction
- mobile-first design language is consistent
- explicit separation of public/private profile states
- profile matching and privacy rules are product-defining rather than afterthoughts

## 12. Important extension points for future features

These are the natural places to expand without breaking the app model:

### Matching improvements
- more nuanced scoring weights
- better recommendation ranking
- AI-generated match reasons
- “mutual compatibility” explanation panels

### Profile improvements
- editable profile forms
- stronger profile verification
- additional social fields / preferences
- richer profile completeness scoring

### Connection improvements
- notifications for rejected / accepted requests
- “remove connection” or “block” flows
- connection suggestion engine

### Community and event improvements
- RSVP management
- host/admin workflows
- recommendation feed by school or interest

### Messaging improvements
- typing indicators
- read receipts
- message reactions
- attachments and media management

### Admin improvements
- moderation queue
- audit trail for reports
- student verification tools

## 13. Recommended product direction for new work

When building new features, keep these principles aligned with the current app:

1. Privacy-first discovery remains core.
2. Matching should remain questionnaire-led, not purely profile-led.
3. Mobile-first UX should stay compact and card-based.
4. App clarity matters more than feature count.
5. A connected state should unlock richer user data and communication features.

## 14. Summary

Campus Connect AI is a Django-based, mobile-first student matching product with a strong compatibility engine, relationship request flow, and privacy-sensitive profile experience. The architecture is already organized around clear product domains, and the current product direction is cohesive enough to support later features without redesigning the system from scratch.

This document is intended as the baseline for future engineering, UX, and product decisions.
