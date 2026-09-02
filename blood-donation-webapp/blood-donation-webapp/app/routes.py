"""
Routes for the Blood Donation Web Application.

Server-rendered pages (home, register, search, request) plus a couple
of small JSON endpoints (/api/search, /api/donors/<id>) that the search
page also calls under the hood, and that a future frontend or mobile
client could reuse directly.
"""
from flask import Blueprint, jsonify, render_template, request

from app import db
from app.models import BLOOD_GROUPS, URGENCY_LEVELS, BloodInventory, BloodRequest, Donor
from app.validators import (
    validate_blood_request,
    validate_donor_registration,
    validate_inventory_adjustment,
)

main_bp = Blueprint("main", __name__)


def _eligibility_days():
    from flask import current_app

    return current_app.config.get("DONATION_ELIGIBILITY_DAYS", 90)


# ---------------------------------------------------------------- pages ---

@main_bp.route("/")
def home():
    donor_count = Donor.query.count()
    request_count = BloodRequest.query.count()
    inventory_units = (
        db.session.query(db.func.coalesce(db.func.sum(BloodInventory.units_available), 0)).scalar()
    )
    return render_template(
        "index.html",
        donor_count=donor_count,
        request_count=request_count,
        inventory_units=inventory_units,
    )


@main_bp.route("/donors")
def donors():
    donor_list = Donor.query.order_by(Donor.name.asc()).all()
    return render_template("donors.html", donors=donor_list)


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", blood_groups=BLOOD_GROUPS, errors={}, form={})

    errors, cleaned = validate_donor_registration(request.form)

    if not errors:
        existing = Donor.query.filter(
            (Donor.email == cleaned["email"]) | (Donor.phone == cleaned["phone"])
        ).first()
        if existing:
            errors["duplicate"] = (
                "A donor with this email or phone number is already registered."
            )

    if errors:
        return render_template(
            "register.html",
            blood_groups=BLOOD_GROUPS,
            errors=errors,
            form=request.form,
        ), 400

    donor = Donor(
        name=cleaned["name"],
        blood_group=cleaned["blood_group"],
        email=cleaned["email"],
        phone=cleaned["phone"],
        city=cleaned["city"],
        last_donation_date=cleaned["last_donation_date"],
    )
    db.session.add(donor)
    db.session.commit()

    return render_template("register.html", success=True, donor=donor, blood_groups=BLOOD_GROUPS, errors={}, form={})


@main_bp.route("/search", methods=["GET"])
def search():
    blood_group = (request.args.get("blood_group") or "").strip().upper()
    city = (request.args.get("city") or "").strip()

    donors = []
    searched = bool(blood_group or city)

    if searched:
        donors = _find_eligible_donors(blood_group, city)

    return render_template(
        "search.html",
        blood_groups=BLOOD_GROUPS,
        donors=donors,
        searched=searched,
        blood_group=blood_group,
        city=city,
        eligibility_days=_eligibility_days(),
    )


@main_bp.route("/request-blood", methods=["GET", "POST"])
def request_blood():
    if request.method == "GET":
        return render_template(
            "request.html", blood_groups=BLOOD_GROUPS, urgency_levels=URGENCY_LEVELS, errors={}, form={}
        )

    errors, cleaned = validate_blood_request(request.form)

    if errors:
        return render_template(
            "request.html",
            blood_groups=BLOOD_GROUPS,
            urgency_levels=URGENCY_LEVELS,
            errors=errors,
            form=request.form,
        ), 400

    blood_req = BloodRequest(**cleaned)
    db.session.add(blood_req)
    db.session.commit()

    matches = _find_eligible_donors(cleaned["blood_group"], cleaned["city"])

    return render_template(
        "request.html",
        success=True,
        blood_request=blood_req,
        matches=matches,
        blood_groups=BLOOD_GROUPS,
        urgency_levels=URGENCY_LEVELS,
        errors={},
        form={},
    )


@main_bp.route("/inventory", methods=["GET"])
def inventory():
    return render_template(
        "inventory.html",
        inventory=_ordered_inventory(),
        blood_groups=BLOOD_GROUPS,
        errors={},
    )


@main_bp.route("/inventory/adjust", methods=["POST"])
def inventory_adjust():
    """
    Sets the on-hand unit count for one blood group. Intentionally a
    standalone, explicit action -- donor registration does NOT touch
    inventory automatically, since registering as a donor isn't the
    same event as blood actually being collected.
    """
    errors, cleaned = validate_inventory_adjustment(request.form)

    if not errors:
        record = BloodInventory.query.filter_by(blood_group=cleaned["blood_group"]).first()
        if record is None:
            record = BloodInventory(blood_group=cleaned["blood_group"])
            db.session.add(record)
        record.units_available = cleaned["units_available"]
        db.session.commit()

    status_code = 400 if errors else 200
    return render_template(
        "inventory.html",
        inventory=_ordered_inventory(),
        blood_groups=BLOOD_GROUPS,
        errors=errors,
        success=not errors,
    ), status_code


# ------------------------------------------------------------- JSON API ---

@main_bp.route("/api/search")
def api_search():
    blood_group = (request.args.get("blood_group") or "").strip().upper()
    city = (request.args.get("city") or "").strip()

    if blood_group and blood_group not in BLOOD_GROUPS:
        return jsonify({"error": f"Invalid blood_group. Must be one of {BLOOD_GROUPS}."}), 400

    donors = _find_eligible_donors(blood_group, city)
    return jsonify({
        "count": len(donors),
        "results": [d.to_dict() for d in donors],
    })


@main_bp.route("/api/donors/<int:donor_id>")
def api_donor_detail(donor_id):
    donor = Donor.query.get_or_404(donor_id)
    return jsonify(donor.to_dict())


# ----------------------------------------------------------------- core ---

def _find_eligible_donors(blood_group="", city=""):
    """
    Core donor-search / eligibility logic shared by the search page,
    the blood-request match list, and the JSON API.

    Filters donors by blood group (exact match) and city (case
    insensitive substring match), then excludes anyone who donated
    within the eligibility window (default 90 days) since real blood
    banks require a recovery period between donations.
    """
    query = Donor.query
    if blood_group:
        query = query.filter(Donor.blood_group == blood_group)
    if city:
        query = query.filter(Donor.city.ilike(f"%{city}%"))

    candidates = query.order_by(Donor.name.asc()).all()
    min_days = _eligibility_days()
    return [d for d in candidates if d.is_eligible(min_days_since_donation=min_days)]


def _ordered_inventory():
    """Inventory rows sorted in the standard blood-group order (A+, A-,
    B+, B-, AB+, AB-, O+, O-) rather than alphabetically."""
    rows = BloodInventory.query.all()
    return sorted(rows, key=lambda row: BLOOD_GROUPS.index(row.blood_group))
