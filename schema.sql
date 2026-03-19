-- ============================================================
-- Suggestion System Database Schema
-- ============================================================
CREATE DATABASE IF NOT EXISTS suggestion_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE suggestion_system;

-- ─── Users ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    fullname   VARCHAR(100)  NOT NULL,
    email      VARCHAR(150)  NOT NULL UNIQUE,
    password   VARCHAR(255)  NOT NULL,
    role       ENUM('student','teacher','staff') DEFAULT 'student',
    created_at DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME      ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
) ENGINE=InnoDB;

-- ─── Admins ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admins (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(80)   NOT NULL UNIQUE,
    email      VARCHAR(150)  NOT NULL UNIQUE,
    password   VARCHAR(255)  NOT NULL,
    role       ENUM('super_admin','admin','moderator') DEFAULT 'admin',
    is_active  TINYINT(1)    DEFAULT 1,
    last_login DATETIME,
    created_at DATETIME      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Suggestions ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suggestions (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id VARCHAR(20)  NOT NULL UNIQUE,
    user_id       INT          NOT NULL,
    title         VARCHAR(200) NOT NULL,
    category      ENUM('academic','facilities','administration','technology',
                       'safety','extracurricular','cafeteria','other') NOT NULL,
    description   TEXT         NOT NULL,
    priority      ENUM('low','medium','high','urgent') DEFAULT 'medium',
    status        ENUM('pending','under_review','in_progress','resolved','rejected') DEFAULT 'pending',
    is_anonymous  TINYINT(1)   DEFAULT 0,
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_status   (status),
    INDEX idx_category (category),
    INDEX idx_user     (user_id),
    INDEX idx_sid      (suggestion_id)
) ENGINE=InnoDB;

-- ─── Admin Responses ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_responses (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id INT          NOT NULL,
    admin_id      INT          NOT NULL,
    response_text TEXT         NOT NULL,
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id)      REFERENCES admins(id)
) ENGINE=InnoDB;

-- ─── Seed default admin ─────────────────────────────────────
-- Password: Admin@1234  (SHA-256)
INSERT IGNORE INTO admins (username, email, password, role) VALUES
('admin', 'admin@school.edu',
 '3db7a10c76b4f31862c50bb6b3e1fefacca64f95dc84e5ecf62a4e218d3a9b54',
 'super_admin'),
('moderator', 'mod@school.edu',
 '3db7a10c76b4f31862c50bb6b3e1fefacca64f95dc84e5ecf62a4e218d3a9b54',
 'moderator');

-- NOTE: SHA256 of "Admin@1234" = 3db7a10c76b4f31862c50bb6b3e1fefacca64f95dc84e5ecf62a4e218d3a9b54
-- Verify with: python3 -c "import hashlib; print(hashlib.sha256('Admin@1234'.encode()).hexdigest())"
