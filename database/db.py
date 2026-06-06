"""SQLite data layer for Spendly.

Provides connection management plus schema creation and demo-data seeding.
No ORM; all writes use parameterized queries. Foreign key enforcement is
enabled on every connection.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

# Resolve the database path relative to the repo root (this file lives in
# database/), so the location is stable regardless of the working directory.
DB_PATH = Path(__file__).resolve().parent.parent / "spendly.db"

# Fixed category list shared across the app.
CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    """Open a connection to the Spendly database.

    Returns a connection with dictionary-like row access and foreign key
    enforcement enabled.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create both tables if they do not already exist. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert one demo user and 8 sample expenses, only if the DB is empty.

    Returns early when the users table already contains data so repeated calls
    do not duplicate records.
    """
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        # Build dates within the current month, formatted YYYY-MM-DD.
        now = datetime.now()

        def day(d):
            return f"{now.year:04d}-{now.month:02d}-{d:02d}"

        # 8 expenses covering all 7 categories (at least one each).
        expenses = [
            (user_id, 12.50, "Food", day(2), "Lunch at cafe"),
            (user_id, 30.00, "Transport", day(4), "Monthly metro top-up"),
            (user_id, 85.75, "Bills", day(6), "Electricity bill"),
            (user_id, 45.00, "Health", day(9), "Pharmacy"),
            (user_id, 18.99, "Entertainment", day(12), "Movie ticket"),
            (user_id, 120.40, "Shopping", day(15), "New shoes"),
            (user_id, 9.25, "Other", day(18), "Misc"),
            (user_id, 22.00, "Food", day(21), "Groceries"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        conn.commit()
    finally:
        conn.close()
