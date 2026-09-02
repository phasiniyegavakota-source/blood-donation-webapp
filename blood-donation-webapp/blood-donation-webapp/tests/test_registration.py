from datetime import date, timedelta

from app import db
from app.models import Donor
from app.validators import validate_donor_registration


def _valid_form(**overrides):
    form = {
        "name": "Priya Sharma",
        "blood_group": "O+",
        "email": "priya@example.com",
        "phone": "555-123-4567",
        "city": "Springfield",
        "last_donation_date": "",
    }
    form.update(overrides)
    return form


class TestValidation:
    def test_valid_form_has_no_errors(self):
        errors, cleaned = validate_donor_registration(_valid_form())
        assert errors == {}
        assert cleaned["blood_group"] == "O+"
        assert cleaned["last_donation_date"] is None

    def test_missing_required_fields_rejected(self):
        errors, _ = validate_donor_registration(_valid_form(name="", email=""))
        assert "name" in errors
        assert "email" in errors

    def test_invalid_blood_group_rejected(self):
        errors, _ = validate_donor_registration(_valid_form(blood_group="Z+"))
        assert "blood_group" in errors

    def test_invalid_email_rejected(self):
        errors, _ = validate_donor_registration(_valid_form(email="not-an-email"))
        assert "email" in errors

    def test_invalid_phone_rejected(self):
        errors, _ = validate_donor_registration(_valid_form(phone="abc"))
        assert "phone" in errors

    def test_future_donation_date_rejected(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        errors, _ = validate_donor_registration(_valid_form(last_donation_date=future))
        assert "last_donation_date" in errors

    def test_valid_past_donation_date_parsed(self):
        past = (date.today() - timedelta(days=200)).isoformat()
        errors, cleaned = validate_donor_registration(_valid_form(last_donation_date=past))
        assert errors == {}
        assert cleaned["last_donation_date"].isoformat() == past


class TestRegisterRoute:
    def test_register_page_loads(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200
        assert b"Become a Donor" in resp.data

    def test_successful_registration_creates_donor(self, client, app):
        resp = client.post("/register", data=_valid_form(), follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            donor = Donor.query.filter_by(email="priya@example.com").first()
            assert donor is not None
            assert donor.blood_group == "O+"
            assert donor.city == "Springfield"

    def test_missing_fields_returns_400_with_errors(self, client):
        resp = client.post("/register", data=_valid_form(name=""))
        assert resp.status_code == 400
        assert b"required" in resp.data.lower()

    def test_duplicate_email_or_phone_is_rejected(self, client):
        first = client.post("/register", data=_valid_form())
        assert first.status_code == 200

        # Same email, different phone -> still a duplicate.
        second = client.post(
            "/register", data=_valid_form(phone="555-999-0000")
        )
        assert second.status_code == 400
        assert b"already registered" in second.data.lower()

    def test_duplicate_phone_with_different_email_is_rejected(self, client):
        client.post("/register", data=_valid_form())
        resp = client.post(
            "/register", data=_valid_form(email="someoneelse@example.com")
        )
        assert resp.status_code == 400
        assert b"already registered" in resp.data.lower()
