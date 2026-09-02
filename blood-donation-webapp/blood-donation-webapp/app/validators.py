"""
Backend validation helpers used by both the HTML form routes and the
JSON API routes, so validation rules live in exactly one place.
"""
import re
from datetime import date, datetime

from email_validator import EmailNotValidError, validate_email

from app.models import BLOOD_GROUPS, URGENCY_LEVELS

# Accepts formats like: 1234567890, 123-456-7890, (123) 456-7890,
# +1 123 456 7890 -- basically 7-15 digits with optional separators.
PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")


class ValidationError(Exception):
    """Raised with a dict of {field_name: message} validation errors."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))


def _require(value):
    return value is not None and str(value).strip() != ""


def validate_name(value, field="name"):
    errors = {}
    if not _require(value):
        errors[field] = "Name is required."
    elif len(value.strip()) < 2:
        errors[field] = "Name must be at least 2 characters."
    elif len(value.strip()) > 100:
        errors[field] = "Name must be 100 characters or fewer."
    return errors


def validate_blood_group(value, field="blood_group"):
    errors = {}
    if not _require(value):
        errors[field] = "Blood group is required."
    elif value.strip().upper() not in BLOOD_GROUPS:
        errors[field] = f"Blood group must be one of: {', '.join(BLOOD_GROUPS)}."
    return errors


def validate_email_field(value, field="email"):
    errors = {}
    if not _require(value):
        errors[field] = "Email is required."
    else:
        try:
            validate_email(value.strip(), check_deliverability=False)
        except EmailNotValidError:
            errors[field] = "Enter a valid email address."
    return errors


def validate_phone(value, field="phone"):
    errors = {}
    if not _require(value):
        errors[field] = "Phone number is required."
    else:
        digits_only = re.sub(r"\D", "", value)
        if not PHONE_RE.match(value.strip()) or not (7 <= len(digits_only) <= 15):
            errors[field] = "Enter a valid phone number (7-15 digits)."
    return errors


def validate_city(value, field="city"):
    errors = {}
    if not _require(value):
        errors[field] = "City / location is required."
    elif len(value.strip()) > 100:
        errors[field] = "City must be 100 characters or fewer."
    return errors


def validate_last_donation_date(value, field="last_donation_date"):
    """value may be an empty string (never donated) or an ISO date string."""
    errors = {}
    if value is None or str(value).strip() == "":
        return errors, None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        errors[field] = "Last donation date must be in YYYY-MM-DD format."
        return errors, None
    if parsed > date.today():
        errors[field] = "Last donation date cannot be in the future."
        return errors, None
    return errors, parsed


def validate_urgency(value, field="urgency"):
    errors = {}
    if not _require(value):
        errors[field] = "Urgency is required."
    elif value.strip().title() not in URGENCY_LEVELS:
        errors[field] = f"Urgency must be one of: {', '.join(URGENCY_LEVELS)}."
    return errors


def validate_units(value, field="units_needed"):
    errors = {}
    try:
        units = int(value)
        if units < 1 or units > 50:
            errors[field] = "Units needed must be between 1 and 50."
    except (TypeError, ValueError):
        errors[field] = "Units needed must be a whole number."
    return errors


def validate_donor_registration(form):
    """
    Validates a donor registration submission (a dict-like object,
    e.g. request.form). Returns (errors: dict, cleaned: dict).
    `cleaned` only contains keys that passed validation.
    """
    errors = {}
    cleaned = {}

    errors.update(validate_name(form.get("name")))
    cleaned["name"] = (form.get("name") or "").strip()

    errors.update(validate_blood_group(form.get("blood_group")))
    cleaned["blood_group"] = (form.get("blood_group") or "").strip().upper()

    errors.update(validate_email_field(form.get("email")))
    cleaned["email"] = (form.get("email") or "").strip().lower()

    errors.update(validate_phone(form.get("phone")))
    cleaned["phone"] = (form.get("phone") or "").strip()

    errors.update(validate_city(form.get("city")))
    cleaned["city"] = (form.get("city") or "").strip()

    date_errors, parsed_date = validate_last_donation_date(form.get("last_donation_date"))
    errors.update(date_errors)
    cleaned["last_donation_date"] = parsed_date

    return errors, cleaned


def validate_blood_request(form):
    """
    Validates a blood request submission. Returns (errors, cleaned).
    """
    errors = {}
    cleaned = {}

    errors.update(validate_name(form.get("requester_name"), field="requester_name"))
    cleaned["requester_name"] = (form.get("requester_name") or "").strip()

    errors.update(validate_email_field(form.get("contact_email"), field="contact_email"))
    cleaned["contact_email"] = (form.get("contact_email") or "").strip().lower()

    errors.update(validate_phone(form.get("contact_phone"), field="contact_phone"))
    cleaned["contact_phone"] = (form.get("contact_phone") or "").strip()

    errors.update(validate_blood_group(form.get("blood_group")))
    cleaned["blood_group"] = (form.get("blood_group") or "").strip().upper()

    errors.update(validate_city(form.get("city")))
    cleaned["city"] = (form.get("city") or "").strip()

    errors.update(validate_urgency(form.get("urgency")))
    cleaned["urgency"] = (form.get("urgency") or "").strip().title()

    errors.update(validate_units(form.get("units_needed", 1)))
    try:
        cleaned["units_needed"] = int(form.get("units_needed", 1))
    except (TypeError, ValueError):
        cleaned["units_needed"] = 1

    cleaned["hospital"] = (form.get("hospital") or "").strip() or None
    cleaned["notes"] = (form.get("notes") or "").strip() or None

    return errors, cleaned


def validate_inventory_adjustment(form):
    """
    Validates an inventory "update stock" submission (blood group +
    new absolute units-available count). Returns (errors, cleaned).
    """
    errors = {}
    cleaned = {}

    errors.update(validate_blood_group(form.get("blood_group")))
    cleaned["blood_group"] = (form.get("blood_group") or "").strip().upper()

    units_value = form.get("units_available")
    try:
        units = int(units_value)
        if units < 0 or units > 100000:
            errors["units_available"] = "Units available must be between 0 and 100000."
        else:
            cleaned["units_available"] = units
    except (TypeError, ValueError):
        errors["units_available"] = "Units available must be a whole number."

    return errors, cleaned
