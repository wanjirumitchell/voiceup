-- ─── SUGGESTION TIMELINE TABLE ───────────────────────────────────────────────
-- Run this SQL in your MySQL database (via phpMyAdmin or MySQL Workbench)

CREATE TABLE IF NOT EXISTS suggestion_timeline (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id INT NOT NULL,
    event_type   VARCHAR(50) NOT NULL,  -- submitted, status_changed, response_added, comment_added, assigned, merged
    old_value    VARCHAR(100) DEFAULT NULL,
    new_value    VARCHAR(100) DEFAULT NULL,
    actor_name   VARCHAR(100) DEFAULT 'System',
    actor_type   ENUM('user','admin','system') DEFAULT 'system',
    note         TEXT DEFAULT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id) ON DELETE CASCADE
);

-- Index for fast lookup
CREATE INDEX idx_timeline_suggestion ON suggestion_timeline(suggestion_id);
