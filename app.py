from flask import Flask

from database.db import get_db, init_db, seed_db

app = Flask(__name__)

# Ensure the database schema and demo data are ready before any route runs.
with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True)
