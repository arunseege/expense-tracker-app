import os
from datetime import datetime

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
    stats = get_summary_stats(session["user_id"])
    transactions = get_recent_transactions(session["user_id"])
    categories = get_category_breakdown(session["user_id"])
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        main_class="profile-layout",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
