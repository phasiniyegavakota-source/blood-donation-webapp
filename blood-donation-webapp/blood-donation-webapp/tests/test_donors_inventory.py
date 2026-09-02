from app import db
from app.models import BLOOD_GROUPS, BloodInventory, Donor


def _add_donor(name, blood_group, city, email=None, phone=None):
    donor = Donor(
        name=name,
        blood_group=blood_group,
        email=email or f"{name.lower().replace(' ', '.')}@example.com",
        phone=phone or f"555-{abs(hash(name)) % 10000:04d}",
        city=city,
    )
    db.session.add(donor)
    db.session.commit()
    return donor


class TestDonorsRoute:
    def test_donors_page_loads_with_no_donors(self, client):
        resp = client.get("/donors")
        assert resp.status_code == 200
        assert b"Registered Donors" in resp.data
        assert b"No donors have registered yet" in resp.data

    def test_donors_page_lists_registered_donor(self, client, app):
        with app.app_context():
            _add_donor("Taylor Reed", "O+", "Metropolis")

        resp = client.get("/donors")
        assert resp.status_code == 200
        assert b"Taylor Reed" in resp.data
        assert b"Metropolis" in resp.data


class TestInventoryRoute:
    def test_inventory_page_loads_and_seeds_all_blood_groups(self, client, app):
        resp = client.get("/inventory")
        assert resp.status_code == 200
        assert b"Blood Inventory" in resp.data
        for bg in BLOOD_GROUPS:
            assert bg.encode() in resp.data

        with app.app_context():
            assert BloodInventory.query.count() == len(BLOOD_GROUPS)
            assert all(row.units_available == 0 for row in BloodInventory.query.all())

    def test_inventory_adjust_updates_units(self, client, app):
        resp = client.post(
            "/inventory/adjust",
            data={"blood_group": "O+", "units_available": "12"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Stock updated successfully" in resp.data

        with app.app_context():
            record = BloodInventory.query.filter_by(blood_group="O+").first()
            assert record is not None
            assert record.units_available == 12

    def test_inventory_adjust_rejects_invalid_blood_group(self, client):
        resp = client.post(
            "/inventory/adjust",
            data={"blood_group": "ZZ", "units_available": "5"},
        )
        assert resp.status_code == 400

    def test_inventory_adjust_rejects_negative_units(self, client):
        resp = client.post(
            "/inventory/adjust",
            data={"blood_group": "A+", "units_available": "-3"},
        )
        assert resp.status_code == 400
        assert b"between 0 and 100000" in resp.data
