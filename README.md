🩸 Online Blood Donation Web Application
====================================================

![Python](https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Database-4479A1?logo=mysql&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-30%20passing-0A9EDC?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

A web-based blood donation management system built with **Python (Flask)**
and **MySQL** (SQLite for local development). It streamlines donor
registration and blood request processing, and implements database-driven
search to identify eligible donors by blood group and location — helping
coordinators respond faster in an emergency.

> Built as a portfolio/coursework project to demonstrate backend web
> development, relational data modeling, and server-side validation. Not a
> production medical system.

## Tech Stack

- **Backend:** Python 3, Flask
- **ORM / Database:** Flask-SQLAlchemy (SQLite for dev, MySQL for
  production via PyMySQL)
- **Validation:** Custom validators + `email-validator`
- **Templating:** Jinja2 (server-rendered HTML)
- **Styling:** Plain CSS, no frontend framework
- **Testing:** pytest

## Features

- 📝 **Donor Registration** — required-field, blood-group, email, and phone
  format validation, plus duplicate-registration prevention
- 🆘 **Blood Request Submission** — requester info, blood group needed,
  location, hospital, urgency level, units needed
- 🔍 **Eligibility-Aware Donor Search** — filters by blood group and city,
  automatically excluding donors who gave within the last 90 days
- 📋 **Donors Listing** — browsable table of every registered donor with
  live eligibility status
- 🏷️ **Blood Inventory Tracking** — standalone stock-by-blood-type tracker,
  deliberately not auto-updated by registration (registering ≠ blood
  actually being collected)
- 🔌 **JSON API** — `/api/search`, `/api/donors/<id>` for programmatic access

## Application Structure

```
blood-donation-webapp/
├── app/
│   ├── __init__.py       # Flask application factory, config, db.create_all()
│   ├── models.py         # SQLAlchemy models: Donor, BloodRequest, BloodInventory
│   ├── routes.py         # Blueprint: page routes + JSON API + search logic
│   └── validators.py     # Backend validation helpers (shared by all routes)
├── templates/
│   ├── base.html         # Shared layout, nav, footer
│   ├── index.html        # Home page
│   ├── register.html     # Donor registration form + result
│   ├── search.html       # Donor search form + results table
│   ├── request.html      # Blood request form + matched donors
│   ├── donors.html       # Registered donors listing
│   └── inventory.html    # Blood inventory tracker + update form
├── static/
│   └── style.css
├── tests/
│   ├── conftest.py
│   ├── test_registration.py
│   ├── test_search.py
│   └── test_donors_inventory.py
├── schema.sql             # Raw MySQL DDL equivalent to the SQLAlchemy models
├── requirements.txt
└── run.py
```

## How to Run

```bash
cd blood-donation-webapp
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Run with SQLite (default, zero config)
python run.py
```

Visit **http://localhost:5000**.

### Point it at MySQL instead

The exact same codebase runs against MySQL — only the connection string
changes, via the `DATABASE_URL` environment variable:

```bash
mysql -u your_user -p -e "CREATE DATABASE blood_donation CHARACTER SET utf8mb4;"
mysql -u your_user -p blood_donation < schema.sql

export DATABASE_URL="mysql+pymysql://your_user:your_password@localhost:3306/blood_donation"
export SECRET_KEY="change-me-in-production"
python run.py
```

### Run the tests

```bash
pytest -v
```

## How the Donor-Eligibility Search Works

The core logic lives in `app/routes.py::_find_eligible_donors()` and
`app/models.py::Donor.is_eligible()`: filter by exact blood-group match,
filter by case-insensitive city substring, then filter by eligibility
window — a donor is only surfaced if they've never donated before or at
least `DONATION_ELIGIBILITY_DAYS` (default **90 days**) have passed since
their last donation. This mirrors the real-world recovery-period guideline
between whole-blood donations, so the search never recommends someone who
matches on blood group/location but isn't actually eligible right now.

```python
def is_eligible(self, as_of=None, min_days_since_donation=90):
    if self.last_donation_date is None:
        return True
    as_of = as_of or date.today()
    days_since = (as_of - self.last_donation_date).days
    return days_since >= min_days_since_donation
```

The same function powers the search page, the request-match list, and the
`/api/search` JSON endpoint — one eligibility rule, applied consistently
everywhere.

## Results / Outcomes

- ✅ Built 6 server-rendered pages (Home, Register, Search, Request Blood,
  Donors, Inventory) plus a JSON API layer
- ✅ Implemented full backend validation — required fields, blood-group
  enum, email/phone format, duplicate-registration prevention
- ✅ Implemented real donor-eligibility logic (90-day rule) applied
  consistently across search, requests, and the API
- ✅ Runs on SQLite with zero setup, or MySQL by swapping one environment
  variable — no code changes needed
- ✅ **30/30 pytest tests passing**, covering validation, eligibility edge
  cases, and every route end-to-end

## Notes on Scope

This is a portfolio-scale project demonstrating core backend web
development skills (Flask app structure, SQLAlchemy modeling, validation,
search/filter logic) — it intentionally does not include authentication, an
admin dashboard, or production deployment concerns like rate limiting,
HTTPS termination, or containerization.

---

Developer: **Hasini Prasad** | [LinkedIn](https://linkedin.com/in/hasini-prasad-b761b0286)
