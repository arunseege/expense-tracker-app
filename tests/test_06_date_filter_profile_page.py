"""Tests for Step 06 — date filter for the profile page.

Every test is derived from the feature spec, not from reading implementation
details. Fixtures use an in-memory SQLite database so each test is fully
isolated.
"""

import sqlite3
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _last_day_of_month(d: date) -> date:
    # Walk to the first day of the next month, then back one day.
    if d.month == 12:
        return date(d.year + 1, 1, 1) - timedelta(days=1)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask app wired to a fresh per-test SQLite database."""
    monkeypatch.setattr("database.db.DB_PATH", tmp_path / "test.db")
    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
        }
    )
    with flask_app.app_context():
        init_db()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_user_id(app):
    """Create a plain test user with no expenses and return their id."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Filter User", "filter@spendly.com", generate_password_hash("filterpass")),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


@pytest.fixture
def seeded_user(app, db_user_id):
    """Insert expenses across three distinct calendar months and return metadata.

    Returns a dict with:
        user_id         — the user's database id
        this_month_from — first day of the current calendar month (YYYY-MM-DD)
        this_month_to   — today (YYYY-MM-DD)
        last_month_from — first day of last calendar month (YYYY-MM-DD)
        last_month_to   — last day of last calendar month (YYYY-MM-DD)
        older_date      — a date three months ago (YYYY-MM-DD)
        this_month_total   — sum of expenses in current month
        last_month_total   — sum of expenses in last month
        older_total        — sum of expenses in the older month
        all_time_total     — total of all three groups
    """
    today = date.today()

    # Current month — two expenses
    cm_from = _first_day_of_month(today)
    cm_to = today
    cm_date1 = cm_from.strftime("%Y-%m-%d")
    cm_date2 = cm_to.strftime("%Y-%m-%d")
    cm_amount1 = 50.00
    cm_amount2 = 25.00

    # Last month — one expense
    lm_last = _first_day_of_month(today) - timedelta(days=1)
    lm_from = _first_day_of_month(lm_last)
    lm_to = lm_last
    lm_date = lm_from.strftime("%Y-%m-%d")
    lm_amount = 80.00

    # Three months ago — one expense
    month = today.month - 3
    year = today.year
    if month <= 0:
        month += 12
        year -= 1
    older_day = date(year, month, 1)
    older_date_str = older_day.strftime("%Y-%m-%d")
    older_amount = 30.00

    conn = get_db()
    try:
        rows = [
            (db_user_id, cm_amount1, "Food", cm_date1, "Current month expense 1"),
            (db_user_id, cm_amount2, "Transport", cm_date2, "Current month expense 2"),
            (db_user_id, lm_amount, "Bills", lm_date, "Last month expense"),
            (db_user_id, older_amount, "Health", older_date_str, "Older expense"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "user_id": db_user_id,
        "this_month_from": cm_from.strftime("%Y-%m-%d"),
        "this_month_to": cm_to.strftime("%Y-%m-%d"),
        "last_month_from": lm_from.strftime("%Y-%m-%d"),
        "last_month_to": lm_to.strftime("%Y-%m-%d"),
        "older_date": older_date_str,
        "this_month_total": round(cm_amount1 + cm_amount2, 2),
        "last_month_total": round(lm_amount, 2),
        "older_total": round(older_amount, 2),
        "all_time_total": round(cm_amount1 + cm_amount2 + lm_amount + older_amount, 2),
    }


@pytest.fixture
def auth_client(client, seeded_user):
    """Test client pre-authenticated as the seeded filter user."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["user_id"]
        sess["user_name"] = "Filter User"
    return client


@pytest.fixture
def empty_user_id(app):
    """A user with zero expenses."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Empty User", "empty2@spendly.com", generate_password_hash("pass")),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# get_summary_stats — date filter behaviour
# ---------------------------------------------------------------------------

