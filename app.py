"""
Brom el ARD -- a Flask web app.

Content comes from an external API (see api_client.py). The only data stored
is user accounts and their favorites (see models.py). Authentication is
email + password with Flask sessions.

Flask CLI commands load .env through python-dotenv. See README.md for the
commands that select SQLite for local development.
"""
import json
import logging
import os
from datetime import timedelta
from functools import wraps
from ipaddress import ip_address
from uuid import uuid4

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event, make_url
from sqlalchemy.exc import ArgumentError, IntegrityError
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
import requests

import api_client
from models import Favorite, User, db
from validators import validate_login, validate_signup

app = Flask(__name__)
LOCAL_SECRET_KEY = "dev-only-fallback-secret-key"
app.secret_key = os.environ.get("SECRET_KEY", LOCAL_SECRET_KEY)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER") == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    SESSION_REFRESH_EACH_REQUEST=False,
)

# Only these public settings are passed to the destination page.
app.config.update(
    GEOAPIFY_API_KEY=os.environ.get("GEOAPIFY_API_KEY", ""),
    GEOAPIFY_TILE_URL=os.environ.get(
        "GEOAPIFY_TILE_URL", "https://maps.geoapify.com/v1/tile/osm-bright/{z}/{x}/{y}{r}.png"
    ),
    GEOCODING_API_URL=os.environ.get(
        "GEOCODING_API_URL", "https://geocoding-api.open-meteo.com/v1/search"
    ),
    FORECAST_API_URL=os.environ.get(
        "FORECAST_API_URL", "https://api.open-meteo.com/v1/forecast"
    ),
    WIKIMEDIA_API_URL=os.environ.get(
        "WIKIMEDIA_API_URL", "https://en.wikipedia.org/w/api.php"
    ),
)


# Reject oversized bodies when Flask reads a submitted form.
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024


# Assign an ID before CSRF and rate-limit checks so rejected requests can be traced.
@app.before_request
def assign_request_id():
    g.request_id = uuid4()


CSRFProtect(app)


# Count login attempts by Cloudflare's client IP on Render, falling back to the socket IP.
def login_client_key():
    if app.config["SESSION_COOKIE_SECURE"]:
        client_ip = request.headers.get("CF-Connecting-IP")
        if client_ip:
            try:
                return str(ip_address(client_ip))
            except ValueError:
                pass
    return get_remote_address()


# Keep rate-limit counters in one worker and tell blocked clients when to retry.
limiter = Limiter(login_client_key, app=app, storage_uri="memory://", headers_enabled=True)


# Give the advisor route a separate limit per signed-in user before it calls Gemini.
def advisor_rate_limit(user_id):
    return limiter.limit("5/minute", key_func=lambda: str(user_id), scope="advisor")


# Send request logs to stderr at INFO level and prevent duplicates in the parent logger.
request_logger = logging.getLogger("brom_el_ard.requests")
request_logger.addHandler(logging.StreamHandler())
request_logger.setLevel(logging.INFO)
request_logger.propagate = False


# Return the request ID to callers and log only the metadata needed to trace the response.
@app.after_request
def log_response(response):
    request_id = str(g.request_id)
    response.headers["X-Request-ID"] = request_id
    request_logger.info(json.dumps({
        "request_id": request_id,
        "endpoint": request.endpoint,
        "method": request.method,
        "status": response.status_code,
        "error_type": g.get("error_type"),
    }))
    return response


# Give users a short HTTP error message while preserving the original status and headers.
@app.errorhandler(HTTPException)
def handle_http_error(error):
    messages = {
        400: "Invalid request. Reload the page and try again.",
        403: "Access denied.",
        404: "Page not found.",
        405: "Method not allowed.",
        413: "Request is too large.",
        429: "Too many requests. Try again later.",
    }
    response = error.get_response()
    response.set_data(messages.get(error.code, "The request could not be completed."))
    response.mimetype = "text/plain"
    return response


# Return a generic 500 and record only the exception type for unexpected errors.
@app.errorhandler(Exception)
def handle_unexpected_error(error):
    g.error_type = type(error).__name__
    return "The request could not be completed.", 500


def database_uri():
    """Use DATABASE_URL when set, otherwise use the local SQLite file."""
    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    return "sqlite:///brom-el-ard.sqlite3"


app.config["SQLALCHEMY_DATABASE_URI"] = database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if os.environ.get("RENDER") == "true": # automatically set by render for the deployed service
    if app.secret_key.strip() in ("", LOCAL_SECRET_KEY):
        raise RuntimeError("Set a private SECRET_KEY environment variable for this Render service")
    # Require a well-formed PostgreSQL database URL on Render
    error = "Set a valid PostgreSQL DATABASE_URL on Render"
    try:
        url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])

        if url.drivername != "postgresql+psycopg2" or not url.host or not url.database:
            raise RuntimeError(error)
    except (ArgumentError, ValueError):
        raise RuntimeError(error) from None


