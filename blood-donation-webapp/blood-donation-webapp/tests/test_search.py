from datetime import date, timedelta

import pytest

from app import db
from app.models import Donor
from app.routes import _find_eligible_donors


def _add_donor(name, blood_group, city, last_donation_date=None, email=None, phone=None):
    donor = Donor(
        name=name,
        blood_group=blood_group,
        email=email or f"{name.lower().replace(' ', '.')}@example.com",
        phone=phone or f"555-{abs(hash(name)) % 10000:04d}",
        city=city,
        last_donation_date=last_donation_date,
    )
    db.session.add(donor)
    db.session.commit()
    return donor


class TestEligibilityLogic:
    def test_donor_with_no_past_donation_is_eligible(self, app):
        with app.app_context():
            donor = _add_donor("Alex Kim", "A+", "Springfield")
            assert donor.is_eligible() is True

    def test_donor_who_donated_recently_is_not_eligible(self, app):
        with app.app_context():
            recent = date.today() - timedelta(days=10)
            donor = _add_donor("Sam Lee", "A+", "Springfield", last_donation_date=recent)
            assert donor.is_eligible(min_days_since_donation=90) is False
            assert donor.days_until_eligible(min_days_since_donation=90) == 80

    def test_donor_past_eligibility_window_is_eligible(self, app):
        with app.app_context():
            old = date.today() - timedelta(days=100)
            donor = _add_donor("Jordan Ray", "A+", "Springfield", last_donation_date=old)
            assert donor.is_eligible(min_days_since_donation=90) is True

    def test_donor_exactly_at_boundary_is_eligible(self, app):
        with app.app_context():
            boundary = date.today() - timedelta(days=90)
            donor = _add_donor("Casey Fox", "A+", "Springfield", last_donation_date=boundary)
            assert donor.is_eligible(min_days_since_donation=90) is True


class TestFindEligibleDonors:
    def test_filters_by_blood_group_and_excludes_recent_donors(self, app):
        with app.app_context():
            _add_donor("Eligible ONeg", "O-", "Springfield")
            _add_donor(
                "Recent ONeg", "O-", "Springfield",
                last_donation_date=date.today() - timedelta(days=5),
            )
            _add_donor("Wrong Group", "AB+", "Springfield")

            results = _find_eligible_donors(blood_group="O-", city="")
            names = [d.name for d in results]

            assert "Eligible ONeg" in names
            assert "Recent ONeg" not in names
            assert "Wrong Group" not in names

    def test_filters_by_city_case_insensitive_substring(self, app):
        with app.app_context():
            _add_donor("City Match", "B+", "Springfield")
            _add_donor("City NoMatch", "B+", "Shelbyville")

            results = _find_eligible_donors(blood_group="B+", city="springfield")
            names = [d.name for d in results]

            assert "City Match" in names
            assert "City NoMatch" not in names

    def test_no_filters_returns_all_eligible_donors(self, app):
        with app.app_context():
            _add_donor("Donor One", "A+", "Springfield")
            _add_donor("Donor Two", "B-", "Shelbyville")

            results = _find_eligible_donors()
            assert len(results) == 2


class TestSearchRoute:
    def test_search_page_loads(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200
        assert b"Find Eligible Donors" in resp.data

    def test_search_returns_matching_donor(self, client, app):
        with app.app_context():
            _add_donor("Findable Donor", "AB+", "Metropolis")

        resp = client.get("/search?blood_group=AB%2B&city=Metropolis")
        assert resp.status_code == 200
        assert b"Findable Donor" in resp.data

    def test_search_excludes_recently_donated(self, client, app):
        with app.app_context():
            _add_donor(
                "Ineligible Donor", "AB-", "Gotham",
                last_donation_date=date.today() - timedelta(days=3),
            )

        resp = client.get("/search?blood_group=AB-&city=Gotham")
        assert resp.status_code == 200
        assert b"Ineligible Donor" not in resp.data
        assert b"No eligible donors match" in resp.data

    def test_api_search_returns_json(self, client, app):
        with app.app_context():
            _add_donor("Api Donor", "O+", "Star City")

        resp = client.get("/api/search?blood_group=O%2B&city=Star")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["count"] == 1
        assert payload["results"][0]["name"] == "Api Donor"

    def test_api_search_rejects_invalid_blood_group(self, client):
        resp = client.get("/api/search?blood_group=ZZ")
        assert resp.status_code == 400
