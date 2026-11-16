"""Reset the disposable local proposal database."""
from app import DEFAULT_DATABASE_URI, app
from database import initialize_database


if __name__ == "__main__":
    if app.config["ON_RENDER"] or app.config["SQLALCHEMY_DATABASE_URI"] != DEFAULT_DATABASE_URI:
        raise SystemExit("Reset is available only for the default local SQLite database.")
    with app.app_context():
        try:
            initialize_database(reset=True)
        except ValueError as error:
            raise SystemExit(str(error)) from None
    print("Local proposal database reset.")