db.init_app(app)
with app.app_context():
    if db.engine.dialect.name == "sqlite":
        @event.listens_for(db.engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys = ON").close()


@app.cli.command("init-db")
def init_db():
    """Create the proposal's database tables."""
    db.create_all()
    print("Database initialized.")


"""
Look up the signed-in user once per request.
Clear the session if the user ID is invalid or the account is missing or inactive.
"""
def get_current_user():
    if "current_user" in g:
        return g.current_user

    user_id = session.get("user_id")
    user = None
    if type(user_id) is int and 0 < user_id < 2**31:
        user = db.session.get(User, user_id)

    g.current_user = user if user is not None and user.is_active else None
    if g.current_user is None and "user_id" in session:
        session.clear()

    return g.current_user


@app.context_processor
def inject_globals():
    """Make the logged-in user (and their favorite ids) available in templates."""
    user = get_current_user()
    favorite_ids = set()
    if user is not None:
        favorite_ids = {favorite.place_id for favorite in user.favorites}
    return {"current_user": user, "favorite_ids": favorite_ids}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if get_current_user() is None:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# Allow only active admins to access this route.
def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if get_current_user().role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


# Find a record owned by the signed-in user, or return 404.
def owned_or_404(model, record_id):
    user = get_current_user()
    if user is None or not 0 < record_id < 2**31:
        abort(404)

    return db.first_or_404(
        db.select(model).filter_by(id=record_id, user_id=user.id)
    )


# ---------- content (from your API) --------------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/search")
def search():
    city = request.args.get("city", "").strip()
    country = request.args.get("country", "").strip()
    public_api_config = {
        "geoapifyKey": app.config["GEOAPIFY_API_KEY"],
        "geoapifyTileUrl": app.config["GEOAPIFY_TILE_URL"],
        "geocodingUrl": app.config["GEOCODING_API_URL"],
        "forecastUrl": app.config["FORECAST_API_URL"],
        "wikimediaUrl": app.config["WIKIMEDIA_API_URL"],
    }
    return render_template(
        "results.html", city=city, country=country, public_api_config=public_api_config
    )


@app.route("/api/places")
def places_api():
    try:
        latitude = float(request.args.get("lat", ""))
        longitude = float(request.args.get("lon", ""))
    except ValueError:
        return jsonify({"error": "Map coordinates are missing or invalid."}), 400

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return jsonify({"error": "Map coordinates are outside the valid range."}), 400

    try:
        places = api_client.search_places(latitude, longitude)
    except requests.RequestException:
        app.logger.warning("Nearby places request failed")
        return jsonify({"error": "Nearby places are temporarily unavailable."}), 502

    return jsonify({"places": places})


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
    if request.method == "POST":
        # Reject invalid signup fields before account creation.
        errors, email = validate_signup(request.form)
        if errors:
            return render_template("signup.html", errors=errors, data={"email": email})
        existing = db.session.scalar(db.select(User).filter_by(normalized_email=email))
        if existing is not None:
            errors["email"] = "An account with this email already exists."
            return render_template("signup.html", errors=errors, data={"email": email})
        password = request.form.get("password", "")
        user = User(normalized_email=email,password_hash=generate_password_hash(password))
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            errors["email"] = "An account with this email already exists."
            return render_template("signup.html", errors=errors, data={"email": email})
        session.clear()
        session["user_id"] = user.id
        session.permanent = True
        flash("Welcome! Your account has been created.")
        return redirect(url_for("home"))
    return render_template("signup.html", errors={}, data={})


@app.route("/login", methods=["GET", "POST"])
# Limit submitted login attempts while allowing users to open the form.
@limiter.limit("5/minute", methods=["POST"])
def login():
    if request.method == "POST":
        # Reject invalid login fields before credential verification.
        errors, email = validate_login(request.form)
        if errors:
            return render_template("login.html", errors=errors, data={"email": email})
        # TODO: implement log-in (see the Sessions & Login slides).
        pass
    return render_template("login.html", errors={}, data={})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))


# ---------- favorites (login required) -----------------------------
@app.route("/favorites")
@login_required
def favorites():
    items = Favorite.query.filter_by(user_id=session["user_id"]).all()
    return render_template("favorites.html", favorites=items)


@app.route("/favorites/add", methods=["POST"])
@login_required
def favorites_add():
    item_id = request.form.get("item_id", "").strip()
    if item_id:
        exists = Favorite.query.filter_by(
            user_id=session["user_id"], item_id=item_id).first()
        if exists:
            flash("Already in your favorites.")
        else:
            db.session.add(Favorite(
                user_id=session["user_id"], item_id=item_id,
                item_title=request.form.get("item_title", ""),
                item_image=request.form.get("item_image", "")))
            db.session.commit()
            flash("Saved to favorites.")
    return redirect(request.form.get("next") or url_for("favorites"))


@app.route("/favorites/remove", methods=["POST"])
@login_required
def favorites_remove():
    item_id = request.form.get("item_id", "").strip()
    fav = Favorite.query.filter_by(
        user_id=session["user_id"], item_id=item_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("Removed from favorites.")
    return redirect(request.form.get("next") or url_for("favorites"))


if __name__ == "__main__":
    app.run(debug=True)
