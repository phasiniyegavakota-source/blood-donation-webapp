-- ============================================================
-- schema.sql
--
-- Raw MySQL DDL equivalent to the SQLAlchemy models in app/models.py.
-- The application itself creates tables automatically via
-- db.create_all() (SQLite or MySQL), so running this file by hand is
-- optional -- it's included to show the underlying relational design
-- and for anyone who wants to provision the MySQL schema manually,
-- e.g. via a migration tool or DBA review.
--
-- Usage:
--   mysql -u your_user -p your_database < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS blood_donation
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE blood_donation;

-- ------------------------------------------------------------
-- donors
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS donors (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    blood_group         ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    email               VARCHAR(120) NOT NULL,
    phone               VARCHAR(20)  NOT NULL,
    city                VARCHAR(100) NOT NULL,
    last_donation_date  DATE NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_donors_email UNIQUE (email),
    CONSTRAINT uq_donors_phone UNIQUE (phone),
    INDEX idx_donors_blood_group (blood_group),
    INDEX idx_donors_city (city)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- blood_requests
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blood_requests (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    requester_name  VARCHAR(100) NOT NULL,
    contact_email   VARCHAR(120) NOT NULL,
    contact_phone   VARCHAR(20)  NOT NULL,
    blood_group     ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    city            VARCHAR(100) NOT NULL,
    hospital        VARCHAR(150) NULL,
    units_needed    INT NOT NULL DEFAULT 1,
    urgency         ENUM('Low', 'Medium', 'High', 'Critical') NOT NULL DEFAULT 'Medium',
    notes           TEXT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_requests_blood_group (blood_group),
    INDEX idx_requests_city (city)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- blood_inventory
--
-- A simple stock-by-blood-type tracker: one row per blood group with
-- the number of units currently on hand. It is intentionally NOT
-- touched by donor registration -- a donor signing up is not the
-- same event as blood actually being collected, so stock is only
-- ever changed explicitly (see app/routes.py::inventory_adjust()).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blood_inventory (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    blood_group       ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    units_available   INT NOT NULL DEFAULT 0,
    last_updated      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT uq_blood_inventory_blood_group UNIQUE (blood_group)
) ENGINE=InnoDB;

-- Seed one row per standard blood group at 0 units. The application
-- also performs this seed automatically on first startup (see
-- app/models.py::seed_blood_inventory()), so this INSERT is only
-- needed when provisioning the schema by hand.
INSERT INTO blood_inventory (blood_group, units_available) VALUES
    ('A+', 0), ('A-', 0), ('B+', 0), ('B-', 0),
    ('AB+', 0), ('AB-', 0), ('O+', 0), ('O-', 0)
ON DUPLICATE KEY UPDATE blood_group = blood_group;

-- ------------------------------------------------------------
-- Example eligibility query used by the search feature:
-- eligible donors of a given blood group / city who have NOT
-- donated in the last 90 days (or have never donated).
-- ------------------------------------------------------------
-- SELECT *
-- FROM donors
-- WHERE blood_group = 'O+'
--   AND city LIKE '%Springfield%'
--   AND (last_donation_date IS NULL
--        OR last_donation_date <= DATE_SUB(CURDATE(), INTERVAL 90 DAY))
-- ORDER BY name ASC;
