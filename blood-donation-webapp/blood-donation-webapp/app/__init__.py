"""
Application factory for the Blood Donation Web Application.

Uses SQLite by default (zero-config, great for local dev/testing) but
honors a DATABASE_URL environment variable so the exact same codebase
can run against MySQL in production. See README.md for the MySQL
connection string format.
"""
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config=None):
    # templates/ and static/ live at the project root (sibling to app/),
    # not inside the app package, per the project layout in README.md.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )

    default_db_path = os.path.join(app.instance_path, "blood_donation.db")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{default_db_path}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Minimum number of days that must pass since a donor's last
        # donation before they are considered eligible again.
        DONATION_ELIGIBILITY_DAYS=90,
    )

    if test_config is not None:
        app.config.update(test_config)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    db.init_app(app)

    from app import models  # noqa: F401  (register models with SQLAlchemy)
    from app.routes import main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        models.seed_blood_inventory()

    return app
