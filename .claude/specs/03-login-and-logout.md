# Spec: Login and Logout

## Overview
Implement credential-based login and session-backed logout so registered users can authenticate into Spendly. This step upgrades the existing stub `GET /login` route into a full POST handler that verifies email and password against the database, writes the authenticated user into Flask's signed session, and redirects to the landing page. It also implements the `GET /logout` stub, which clears the session and redirects back to `/login`. Together these two routes establish the session lifecycle that all future authenticated features depend on.

## Depends on
- Step 01 — Database Setup (`get_db()`, `users` table, `password_hash` column)
- Step 02 — Registration (users exist in the database to log in with)

## Routes
- `POST /login` — verify credentials, write session, redirect to `/` on success — public
- `GET /logout` — clear session, redirect to `/login` — public (no auth guard needed at this step)

Note: `GET /login` already renders `login.html`; this step adds POST handling to the same route function.

## Database changes
No database changes. The existing `users` table already has `id`, `name`, `email`, and `password_hash`. No new tables or columns needed.

## Templates
- **Create:** none — `login.html` already exists
- **Modify:** `templates/login.html` — ensure the form posts to `url_for('login')` with `method="post"`, and that flash messages are displayed. Add fields: `email` (type email) and `password` (type password).

## Files to change
- `app.py` — upgrade `login` route to handle POST; add `logout` route; import `session` from flask and `get_user_by_email` from `database.db`
- `database/db.py` — add `get_user_by_email(email)` helper that returns the matching user row or `None`
- `templates/login.html` — add POST form and flash message display if not already present

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` is already available via the existing werkzeug install.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for all internal links — never hardcode URLs
- DB logic (`get_user_by_email`) must live in `database/db.py`, not inline in the route
- On successful login store `session['user_id']` (int) and `session['user_name']` (str) only
- On failed login show a generic flash error ("Invalid email or password.") — do not reveal which field was wrong
- Use `flash()` + re-render (not redirect) on validation errors so the form email value is preserved
- `logout` must call `session.clear()` before redirecting
- Import `session` from flask in `app.py`; do not use a separate session library

## Definition of done
- [ ] `GET /login` renders the login form without errors
- [ ] Submitting valid credentials writes `session['user_id']` and redirects to `/`
- [ ] Submitting a wrong password shows "Invalid email or password." and does not create a session
- [ ] Submitting an unregistered email shows "Invalid email or password." and does not create a session
- [ ] Submitting with a blank email or password shows a validation error and does not query the database
- [ ] `GET /logout` clears the session and redirects to `/login`
- [ ] After logout, revisiting `/logout` again still redirects cleanly to `/login`
- [ ] The login form uses `url_for('login')` as the action and `method="post"`
- [ ] The template extends `base.html` and displays flashed messages