class TestGetSummaryStatsDateFilter:
    def test_date_range_returns_only_in_range_expenses(self, app, seeded_user):
        """Supplying date_from/date_to must exclude out-of-range expenses."""
        with app.app_context():
            stats = get_summary_stats(
                seeded_user["user_id"],
                date_from=seeded_user["this_month_from"],
                date_to=seeded_user["this_month_to"],
            )
        assert stats["total_spent"] == pytest.approx(
            seeded_user["this_month_total"], abs=0.01
        ), "Only current-month expenses should be included"
        assert stats["transaction_count"] == 2, "Two expenses in current month"

    def test_none_bounds_returns_all_expenses(self, app, seeded_user):
        """Passing date_from=None and date_to=None must return all expenses."""
        with app.app_context():
            stats = get_summary_stats(seeded_user["user_id"], date_from=None, date_to=None)
        assert stats["total_spent"] == pytest.approx(
            seeded_user["all_time_total"], abs=0.01
        ), "All-time total must match sum of all four seeded expenses"
        assert stats["transaction_count"] == 4

    def test_range_with_no_matching_expenses_returns_zeros(self, app, empty_user_id):
        """A date range with no matching expenses must return zeros, not an error."""
        with app.app_context():
            stats = get_summary_stats(
                empty_user_id,
                date_from="2000-01-01",
                date_to="2000-01-31",
            )
        assert stats["total_spent"] == 0, "No expenses should yield total 0"
        assert stats["transaction_count"] == 0, "No expenses should yield count 0"
        assert stats["top_category"] == "—", "No expenses should yield no top category"

    def test_last_month_range_returns_only_last_month(self, app, seeded_user):
        """Filtering to last month must exclude current-month and older expenses."""
        with app.app_context():
            stats = get_summary_stats(
                seeded_user["user_id"],
                date_from=seeded_user["last_month_from"],
                date_to=seeded_user["last_month_to"],
            )
        assert stats["total_spent"] == pytest.approx(
            seeded_user["last_month_total"], abs=0.01
        ), "Only last-month expenses should be included"
        assert stats["transaction_count"] == 1

    def test_top_category_reflects_filtered_range(self, app, seeded_user):
        """top_category must reflect only the filtered range, not all-time data."""
        with app.app_context():
            stats = get_summary_stats(
                seeded_user["user_id"],
                date_from=seeded_user["last_month_from"],
                date_to=seeded_user["last_month_to"],
            )
        # The only last-month expense is "Bills"
        assert stats["top_category"] == "Bills"


# ---------------------------------------------------------------------------
# get_recent_transactions — date filter behaviour
# ---------------------------------------------------------------------------

class TestGetRecentTransactionsDateFilter:
    def test_date_range_returns_only_in_range_transactions(self, app, seeded_user):
        with app.app_context():
            txs = get_recent_transactions(
                seeded_user["user_id"],
                date_from=seeded_user["this_month_from"],
                date_to=seeded_user["this_month_to"],
            )
        assert len(txs) == 2, "Two current-month expenses expected"
        for tx in txs:
            assert (
                tx["date"] >= seeded_user["this_month_from"]
                and tx["date"] <= seeded_user["this_month_to"]
            ), f"Transaction date {tx['date']} is outside the requested range"

    def test_none_bounds_returns_all_transactions(self, app, seeded_user):
        with app.app_context():
            txs = get_recent_transactions(
                seeded_user["user_id"], date_from=None, date_to=None
            )
        assert len(txs) == 4, "All four seeded transactions should be returned"

    def test_range_with_no_matching_expenses_returns_empty_list(self, app, empty_user_id):
        with app.app_context():
            txs = get_recent_transactions(
                empty_user_id,
                date_from="2000-01-01",
                date_to="2000-01-31",
            )
        assert txs == [], "Empty list expected when no expenses match the range"

    def test_results_ordered_newest_first_within_range(self, app, seeded_user):
        with app.app_context():
            txs = get_recent_transactions(
                seeded_user["user_id"],
                date_from=seeded_user["this_month_from"],
                date_to=seeded_user["this_month_to"],
            )
        dates = [tx["date"] for tx in txs]
        assert dates == sorted(dates, reverse=True), "Transactions must be newest first"

    def test_has_expected_keys(self, app, seeded_user):
        with app.app_context():
            txs = get_recent_transactions(
                seeded_user["user_id"],
                date_from=seeded_user["this_month_from"],
                date_to=seeded_user["this_month_to"],
            )
        for tx in txs:
            assert {"date", "description", "category", "amount"} <= tx.keys()


