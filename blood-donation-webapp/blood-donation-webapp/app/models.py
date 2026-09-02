"""
SQLAlchemy models for the Blood Donation Web Application.

These models run unchanged against SQLite (default, for local dev and
tests) or MySQL (via DATABASE_URL, see README.md). schema.sql contains
the equivalent raw MySQL DDL for reference / manual provisioning.
"""
from datetime import date, datetime

from app import db

# Valid blood group values, shared by both models and by form validation.
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

URGENCY_LEVELS = ["Low", "Medium", "High", "Critical"]


class Donor(db.Model):
    __tablename__ = "donors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    blood_group = db.Column(db.String(3), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    last_donation_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def is_eligible(self, as_of=None, min_days_since_donation=90):
        """
        A donor is eligible to donate again if they have never donated
        before, or if at least `min_days_since_donation` days have
        passed since their last recorded donation. This mirrors the
        real-world medical guideline that donors need a recovery
        window (commonly ~90 days for whole blood) between donations.
        """
        if self.last_donation_date is None:
            return True
        as_of = as_of or date.today()
        days_since = (as_of - self.last_donation_date).days
        return days_since >= min_days_since_donation

    def days_until_eligible(self, as_of=None, min_days_since_donation=90):
        """Returns 0 if already eligible, otherwise days remaining."""
        if self.is_eligible(as_of, min_days_since_donation):
            return 0
        as_of = as_of or date.today()
        days_since = (as_of - self.last_donation_date).days
        return min_days_since_donation - days_since

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "blood_group": self.blood_group,
            "email": self.email,
            "phone": self.phone,
            "city": self.city,
            "last_donation_date": (
                self.last_donation_date.isoformat() if self.last_donation_date else None
            ),
            "eligible": self.is_eligible(),
        }

    def __repr__(self):
        return f"<Donor {self.name} ({self.blood_group}) - {self.city}>"


class BloodRequest(db.Model):
    __tablename__ = "blood_requests"

    id = db.Column(db.Integer, primary_key=True)
    requester_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    blood_group = db.Column(db.String(3), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    hospital = db.Column(db.String(150), nullable=True)
    units_needed = db.Column(db.Integer, nullable=False, default=1)
    urgency = db.Column(db.String(10), nullable=False, default="Medium")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "requester_name": self.requester_name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "blood_group": self.blood_group,
            "city": self.city,
            "hospital": self.hospital,
            "units_needed": self.units_needed,
            "urgency": self.urgency,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<BloodRequest {self.blood_group} for {self.requester_name} in {self.city}>"


class BloodInventory(db.Model):
    """
    A simple stock-by-blood-type tracker: one row per blood group with
    the number of units currently on hand. This is intentionally a
    standalone tracker -- registering a donor does NOT auto-increment
    it, since a donor registration is not the same event as an actual
    blood collection (that's a separate real-world step handled by
    staff). Stock is only ever changed explicitly, via the "Update
    Stock" form on the inventory page.
    """

    __tablename__ = "blood_inventory"

    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(3), nullable=False, unique=True, index=True)
    units_available = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        return {
            "blood_group": self.blood_group,
            "units_available": self.units_available,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    def __repr__(self):
        return f"<BloodInventory {self.blood_group}: {self.units_available} units>"


def seed_blood_inventory():
    """
    Ensure every standard blood group has an inventory row (starting at
    0 units) so the inventory page always has all 8 groups to show and
    adjust, mirroring the seed INSERTs in schema.sql. Safe to call
    repeatedly -- only missing groups are inserted.
    """
    existing = {row.blood_group for row in BloodInventory.query.all()}
    missing = [bg for bg in BLOOD_GROUPS if bg not in existing]
    for bg in missing:
        db.session.add(BloodInventory(blood_group=bg, units_available=0))
    if missing:
        db.session.commit()
