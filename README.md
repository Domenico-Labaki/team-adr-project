# Team Project Starter (Flask)

A starter for the GIN446 team project: a full-stack Flask web app whose content
comes from a free external API. It runs out of the box on sample data so you can
deploy it first, then make it your own.

**You build the authentication yourself.** The starter gives you the structure,
the API client, the templates, the data models and the database wiring - but the
sign-up / log-in / log-out / session logic is left as **stubs for you to
implement** (see the "Sessions & Login" slides).

## What it does (starter state)
- Browse sample items, search, open a detail page.
- A `User` and a `Favorite` table are defined; `favorites` routes are a worked
  example that uses the session (they work once you implement log-in).
- Auth routes exist but are empty - that's your job.

## Run it in VS Code
1. Open this folder in VS Code.
2. Create and activate a virtual environment:
   - Windows: `python -m venv venv` then `venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv venv` then `source venv/bin/activate`
3. `pip install -r requirements.txt`
4. Initialize the local SQLite database, then start Flask. These commands skip
   `.env` and select SQLite explicitly so local tests use the local database
   even if `.env` points to Render.
   - macOS/Linux

     ```bash
     FLASK_SKIP_DOTENV=1 DATABASE_URL=sqlite:///brom-el-ard.sqlite3 python -m flask --app app init-db
     FLASK_SKIP_DOTENV=1 DATABASE_URL=sqlite:///brom-el-ard.sqlite3 python -m flask --app app run --debug
     ```

   - Windows PowerShell

     ```powershell
     $env:FLASK_SKIP_DOTENV = '1'
     $env:DATABASE_URL = 'sqlite:///brom-el-ard.sqlite3'
     python -m flask --app app init-db
     python -m flask --app app run --debug
     ```

5. Open `http://127.0.0.1:5000`.

## The database
- `models.py` defines the six database tables.
- The local database is `instance/brom-el-ard.sqlite3`. Its data persists across
  restarts, and it is separate from the starter `app.db`.
- Run `flask init-db` before the first startup. It creates missing tables and
  preserves existing data. Changes to existing tables require a migration.

## Environment variables

Installing the project requirements includes `python-dotenv`. Flask CLI commands
load the environment settings from `.env` when you run them from the project
directory. Environment variables already set in your shell or on the command
line take precedence over values in `.env`. Git ignores `.env`.

Copy the API settings from `.env.example` into your ignored `.env`, and set
`GEOAPIFY_API_KEY` to your browser map key. API URLs have the defaults shown in
`.env.example`; the key has no default. Without a key, weather and places still
load, and the map displays an unavailable message.

Geoapify, Open-Meteo geocoding/forecast, and Wikipedia settings are serialized
into the destination page for direct browser requests. The Geoapify key remains
visible to visitors in the page and tile requests. `OVERPASS_API_URL` stays on
the server. `SECRET_KEY` and `DATABASE_URL` are never included in this public
configuration. Attribution, sample-image, and library CDN links are not API
configuration and remain in the source.

On Render, set the same variables in the service's Environment settings and
restart the service after changing them. For local use, Flask CLI loads `.env`;
Gunicorn reads the variables supplied by its process environment.

## Your work (the TODOs)
- **Authentication** - implement `signup`, `login`, `logout` and sessions in
  `app.py` (hash passwords, store `session["user_id"]`, gate routes, clear on
  logout). Validators are provided in `validators.py`.
- **`api_client.py`** - replace the sample data with calls to *your* chosen API.
  Keep the shapes: `search(q)` -> list of `{id, title, image}`;
  `get_item(id)` -> one `{id, title, image, description}`.
- **`templates/`** - change the wording and show the fields your API returns.

## Structure
```
app.py            routes; auth stubs you implement (the controller)
api_client.py     all calls to your external API (edit this)
validators.py     server-side validation for sign-up / log-in (provided)
models.py         six database models
reset_db.py       drop and recreate the tables for local development
templates/        pages (the view)
static/style.css
requirements.txt  packages
Procfile          start command for Render (gunicorn)
```

## Deploy
Push to your **team GitHub repo**, then follow the **"Set Up Your Team's Database
on Render"** activity to add a PostgreSQL database and go live.

Use the existing Render PostgreSQL user for initialization and for the web
service. To initialize a fresh database from your laptop, set `DATABASE_URL`
in your local `.env` to that user's External Database URL. Run this command
from the project directory.

```bash
python -m flask --app app init-db
```

Set these values in the Render web service's **Environment** settings.

- `SECRET_KEY` — a private key Flask uses to sign sessions.
- `DATABASE_URL` — the Internal Database URL for the same Render PostgreSQL user.

<!-- Keep the documented start command consistent with the in-memory rate limits. -->
Use `gunicorn --workers 1 app:app` as the start command so requests share the
same in-memory rate-limit counters.
