import os
from datetime import date, datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_user_by_email, get_user_by_id, init_db, seed_db
from database.queries import get_category_breakdown, get_recent_transactions, get_summary_stats

app = Flask(__name__)

# Required for flash()/session signing. Dev fallback only — production must
# supply SECRET_KEY via the environment.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Ensure the database schema and demo data are ready before any route runs.
with app.app_context():
    init_db()
    seed_db()


@app.route("/")
def index():
    return render_template("landing.html", main_class="")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template("register.html", name=name, email=email)

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html", name=name, email=email)

        user_id = create_user(name, email, password)
        if user_id is None:
            flash("That email is already registered.", "error")
            return render_template("register.html", name=name, email=email)

        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("All fields are required.", "error")
            return render_template("login.html", email=email)

        user = get_user_by_email(email)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html", email=email)

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    row = get_user_by_id(session["user_id"])
    name = row["name"] if row else session.get("user_name", "")
    initials = "".join(part[0].upper() for part in name.split()[:2])
    created_at = row["created_at"] if row else ""
    try:
        member_since = datetime.strptime(created_at[:7], "%Y-%m").strftime("%B %Y")
    except (ValueError, TypeError):
        member_since = ""
    user = {
        "name": name,
        "email": row["email"] if row else "",
        "member_since": member_since,
        "initials": initials,
    }
    date_from = request.args.get("date_from") or None
    date_to = request.args.get("date_to") or None
    if date_from and date_to and date_from > date_to:
        flash("'From' date must be before 'To' date.", "error")
        return redirect(url_for("profile"))
    if date_from and date_to:
        active_filter = "custom"
    else:
        filter_val = request.args.get("filter", "this_month")
        today = date.today()
        if filter_val == "this_month":
            date_from = today.replace(day=1).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            active_filter = "this_month"
        elif filter_val == "last_month":
            last_day = today.replace(day=1) - timedelta(days=1)
            date_from = last_day.replace(day=1).strftime("%Y-%m-%d")
            date_to = last_day.strftime("%Y-%m-%d")
            active_filter = "last_month"
        elif filter_val == "last_3_months":
            month = today.month - 3
            year = today.year
            if month <= 0:
                month += 12
                year -= 1
            date_from = date(year, month, 1).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            active_filter = "last_3_months"
        else:
            filter_val = "all_time"
            date_from = None
            date_to = None
            active_filter = "all_time"
    stats = get_summary_stats(session["user_id"], date_from, date_to)
    transactions = get_recent_transactions(session["user_id"], date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(session["user_id"], date_from, date_to)
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        active_filter=active_filter,
        date_from=date_from or "",
        date_to=date_to or "",
        main_class="profile-layout",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
