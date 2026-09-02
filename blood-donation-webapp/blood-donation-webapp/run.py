"""
Entry point for local development.

Usage:
    python run.py

Reads DATABASE_URL from the environment if set (see README.md for the
MySQL connection string format); otherwise defaults to a local SQLite
database at instance/blood_donation.db.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
