from database.db import get_db


def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        params = [user_id]
        date_clause = ""
        if date_from and date_to:
            date_clause = " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM expenses WHERE user_id = ?"
            + date_clause,
            params,
        ).fetchone()
        total_spent = round(row[0], 2)
        transaction_count = row[1]
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?"
            + date_clause
            + " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params,
        ).fetchone()
        top_category = top[0] if top else "—"
        return {
            "total_spent": total_spent,
            "transaction_count": transaction_count,
            "top_category": top_category,
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    conn = get_db()
    try:
        params = [user_id]
        date_clause = ""
        if date_from and date_to:
            date_clause = " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + date_clause + " ORDER BY date DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        params = [user_id]
        date_clause = ""
        if date_from and date_to:
            date_clause = " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + date_clause + " GROUP BY category ORDER BY total DESC",
            params,
        ).fetchall()
        if not rows:
            return []
        grand_total = sum(r["total"] for r in rows)
        result = [
            {
                "name": r["category"],
                "amount": round(r["total"], 2),
                "pct": round(r["total"] / grand_total * 100),
            }
            for r in rows
        ]
        diff = 100 - sum(c["pct"] for c in result)
        result[0]["pct"] += diff
        return result
    finally:
        conn.close()