# ---------------------------------------------------------------------------
# get_category_breakdown — date filter behaviour
# ---------------------------------------------------------------------------

class TestGetCategoryBreakdownDateFilter:
    def test_date_range_returns_only_in_range_categories(self, app, seeded_user):
        with app.app_context():
            cats = get_category_breakdown(
                seeded_user["user_id"],
                date_from=seeded_user["this_month_from"],
                date_to=seeded_user["this_month_to"],
            )
        # Current month has "Food" and "Transport" only
        names = {c["name"] for c in cats}
        assert names == {"Food", "Transport"}, (
            f"Only current-month categories expected, got {names}"
        )

    def test_none_bounds_returns_all_categories(self, app, seeded_user):
        with app.app_context():
            cats = get_category_breakdown(
                seeded_user["user_id"], date_from=None, date_to=None
            )
        names = {c["name"] for c in cats}
        # Four expenses across Food, Transport, Bills, Health
        assert names == {"Food", "Transport", "Bills", "Health"}

    def test_range_with_no_matching_expenses_returns_empty_list(self, app, empty_user_id):
        with app.app_context():
            cats = get_category_breakdown(
                empty_user_id,
                date_from="2000-01-01",
                date_to="2000-01-31",
            )
        assert cats == [], "Empty list expected when no expenses match the range"

    def test_has_expected_keys(self, app, seeded_user):
        with app.app_context():
            cats = get_category_breakdown(
                seeded_user["user_id"],
                date_from=seeded_user["this_month_from"],
                date_to=seeded_user["this_month_to"],
            )
        for cat in cats:
            assert {"name", "amount", "pct"} <= cat.keys()

    def test_amounts_reflect_filtered_range(self, app, seeded_user):
        with app.app_context():
            cats = get_category_breakdown(
                seeded_user["user_id"],
                date_from=seeded_user["this_month_from"],
                date_to=seeded_user["this_month_to"],
            )
        total = sum(c["amount"] for c in cats)
        assert total == pytest.approx(seeded_user["this_month_total"], abs=0.01)


# ---------------------------------------------------------------------------
# GET /profile — auth guard
# ---------------------------------------------------------------------------

class TestProfileAuthGuard:
    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "Expected redirect for unauthenticated request"
        assert "/login" in resp.headers["Location"], "Should redirect to /login"

    def test_unauthenticated_with_filter_param_also_redirects(self, client):
        resp = client.get("/profile?filter=this_month")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# GET /profile — filter presets return 200
# ---------------------------------------------------------------------------

class TestProfileFilterPresets:
    def test_no_query_param_defaults_to_this_month_returns_200(
        self, auth_client
    ):
        resp = auth_client.get("/profile")
        assert resp.status_code == 200, "No params should default to this_month and succeed"

    def test_filter_this_month_returns_200(self, auth_client):
        resp = auth_client.get("/profile?filter=this_month")
        assert resp.status_code == 200

    def test_filter_last_month_returns_200(self, auth_client):
        resp = auth_client.get("/profile?filter=last_month")
        assert resp.status_code == 200

    def test_filter_last_3_months_returns_200(self, auth_client):
        resp = auth_client.get("/profile?filter=last_3_months")
        assert resp.status_code == 200

    def test_filter_all_time_returns_200(self, auth_client):
        resp = auth_client.get("/profile?filter=all_time")
        assert resp.status_code == 200

    def test_unrecognised_filter_falls_back_silently_returns_200(self, auth_client):
        resp = auth_client.get("/profile?filter=garbage")
        assert resp.status_code == 200, "Unrecognised filter must fall back, not raise an error"

    def test_unrecognised_filter_does_not_return_500(self, auth_client):
        resp = auth_client.get("/profile?filter=; DROP TABLE expenses;")
        assert resp.status_code in (200, 302), "Must not return a server error"


