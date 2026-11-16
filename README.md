# Team Project Starter (Flask)

A starter for the GIN446 team project: a full-stack Flask web app whose content
comes from a free external API. It runs out of the box on sample data so you can
deploy it first, then make it your own.

**You build the authentication yourself.** The starter gives you the structure,
the API client, the templates, the data models and the database wiring - but the
sign-up and log-in account logic is left as **stubs for you to implement** (see
the "Sessions & Login" slides).

## What it does (starter state)
- Browse sample items, search, open a detail page.
- The proposal's six tables are defined in `models.py`.
- Sign-up and log-in forms validate input. Account creation and password
  verification are part of SCRUM-7.

## Run locally

1. From the repository root, create and activate a virtual environment.
   - macOS/Linux — `python3 -m venv .venv` and `source .venv/bin/activate`
   - Windows PowerShell — `python -m venv .venv` and `.\.venv\Scripts\Activate.ps1`
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. In a local shell with `DATABASE_URL` unset, set `FLASK_SKIP_DOTENV=1` to
   keep the local run on SQLite. On macOS/Linux use `export FLASK_SKIP_DOTENV=1`.
   In PowerShell use `$env:FLASK_SKIP_DOTENV = '1'`.
4. Run `flask --app app init-db`, then `flask run --debug`.
5. Open `http://127.0.0.1:5000`.

The initializer creates `instance/brom-el-ard.sqlite3` for local work. It is a
separate file from the starter's `app.db`. The starter session key is for
local development. Set a private `SECRET_KEY` for a hosted run.

## The database
- `flask --app app init-db` creates the proposal tables in a fresh database.
  Running it again preserves rows. Use a new database if setup reports a
  different schema.
- `python reset_db.py` drops and recreates tables in the disposable default
  SQLite database. For normal setup, use `flask --app app init-db`.

## Your work (the TODOs)
- **Authentication** - implement account creation and credential checks in
  `signup` and `login`. Use the existing validators, store the integer user ID
  in `session["user_id"]`, and clear the old session before setting it on
  successful authentication. Set `session.permanent = True` for the
  configured eight-hour cookie. Log the login outcome through `log_event`
  and use the same failure message for unknown users and bad passwords.
- **`api_client.py`** - replace the sample data with calls to *your* chosen API.
  Keep the shapes: `search(q)` -> list of `{id, title, image}`;
  `get_item(id)` -> one `{id, title, image, description}`.
- **`templates/`** - change the wording and show the fields your API returns.
- **Advisor** - after authentication, call `check_advisor_limit(user_id)` on
  POST before contacting the provider. The rate limits are five advisor
  requests per account per minute and ten login submissions per client per
  15 minutes. Run a single worker so requests share those counters.

## Structure
```
app.py            routes, access checks, and the init-db command
api_client.py     all calls to your external API (edit this)
validators.py     server-side validation for sign-up / log-in (provided)
models.py         the six proposal models
database.py       explicit database initialization
reset_db.py       reset the default local SQLite database
request_security.py  form protection, rate limits, and request logs
runtime_grants.sql   PostgreSQL runtime permissions
templates/        pages (the view)
static/style.css
requirements.txt  packages
Procfile          start command for Render (gunicorn)
```

## Deploy

Render sets `RENDER=true` automatically. Initialize a fresh PostgreSQL database
before starting the web service. Use the schema owner's PostgreSQL URL as
`DATABASE_URL` for `flask --app app init-db`. Run the grants script as the
owner after creating a separate login role for the app with no ownership or
membership in the owner role. For example, with `DATABASE_URL` set to the
schema owner's `postgresql://` URL and `brom_runtime` as the runtime role:

```sh
psql "$DATABASE_URL" -v runtime_role=brom_runtime -f runtime_grants.sql
```

Write the audit row in the same transaction as the admin operation and use
`g.request_id` for its UUID. Use an inline SQLAlchemy Core insert on the audit
table to avoid implicit `RETURNING`.

In the Render web service's **Environment** settings, supply these variables
before starting the app with `gunicorn app:app`.

| Variable | Value |
| --- | --- |
| `SECRET_KEY` | A private random session key |
| `DATABASE_URL` | The runtime role's PostgreSQL connection URL |

You can generate a new session key with `python -c "import secrets; print(secrets.token_hex(32))"`.
Store the values in the service environment. Hosted startup fails if a value
is missing or invalid. Use the single-worker setup for the in-memory rate
limits.
