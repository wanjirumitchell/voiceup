-- VoiceUp v3 Schema Update
USE suggestion_system;

-- Login attempts tracking
CREATE TABLE IF NOT EXISTS login_attempts (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL,
    type       ENUM('user','admin') DEFAULT 'user',
    ip_address VARCHAR(50),
    attempted_at DATETIME DEFAULT NOW(),
    INDEX idx_identifier (identifier),
    INDEX idx_attempted_at (attempted_at)
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS password_resets (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    token      VARCHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used       TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    title       VARCHAR(255) NOT NULL,
    message     TEXT,
    link        VARCHAR(255),
    is_read     TINYINT DEFAULT 0,
    created_at  DATETIME DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_read (user_id, is_read)
);

-- Comments (threaded between user and admin on a suggestion)
CREATE TABLE IF NOT EXISTS comments (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id INT NOT NULL,
    user_id       INT NULL,
    admin_id      INT NULL,
    parent_id     INT NULL,
    body          TEXT NOT NULL,
    created_at    DATETIME DEFAULT NOW(),
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE SET NULL,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
);

-- System settings
CREATE TABLE IF NOT EXISTS system_settings (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_val TEXT,
    updated_at  DATETIME DEFAULT NOW()
);

-- Default settings
INSERT IGNORE INTO system_settings (setting_key, setting_val) VALUES
    ('site_name',          'VoiceUp'),
    ('announcement',       ''),
    ('announcement_active','0'),
    ('maintenance_mode',   '0'),
    ('sla_urgent',         '1'),
    ('sla_high',           '3'),
    ('sla_medium',         '7'),
    ('sla_low',            '14'),
    ('max_login_attempts', '5'),
    ('lockout_minutes',    '30'),
    ('categories',         'academics,facilities,welfare,technology,administration,sports,other');

-- Merge tracking
ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS merged_into INT NULL;
ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS is_merged TINYINT DEFAULT 0;

-- Ban users
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned TINYINT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_reason VARCHAR(255) NULL;

SELECT 'VoiceUp v3 schema update complete!' AS result;
