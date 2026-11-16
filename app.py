"""
Brom el ARD -- a Flask web app built from the team project starter.

Content comes from the API client (see api_client.py). The proposal's stored
data is defined in models.py. Authentication uses Flask sessions.

Run locally:   flask run --debug    ->   http://127.0.0.1:5000
"""
import os
from functools import wraps

import click

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort, g)
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Favorite
import api_client
from database import enable_sqlite_foreign_keys, initialize_database
from request_security import check_login_limit, configure_request_security, log_event
from validators import validate_signup, validate_login

LOCAL_SECRET = "dev-only-change-me"
DEFAULT_DATABASE_URI = "sqlite:///brom-el-ard.sqlite3"
MAX_DATABASE_ID = 2**31 - 1

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", LOCAL_SECRET)
app.config["ON_RENDER"] = os.environ.get("RENDER") == "true"


def database_uri():
    """PostgreSQL on Render (DATABASE_URL), else a separate local SQLite file."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    return DEFAULT_DATABASE_URI


def check_render_config():
    if app.secret_key.strip() in {"", LOCAL_SECRET}:
        raise RuntimeError("Set a private SECRET_KEY in Render's environment.")
    invalid_url = "Set a valid PostgreSQL DATABASE_URL in Render's environment."
    try:
        parsed = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    except (ArgumentError, ValueError):
        raise RuntimeError(invalid_url) from None
    if parsed.drivername != "postgresql+psycopg2" or not parsed.host or not parsed.database:
        raise RuntimeError(invalid_url)


app.config["SQLALCHEMY_DATABASE_URI"] = database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
if app.config["ON_RENDER"]:
    check_render_config()
    app.config["DEBUG"] = False
db.init_app(app)
with app.app_context():
    if db.engine.url.get_backend_name() == "sqlite":
        event.listen(db.engine, "connect", enable_sqlite_foreign_keys)

configure_request_security(app)


@app.cli.command("init-db")
def init_db_command():
    """Create the proposal's tables in the configured database."""
    try:
        initialize_database()
    except ValueError as error:
        raise click.ClickException(str(error)) from None
    click.echo("Proposal database initialized.")


def current_user():
    if "current_user" not in g:
        user_id = session.get("user_id")
        user = None
        if type(user_id) is int and 1 <= user_id <= MAX_DATABASE_ID:
            user = db.session.get(User, user_id)
        g.current_user = user if user is not None and user.is_active else None
        if "user_id" in session and g.current_user is None:
            session.clear()
    return g.current_user


@app.context_processor
def inject_globals():
    """Make the active account available in templates."""
    return {"current_user": current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            log_event("access", "login_required", status=302)
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user().role != "admin":
            log_event("access", "admin_required", status=403)
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def owned_or_404(model, record_id):
    """Find a row owned by the active user. For a stop, scope its parent itinerary first."""
    user = current_user()
    if user is not None and 1 <= record_id <= MAX_DATABASE_ID:
        row = db.session.scalar(db.select(model).filter_by(id=record_id, user_id=user.id))
        if row is not None:
            return row
    log_event("access", "owned_record_unavailable", status=404)
    abort(404)


# ---------- content (from your API) --------------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if len(query) > 120:
        abort(400)
    items = api_client.search(query) if query else []
    return render_template("results.html", items=items, query=query)


@app.route("/item/<item_id>")
def item(item_id):
    data = api_client.get_item(item_id)
    if not data:
        abort(404)
    return render_template("detail.html", item=data)


# ===================================================================
# AUTHENTICATION  --  YOU BUILD THIS (sign-up, log-in, log-out, sessions)
# ===================================================================
# This is YOUR work. The routes below are stubs. Implement them using what
# you learned in the "Sessions & Login" slides. Tools already imported for
# you at the top: generate_password_hash, check_password_hash, session,
# and the validators validate_signup / validate_login.
#
# What each route should do:
#   signup (POST): validate the form; reject an email that already exists;
#                  hash the password; create the User; store session["user_id"];
#                  redirect home.
#   login  (POST): validate; find the user by email; check_password_hash;
#                  on success store session["user_id"]; else show an error.
#   logout        : session.clear(); redirect home.
# A worked version of favorites below shows how session["user_id"] is used.

@app.route("/signup", methods=["GET", "POST"])
def signup():
    errors = {}
    data = {}
    if request.method == "POST":
        errors, email = validate_signup(request.form)
        data = {"email": email} if "email" not in errors else {}
        # TODO: create an account from valid form data (SCRUM-7).
    return render_template("signup.html", errors=errors, data=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    errors = {}
    data = {}
    if request.method == "POST":
        check_login_limit()
        errors, email = validate_login(request.form)
        data = {"email": email} if "email" not in errors else {}
        log_event("login", "invalid_form" if errors else "received")
        # TODO: authenticate valid form data and start a fresh session (SCRUM-7).
    return render_template("login.html", errors=errors, data=data)


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- favorites (login required) -----------------------------
@app.route("/favorites")
@login_required
def favorites():
    items = current_user().favorites
    return render_template("favorites.html", favorites=items)


@app.route("/favorites/add", methods=["POST"])
@login_required
def favorites_add():
    flash("Saving places will be available when place providers are connected.")
    return redirect(url_for("favorites"))


@app.route("/favorites/remove", methods=["POST"])
@login_required
def favorites_remove():
    favorite_id = request.form.get("favorite_id", type=int)
    if favorite_id is None or not 1 <= favorite_id <= MAX_DATABASE_ID:
        abort(400)
    db.session.delete(owned_or_404(Favorite, favorite_id))
    db.session.commit()
    flash("Removed from favorites.")
    return redirect(url_for("favorites"))


if __name__ == "__main__":
    app.run(debug=not app.config["ON_RENDER"], load_dotenv=False)
