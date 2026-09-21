# Profile API

All endpoints below require a logged-in Django session. JSON requests use
`Content-Type: application/json`; photo requests use `multipart/form-data`.

## Current user

### `GET /api/profile/me/`

Returns the authenticated user's profile. The response includes `languages` as
an array and a `profile_photo` URL when a photo exists.

### `POST /api/profile/me/`

Creates or replaces the authenticated user's profile fields. Required fields
may be omitted only when the existing profile form allows them to be blank.

### `PATCH /api/profile/me/`

Partially updates only the supplied fields. Supported fields include
`display_name`, `age`, `city`, `gender`, `languages`, `bio`, `university`,
`major`, `year`, `interests`, and `is_public`.

### `PATCH /api/profile/me/photo/`

Uploads a JPG, JPEG, PNG, or WEBP image no larger than 5 MB in the `photo`
field. The uploaded image is stored under Django `MEDIA_ROOT`.

### `DELETE /api/profile/me/photo/`

Removes the authenticated user's profile photo.

### `GET /api/profile/me/strength/`

Returns `profile_strength`, `completed_fields`, `total_fields`, and
`missing_fields`, calculated from the stored profile values.

### `GET /api/profile/me/stats/`

Returns database-backed `communities_count`, `chats_count`, `events_count`, and
`answers_count`. Features without a model currently return accurate zeroes.

## Other students

### `GET /api/students/<user-id>/profile/`

Returns public profile fields only. Private profiles return `403` unless the
requesting user has an accepted connection with the student. Passwords,
private email addresses, tokens, and authentication data are never serialized.
