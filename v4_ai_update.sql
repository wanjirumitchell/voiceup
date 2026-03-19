-- VoiceUp v4 AI Features Schema Update
USE suggestion_system;

-- AI analysis results stored per suggestion
CREATE TABLE IF NOT EXISTS ai_analysis (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id INT NOT NULL UNIQUE,
    sentiment     VARCHAR(20) DEFAULT 'neutral',
    sentiment_score DECIMAL(3,2) DEFAULT 0.50,
    auto_category VARCHAR(50),
    auto_priority VARCHAR(20),
    summary       TEXT,
    keywords      TEXT,
    analyzed_at   DATETIME DEFAULT NOW(),
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id) ON DELETE CASCADE
);

-- AI draft responses
CREATE TABLE IF NOT EXISTS ai_drafts (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id INT NOT NULL,
    draft_text    TEXT NOT NULL,
    used          TINYINT DEFAULT 0,
    created_at    DATETIME DEFAULT NOW(),
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id) ON DELETE CASCADE
);

-- AI trend reports
CREATE TABLE IF NOT EXISTS ai_reports (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    report_type VARCHAR(50) DEFAULT 'weekly',
    content    TEXT,
    generated_at DATETIME DEFAULT NOW()
);

-- Chatbot conversations
CREATE TABLE IF NOT EXISTS chatbot_sessions (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT,
    session_key VARCHAR(64) NOT NULL,
    messages   LONGTEXT,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Add AI fields to suggestions
ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS ai_sentiment VARCHAR(20) DEFAULT NULL;
ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS ai_summary TEXT DEFAULT NULL;

SELECT 'VoiceUp v4 AI schema ready!' AS result;
