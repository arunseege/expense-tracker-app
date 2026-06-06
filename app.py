import os

from flask import Flask, flash, redirect, render_template, request, url_for

from database.db import create_user, init_db, seed_db

app = Flask(__name__)

# Required for flash()/session signing. Dev fallback only — production must
# supply SECRET_KEY via the environment.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Ensure the database schema and demo data are ready before any route runs.
with app.app_context():
    init_db()
    seed_db()


@app.route("/register", methods=["GET", "POST"])
def register():
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


@app.route("/login")
def login():
    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True)
