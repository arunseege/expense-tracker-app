"""Tests for Step 05 — backend connection for the profile page."""

import pytest

from app import app as flask_app
from database.db import get_db, init_db, seed_db
from database.queries import get_category_breakdown, get_recent_transactions, get_summary_stats


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.app_context():
        init_db()
        seed_db()
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id():
    """Return the id of the demo user inserted by seed_db()."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
        return row["id"]
    finally:
        conn.close()


@pytest.fixture
def empty_user_id():
    """Return a user id that has no expenses, creating the user if needed."""
    from werkzeug.security import generate_password_hash
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Empty User", "empty@spendly.com", generate_password_hash("pass")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("empty@spendly.com",)
        ).fetchone()
        # Ensure this user has no expenses (clean slate across runs).
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (row["id"],))
        conn.commit()
        return row["id"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# get_summary_stats
# ---------------------------------------------------------------------------

class TestGetSummaryStats:
    def test_returns_correct_totals_for_seed_user(self, app, seed_user_id):
        with app.app_context():
            stats = get_summary_stats(seed_user_id)
        assert stats["transaction_count"] == 8
        assert stats["total_spent"] == pytest.approx(343.89, abs=0.01)
        assert stats["top_category"] == "Shopping"

    def test_returns_zeros_for_user_with_no_expenses(self, app, empty_user_id):
        with app.app_context():
            stats = get_summary_stats(empty_user_id)
        assert stats["total_spent"] == 0
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"


# ---------------------------------------------------------------------------
# get_recent_transactions
# ---------------------------------------------------------------------------

class TestGetRecentTransactions:
    def test_returns_list_with_expected_keys(self, app, seed_user_id):
        with app.app_context():
            txs = get_recent_transactions(seed_user_id)
        assert len(txs) == 8
        for tx in txs:
            assert {"date", "description", "category", "amount"} <= tx.keys()

    def test_ordered_newest_first(self, app, seed_user_id):
        with app.app_context():
            txs = get_recent_transactions(seed_user_id)
        dates = [tx["date"] for tx in txs]
        assert dates == sorted(dates, reverse=True)

    def test_limit_is_respected(self, app, seed_user_id):
        with app.app_context():
            txs = get_recent_transactions(seed_user_id, limit=3)
        assert len(txs) == 3

    def test_returns_empty_list_for_user_with_no_expenses(self, app, empty_user_id):
        with app.app_context():
            txs = get_recent_transactions(empty_user_id)
        assert txs == []


# ---------------------------------------------------------------------------
# get_category_breakdown
# ---------------------------------------------------------------------------

class TestGetCategoryBreakdown:
    def test_returns_7_categories_for_seed_user(self, app, seed_user_id):
        with app.app_context():
            cats = get_category_breakdown(seed_user_id)
        assert len(cats) == 7

    def test_has_expected_keys(self, app, seed_user_id):
        with app.app_context():
            cats = get_category_breakdown(seed_user_id)
        for cat in cats:
            assert {"name", "amount", "pct"} <= cat.keys()

    def test_ordered_by_amount_desc(self, app, seed_user_id):
        with app.app_context():
            cats = get_category_breakdown(seed_user_id)
        amounts = [c["amount"] for c in cats]
        assert amounts == sorted(amounts, reverse=True)

    def test_pcts_sum_to_100(self, app, seed_user_id):
        with app.app_context():
            cats = get_category_breakdown(seed_user_id)
        assert sum(c["pct"] for c in cats) == 100

    def test_pcts_are_integers(self, app, seed_user_id):
        with app.app_context():
            cats = get_category_breakdown(seed_user_id)
        for cat in cats:
            assert isinstance(cat["pct"], int)

    def test_returns_empty_list_for_user_with_no_expenses(self, app, empty_user_id):
        with app.app_context():
            cats = get_category_breakdown(empty_user_id)
        assert cats == []


# ---------------------------------------------------------------------------
# /profile route
# ---------------------------------------------------------------------------

class TestProfileRoute:
    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_authenticated_returns_200(self, client, app):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"
        resp = client.get("/profile")
        assert resp.status_code == 200

    def test_shows_seed_user_name_and_email(self, client, seed_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = seed_user_id
            sess["user_name"] = "Demo User"
        resp = client.get("/profile")
        body = resp.data.decode()
        assert "Demo User" in body
        assert "demo@spendly.com" in body

    def test_rupee_symbol_present(self, client, seed_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = seed_user_id
            sess["user_name"] = "Demo User"
        resp = client.get("/profile")
        assert "₹" in resp.data.decode()

    def test_new_user_profile_renders_without_errors(self, client, empty_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = empty_user_id
            sess["user_name"] = "Empty User"
        resp = client.get("/profile")
        assert resp.status_code == 200
        assert "₹0.00" in resp.data.decode()
