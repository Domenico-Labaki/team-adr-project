"""The six database models in the Brom el ARD application."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Timestamps:
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )


class User(Timestamps, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    normalized_email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(16), nullable=False, server_default="user")
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())
    favorites = db.relationship(
        "Favorite", backref="user", cascade="all, delete-orphan"
    )
    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'admin')", name="user_role"),
    )


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    provider = db.Column(db.String(16), nullable=False)
    place_id = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )
    __table_args__ = (
        db.CheckConstraint("provider IN ('yelp', 'overpass')", name="favorite_provider"),
        db.UniqueConstraint("user_id", "provider", "place_id", name="favorite_owner_place"),
    )


class Destination(Timestamps, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    geoapify_place_id = db.Column(db.Text, unique=True, nullable=False)
    country_code = db.Column(db.CHAR(2), nullable=False)
    country = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    region = db.Column(db.String(120))
    latitude = db.Column(db.Numeric(9, 6), nullable=False)
    longitude = db.Column(db.Numeric(9, 6), nullable=False)
    timezone = db.Column(db.String(64))
    description = db.Column(db.Text)
    is_featured = db.Column(db.Boolean, nullable=False, server_default=db.false())
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    __table_args__ = (
        db.CheckConstraint("latitude BETWEEN -90 AND 90", name="destination_latitude"),
        db.CheckConstraint("longitude BETWEEN -180 AND 180", name="destination_longitude"),
    )


class Itinerary(Timestamps, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey("destination.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(16), nullable=False, server_default="draft")
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    __table_args__ = (
        db.CheckConstraint("status IN ('draft', 'finalized')", name="itinerary_status"),
        db.CheckConstraint(
            "(start_date IS NULL AND end_date IS NULL) OR "
            "(start_date IS NOT NULL AND end_date IS NOT NULL AND end_date >= start_date)",
            name="itinerary_dates",
        ),
    )


class ItineraryStop(Timestamps, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    itinerary_id = db.Column(
        db.Integer, db.ForeignKey("itinerary.id", ondelete="CASCADE"), nullable=False
    )
    provider = db.Column(db.String(16), nullable=False)
    place_id = db.Column(db.Text, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text)
    __table_args__ = (
        db.CheckConstraint("provider IN ('yelp', 'overpass')", name="itinerary_stop_provider"),
        db.CheckConstraint("day > 0 AND position > 0", name="itinerary_stop_positive_order"),
        db.UniqueConstraint("itinerary_id", "day", "position", name="itinerary_stop_slot"),
    )


class AuditLog(db.Model):
    id = db.Column(db.BigInteger().with_variant(db.Integer(), "sqlite"), primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(32), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    request_id = db.Column(db.Uuid, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )
