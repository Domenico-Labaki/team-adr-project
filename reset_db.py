"""Reset the disposable local SQLite database.

This standalone script reads DATABASE_URL from the process environment. Run
the reset from the project directory on macOS or Linux with SQLite selected.

    DATABASE_URL=sqlite:///brom-el-ard.sqlite3 python reset_db.py

This drops and recreates the tables defined in models.py, deleting their data.

For a fresh Render PostgreSQL database, run `python -m flask --app app init-db`
with the schema owner's external connection URL set as DATABASE_URL in your
local .env. The Flask CLI loads .env through python-dotenv. The init-db command
creates missing tables and preserves existing rows.
"""
from app import app
from models import db

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database reset: all tables created from models.py.")
