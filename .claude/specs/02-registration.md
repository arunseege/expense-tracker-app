# Spec: Registration

## Overview
Implement user registration so new visitors can create a Spendly account. This step upgrades the existing stub `GET /register` route into a fully functional form that accepts a POST, validates input, hashes the password, and inserts a new row into the `users` table. On success the user is shown with a success message and then redirected to the login page. This is the entry point for all authenticated features that follow.


## Depends on
- Step 01 — Database Setup (`get_db()`, `init_db()`, `users` table must exist)

## Routes
- `GET /register` — render the registration form — public
- `POST /register` — process form submission; redirect to `/login` on success — public

## Database changes
No new tables or columns. The existing `users` table (from Step 01) already has
`id`, `name`, `email`, `password_hash`, and `created_at`. No schema changes needed.

## Templates
- **Create:** `templates/register.html` — registration form extending `base.html`
- **Modify:** none

## Files to change
- `app.py` — replace the `GET /register` stub with a real route that handles both
  GET (render form) and POST (process submission)
- `database/db.py` — add `create_user(name, email, password)` helper

## Files to create
- `templates/register.html` — form with fields: name, email, password, confirm password

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`; never store plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for all internal links — never hardcode URLs
- DB logic (insert user) must live in `database/db.py`, not inline in the route
- Duplicate email must show a user-facing error (flash message), not raise an unhandled 500
- Validate server-side: all fields required, password and confirm-password must match
- On success redirect to `/login` using `redirect(url_for('login'))`
- Use `abort(400)` only for malformed requests; use flash + re-render for validation errors
- Use Flask's `flash()` and `get_flashed_messages()` for error and success messages

## Definition of done
- [ ] `GET /register` renders the registration form without errors
- [ ] Submitting the form with valid data inserts a new user into `users` with a hashed password
- [ ] After successful registration the user is redirected to `/login`
- [ ] Submitting with an already-registered email shows an error message and does not insert a duplicate row
- [ ] Submitting with mismatched passwords shows an error message
- [ ] Submitting with any blank field shows an error message
- [ ] The stored password is a werkzeug hash, not plaintext
- [ ] The form uses `url_for('register')` as the action attribute
- [ ] The template extends `base.html`
