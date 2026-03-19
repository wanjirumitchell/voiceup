-- VoiceUp Super Admin Schema Update
-- Run this in MySQL to add super admin support

USE suggestion_system;

-- Update role column to include super_admin
ALTER TABLE admins MODIFY COLUMN role ENUM('super_admin','admin','moderator') DEFAULT 'admin';

-- Add created_at to admins if not exists
ALTER TABLE admins ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT NOW();

-- Promote the default admin to super_admin
UPDATE admins SET role='super_admin' WHERE username='admin';

SELECT username, role, is_active FROM admins;
SELECT 'Super admin setup complete!' AS result;
