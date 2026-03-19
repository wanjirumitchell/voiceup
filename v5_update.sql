-- VoiceUp v5 Schema Update
USE suggestion_system;

-- Add student_id and profile fields to users
ALTER TABLE users ADD COLUMN student_id VARCHAR(50) NULL;
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NULL;
ALTER TABLE users ADD COLUMN profile_photo VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN department VARCHAR(100) NULL;
ALTER TABLE users ADD COLUMN bio TEXT NULL;

-- Suggestion templates
CREATE TABLE IF NOT EXISTS suggestion_templates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    category    VARCHAR(50) NOT NULL,
    priority    VARCHAR(20) DEFAULT 'medium',
    description TEXT NOT NULL,
    icon        VARCHAR(50) DEFAULT 'fa-lightbulb',
    is_active   TINYINT DEFAULT 1,
    use_count   INT DEFAULT 0,
    created_at  DATETIME DEFAULT NOW()
);

INSERT IGNORE INTO suggestion_templates (id, title, category, priority, description, icon) VALUES
(1,'Poor WiFi Connection','technology','high','The WiFi connection in [location] is very slow/unreliable. This affects students ability to access online learning resources. I suggest upgrading the network infrastructure.','fa-wifi'),
(2,'Library Hours Extension','facilities','medium','The library closes too early at [time]. Many students need access after this time, especially during exam periods. I suggest extending hours to [suggested time].','fa-book'),
(3,'Canteen Food Quality','welfare','medium','The food quality at the canteen needs improvement. Specifically, [describe issue]. Students health and academic performance are affected by poor nutrition.','fa-utensils'),
(4,'Classroom Maintenance','facilities','high','The classroom in [location] has maintenance issues: [describe issues]. This affects learning and could be a safety hazard.','fa-building'),
(5,'New Course Request','academics','medium','I suggest adding [course name] to the curriculum. This would benefit students by [reason]. Many institutions already offer this course.','fa-graduation-cap'),
(6,'Sports Equipment','sports','low','The sports department needs new [equipment type]. The current equipment is [condition]. This would improve physical education activities.','fa-football-ball');

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NULL,
    admin_id    INT NULL,
    action      VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id   INT NULL,
    details     TEXT,
    ip_address  VARCHAR(50),
    created_at  DATETIME DEFAULT NOW()
);

-- SMS log
CREATE TABLE IF NOT EXISTS sms_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    phone      VARCHAR(20) NOT NULL,
    message    TEXT NOT NULL,
    status     VARCHAR(20) DEFAULT 'sent',
    sent_at    DATETIME DEFAULT NOW()
);

SELECT 'VoiceUp v5 schema ready!' AS result;