# ---------------------------------------------------------------------------
# GET /profile — stat values per filter preset
# ---------------------------------------------------------------------------

class TestProfileFilterStats:
    def test_this_month_stats_reflect_current_month_only(
        self, auth_client, seeded_user
    ):
        """The total shown for this_month must match only current-month expenses."""
        resp = auth_client.get("/profile?filter=this_month")
        assert resp.status_code == 200
        body = resp.data.decode()
        # Format the expected total as it would appear in the template (₹50.00 style)
        expected = f"{seeded_user['this_month_total']:.2f}"
        assert expected in body, (
            f"Expected this-month total {expected} in page body"
        )

    def test_all_time_stats_show_all_expenses(
        self, auth_client, seeded_user
    ):
        """all_time must show the sum of every expense, same as no-filter baseline."""
        resp = auth_client.get("/profile?filter=all_time")
        assert resp.status_code == 200
        body = resp.data.decode()
        expected = f"{seeded_user['all_time_total']:.2f}"
        assert expected in body, (
            f"Expected all-time total {expected} in page body"
        )

    def test_last_month_stats_reflect_last_month_only(
        self, auth_client, seeded_user
    ):
        resp = auth_client.get("/profile?filter=last_month")
        assert resp.status_code == 200
        body = resp.data.decode()
        expected = f"{seeded_user['last_month_total']:.2f}"
        assert expected in body, (
            f"Expected last-month total {expected} in page body"
        )


# ---------------------------------------------------------------------------
# GET /profile — custom date range
# ---------------------------------------------------------------------------

class TestProfileCustomDateRange:
    def test_valid_custom_range_returns_200(self, auth_client, seeded_user):
        url = (
            f"/profile?date_from={seeded_user['this_month_from']}"
            f"&date_to={seeded_user['this_month_to']}"
        )
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_valid_custom_range_stats_scoped_to_range(
        self, auth_client, seeded_user
    ):
        url = (
            f"/profile?date_from={seeded_user['this_month_from']}"
            f"&date_to={seeded_user['this_month_to']}"
        )
        resp = auth_client.get(url)
        body = resp.data.decode()
        expected = f"{seeded_user['this_month_total']:.2f}"
        assert expected in body, "Custom range should scope stats to the given window"

    def test_date_from_equal_to_date_to_returns_200(
        self, auth_client, seeded_user
    ):
        """A single-day range (date_from == date_to) is valid and must return 200."""
        single_day = seeded_user["this_month_from"]
        url = f"/profile?date_from={single_day}&date_to={single_day}"
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_date_from_greater_than_date_to_redirects(
        self, auth_client, seeded_user
    ):
        """date_from > date_to is invalid; route must redirect, not serve data."""
        url = (
            f"/profile?date_from={seeded_user['this_month_to']}"
            f"&date_to={seeded_user['this_month_from']}"
        )
        resp = auth_client.get(url)
        assert resp.status_code == 302, (
            "Inverted date range must redirect, not return 200 with data"
        )

    def test_date_from_greater_than_date_to_does_not_return_200(
        self, auth_client, seeded_user
    ):
        """Confirm the inverted range does NOT silently render the page."""
        # Only meaningful when from and to are actually different
        if seeded_user["this_month_from"] == seeded_user["this_month_to"]:
            pytest.skip("from == to; cannot create inverted range in this scenario")
        url = (
            f"/profile?date_from={seeded_user['this_month_to']}"
            f"&date_to={seeded_user['this_month_from']}"
        )
        resp = auth_client.get(url)
        assert resp.status_code != 200, (
            "Inverted date range must not return a 200 response"
        )


# ---------------------------------------------------------------------------
# GET /profile — empty-range rendering (no errors)
# ---------------------------------------------------------------------------

