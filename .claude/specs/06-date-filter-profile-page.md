# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page so users can scope all
displayed data — summary stats, recent transactions, and category breakdown —
to a chosen time window. Currently every section shows all-time data regardless
of when expenses were recorded. A filter bar with four preset options ("This
Month", "Last Month", "Last 3 Months", "All Time") is rendered above the stats
row. Selecting a preset reloads the page with a `?filter=` query parameter; the
route reads that parameter, derives `date_from` / `date_to` bounds, and passes
them through to the three query helpers. The active preset is visually
highlighted. No custom date pickers are introduced at this step.

## Depends on
- Step 1: Database setup (`get_db()`, `expenses` table with `date` column)
- Step 2: Registration (users exist)
- Step 3: Login / Logout (`session["user_id"]` is set)
- Step 4: Profile page static UI (template structure is stable)
- Step 5: Backend connection (live data already flows into all three sections)

## Routes
No new routes. The existing `GET /profile` route is extended to accept an
optional `?filter=` query parameter with values: `this_month`, `last_month`,
`last_3_months`, `all_time` (default: `this_month`).

## Database changes
No database changes. The `expenses.date` column (`TEXT`, format `YYYY-MM-DD`)
already exists and is sufficient for range filtering with `BETWEEN ? AND ?`.

## Templates
- **Modify**: `templates/profile.html`
  - Add a filter bar (`<div class="filter-bar">`) between the user-card and the
    stats row.
  - Four `<a>` links, each pointing to `url_for('profile', filter=<preset>)`.
  - The active preset receives the `filter-btn--active` CSS class (compare
    against the `active_filter` template variable).

## Files to change
- `database/queries.py`
  - `get_summary_stats(user_id, date_from=None, date_to=None)` — add optional
    date bounds; when both are supplied append `AND date BETWEEN ? AND ?` to
    every query.
  - `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`
    — same pattern.
  - `get_category_breakdown(user_id, date_from=None, date_to=None)` — same
    pattern.
- `app.py`
  - `profile()` route: read `request.args.get("filter", "this_month")`, compute
    `date_from` / `date_to` using Python's `datetime` module, pass them to all
    three query helpers, and forward `active_filter` to the template.
- `templates/profile.html` — add filter bar (see Templates section).
- `static/css/profile.css` — add styles for `.filter-bar`, `.filter-btn`, and
  `.filter-btn--active`.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never f-strings in SQL
- FK enforcement is already handled by `get_db()`; do not duplicate the PRAGMA
- Use CSS variables — never hardcode hex values in the stylesheet
- All templates extend `base.html`
- Date arithmetic must use Python's standard `datetime` module — no `dateutil`
- `date_from` and `date_to` must be `YYYY-MM-DD` strings when passed to queries
- "This Month" = first day of the current calendar month → today
- "Last Month" = first day of the previous calendar month → last day of that month
- "Last 3 Months" = first day of the month three months ago → today
- "All Time" = no date bounds (pass `None, None` to helpers)
- An unrecognised `filter` value must fall back silently to `this_month`
- The filter bar links must use `url_for()` — never hardcode `/profile?filter=…`

## Definition of done
- [ ] The profile page renders a filter bar with four labelled buttons above the
  stats row
- [ ] The button matching the current `?filter=` value is visually highlighted
- [ ] "This Month" is active by default when no `?filter=` param is present
- [ ] Selecting "All Time" shows the same totals that were visible before this
  step (all expenses, e.g. ₹343.89 for the seed user)
- [ ] Selecting "This Month" shows only expenses whose `date` falls in the
  current calendar month
- [ ] Selecting "Last Month" shows only expenses from the previous calendar month
- [ ] Selecting "Last 3 Months" shows expenses from the past three months
- [ ] Selecting a filter updates all three sections simultaneously: summary
  stats, transaction list, and category breakdown
- [ ] With no expenses in the selected range, summary stats show ₹0.00 / 0
  transactions / "—", the transaction table is empty, and the category breakdown
  is empty — no errors or exceptions
- [ ] All internal links use `url_for()` — no hardcoded URLs
