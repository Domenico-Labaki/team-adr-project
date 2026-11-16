"""Explicit setup for the proposal schema."""
from sqlalchemy import inspect

from models import db


def enable_sqlite_foreign_keys(connection, _record):
    connection.execute("PRAGMA foreign_keys = ON").close()


def initialize_database(*, reset=False):
    with db.engine.begin() as connection:
        is_postgres = connection.dialect.name == "postgresql"
        if is_postgres:
            # Serialize schema setup in this database until this transaction ends.
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(44604)")
        elif connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            raise ValueError("Choose PostgreSQL or local SQLite to initialize the proposal schema.")

        inspector = inspect(connection)
        existing = set(inspector.get_table_names())
        tables = db.metadata.tables
        if existing and (
            existing != set(tables)
            or any(
                {column["name"] for column in inspector.get_columns(name)} != set(table.columns.keys())
                for name, table in tables.items()
            )
        ):
            raise ValueError("The target contains a different schema. Choose a fresh database.")

        if reset:
            db.metadata.drop_all(connection)
        db.metadata.create_all(connection)

        if is_postgres:
            connection.exec_driver_sql("""
                CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    NEW.updated_at := statement_timestamp();
                    RETURN NEW;
                END;
                $$
            """)
            for table in tables.values():
                if "updated_at" in table.columns:
                    name = connection.dialect.identifier_preparer.quote(table.name)
                    connection.exec_driver_sql(f"""
                        CREATE OR REPLACE TRIGGER set_updated_at
                        BEFORE UPDATE ON {name}
                        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
                    """)
