-- ============================================================
--  E-Waste College Management System — MySQL Schema
--  Database: ewaste_college_db
-- ============================================================

CREATE DATABASE IF NOT EXISTS ewaste_college_db;
USE ewaste_college_db;

-- ── USERS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id          INT           PRIMARY KEY AUTO_INCREMENT,
    name             VARCHAR(100)  NOT NULL,
    email            VARCHAR(100)  NOT NULL UNIQUE,
    phone            VARCHAR(15)   NOT NULL,
    department       VARCHAR(100),
    class_year       VARCHAR(50),
    roll_no          VARCHAR(50),
    college_location TEXT,
    password         VARCHAR(255)  NOT NULL,
    created_at       DATETIME      DEFAULT CURRENT_TIMESTAMP
);

-- ── ADMIN ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin (
    admin_id   INT          PRIMARY KEY AUTO_INCREMENT,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL
);

-- Default admin (password: admin123 — hashed with werkzeug pbkdf2:sha256)
INSERT INTO admin (username, password)
VALUES ('admin', 'scrypt:32768:8:1$FBn0Wp70GTgjamWr$ac09a6b1e70ddc84c6d5b8fefc8125bdbcce398741d85ce39264ef7612a4803fce2bb64cbc87ecb9d7e5e7dbf6bc071110362c89ee6e69b28adc303a1b0b460f')
ON DUPLICATE KEY UPDATE username=username;

-- ── E-WASTE ITEMS ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ewaste_items (
    waste_id        INT             PRIMARY KEY AUTO_INCREMENT,
    user_id         INT             NOT NULL,
    item_name       VARCHAR(100)    NOT NULL,
    category        VARCHAR(100)    NOT NULL,
    quantity        INT             NOT NULL DEFAULT 1,
    waste_condition VARCHAR(100),
    approx_weight   DECIMAL(8,2),
    description     TEXT,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ── PICKUP REQUESTS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pickup_requests (
    request_id       INT          PRIMARY KEY AUTO_INCREMENT,
    user_id          INT          NOT NULL,
    waste_id         INT          NOT NULL,
    pickup_location  TEXT         NOT NULL,
    pickup_date      DATE         NOT NULL,
    time_slot        VARCHAR(50),
    note             TEXT,
    status           VARCHAR(50)  NOT NULL DEFAULT 'Pending',
    collector_name   VARCHAR(100),
    collector_phone  VARCHAR(15),
    assigned_at      DATETIME     NULL,
    completed_at     DATETIME     NULL,
    cancelled_at     DATETIME     NULL,
    created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (waste_id) REFERENCES ewaste_items(waste_id) ON DELETE CASCADE
);

-- ── RECYCLING RECORDS ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS recycling_records (
    recycle_id        INT          PRIMARY KEY AUTO_INCREMENT,
    request_id        INT          NOT NULL,
    recycling_center  VARCHAR(150),
    sent_date         DATE,
    recycled_date     DATE,
    recycle_status    VARCHAR(100),
    remarks           TEXT,
    FOREIGN KEY (request_id) REFERENCES pickup_requests(request_id) ON DELETE CASCADE
);
select*from pickup_requests ;