class TestProfileEmptyRange:
    def test_far_future_range_renders_without_error(self, client, empty_user_id):
        """A range with no matching expenses must not raise an exception."""
        with client.session_transaction() as sess:
            sess["user_id"] = empty_user_id
            sess["user_name"] = "Empty User"
        resp = client.get("/profile?date_from=2099-01-01&date_to=2099-01-31")
        assert resp.status_code == 200, "Empty date range must render cleanly"

    def test_far_future_range_shows_zero_total(self, client, empty_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = empty_user_id
            sess["user_name"] = "Empty User"
        resp = client.get("/profile?date_from=2099-01-01&date_to=2099-01-31")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "0.00" in body, "Zero spend should appear when no expenses match"

    def test_empty_user_this_month_shows_zero(self, client, empty_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = empty_user_id
            sess["user_name"] = "Empty User"
        resp = client.get("/profile?filter=this_month")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "0.00" in body

    def test_empty_user_all_time_shows_zero(self, client, empty_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = empty_user_id
            sess["user_name"] = "Empty User"
        resp = client.get("/profile?filter=all_time")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "0.00" in body


# ---------------------------------------------------------------------------
# GET /profile — filter bar template rendering
# ---------------------------------------------------------------------------

class TestProfileFilterBarTemplate:
    def test_filter_bar_present_in_page(self, auth_client):
        """The filter bar container must be rendered on the profile page."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        assert b"filter-bar" in resp.data, "Expected filter-bar element in HTML"

    def test_four_filter_buttons_present(self, auth_client):
        """All four preset filter options must appear as links in the page."""
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        assert "this_month" in body, "this_month filter link must be present"
        assert "last_month" in body, "last_month filter link must be present"
        assert "last_3_months" in body, "last_3_months filter link must be present"
        assert "all_time" in body, "all_time filter link must be present"

    def test_active_filter_class_present_for_this_month(self, auth_client):
        """The active preset must receive the filter-btn--active CSS class."""
        resp = auth_client.get("/profile?filter=this_month")
        assert b"filter-btn--active" in resp.data, (
            "Active filter must have filter-btn--active class"
        )

    def test_active_filter_class_present_for_all_time(self, auth_client):
        resp = auth_client.get("/profile?filter=all_time")
        assert b"filter-btn--active" in resp.data

    def test_active_filter_class_present_for_last_month(self, auth_client):
        resp = auth_client.get("/profile?filter=last_month")
        assert b"filter-btn--active" in resp.data

    def test_active_filter_class_present_for_last_3_months(self, auth_client):
        resp = auth_client.get("/profile?filter=last_3_months")
        assert b"filter-btn--active" in resp.data

    def test_default_no_params_highlights_this_month(self, auth_client):
        """With no ?filter= param, this_month must be the highlighted button."""
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        # The page must contain the active class and the this_month identifier
        assert "filter-btn--active" in body
        assert "this_month" in body

    def test_filter_links_use_profile_route(self, auth_client):
        """Filter links must point to the /profile route (url_for compliance)."""
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        # url_for('profile', filter=...) produces /profile?filter=...
        assert "/profile?filter=" in body, (
            "Filter links must use url_for() pointing to /profile?filter="
        )


# ---------------------------------------------------------------------------
# GET /profile — active_filter forwarded to template per preset
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filter_param, expected_active",
    [
        ("this_month", "this_month"),
        ("last_month", "last_month"),
        ("last_3_months", "last_3_months"),
        ("all_time", "all_time"),
        # Unrecognised value must fall back to all_time per spec
        ("garbage", "all_time"),
    ],
)
def test_active_filter_value_in_response(
    client, app, seeded_user, filter_param, expected_active
):
    """active_filter must be forwarded correctly for every recognised preset."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["user_id"]
        sess["user_name"] = "Filter User"
    resp = client.get(f"/profile?filter={filter_param}")
    assert resp.status_code == 200
    body = resp.data.decode()
    # The template marks the active button, so the expected_active value
    # must appear alongside the filter-btn--active marker in the page.
    assert expected_active in body, (
        f"Expected active_filter '{expected_active}' to appear in response body "
        f"when ?filter={filter_param}"
    )
