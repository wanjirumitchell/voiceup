-- VoiceUp v6 Schema Update
USE suggestion_system;

-- Departments table
CREATE TABLE IF NOT EXISTS departments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    head_admin  INT NULL,
    email       VARCHAR(255) NULL,
    is_active   TINYINT DEFAULT 1,
    color       VARCHAR(20) DEFAULT '#6366f1',
    icon        VARCHAR(50) DEFAULT 'fa-building',
    created_at  DATETIME DEFAULT NOW(),
    FOREIGN KEY (head_admin) REFERENCES admins(id) ON DELETE SET NULL
);

-- Add department to suggestions
ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS department_id INT NULL;
ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS department_id INT NULL REFERENCES departments(id);

-- Add department to categories mapping
CREATE TABLE IF NOT EXISTS category_departments (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    category      VARCHAR(50) NOT NULL,
    department_id INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
);

-- Default departments
INSERT IGNORE INTO departments (id, name, description, color, icon) VALUES
(1, 'Academic Affairs', 'Handles all academic related suggestions', '#6366f1', 'fa-graduation-cap'),
(2, 'Facilities & Maintenance', 'Handles building and facility issues', '#f59e0b', 'fa-tools'),
(3, 'Student Welfare', 'Handles student wellbeing and welfare', '#10b981', 'fa-heart'),
(4, 'ICT Department', 'Handles technology and IT issues', '#3b82f6', 'fa-laptop'),
(5, 'Administration', 'General administrative matters', '#8b5cf6', 'fa-briefcase'),
(6, 'Sports & Recreation', 'Handles sports and recreational activities', '#ef4444', 'fa-football-ball');

-- Map categories to departments
INSERT IGNORE INTO category_departments (category, department_id) VALUES
('academics', 1),
('facilities', 2),
('welfare', 3),
('technology', 4),
('administration', 5),
('sports', 6),
('other', 5);

-- Email settings
INSERT IGNORE INTO system_settings (setting_key, setting_val) VALUES
('email_enabled', '0'),
('email_host', 'smtp.gmail.com'),
('email_port', '587'),
('email_user', ''),
('email_password', ''),
('email_from_name', 'VoiceUp System');

SELECT 'VoiceUp v6 schema ready!' AS result;
