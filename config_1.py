import os

# ═══════════════════════════════════════════════════════════════════
# VoiceUp Configuration File
# ═══════════════════════════════════════════════════════════════════
# ⚠️  This file contains secrets — NEVER push to GitHub!
# ⚠️  It is listed in .gitignore for your protection.
# ═══════════════════════════════════════════════════════════════════

# ─── App ─────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'v0iceUp-2026-KE-s3cur3-r@nd0m-k3y-m1tch3ll-xyz!')
DEBUG      = False
PORT       = 8080

# ─── Database ────────────────────────────────────────────────────
MYSQL_HOST     = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_USER     = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root1234')
MYSQL_DB       = os.environ.get('MYSQL_DB', 'suggestion_system')
MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3305))

# ─── AI (Gemini) ─────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')  # Add your key here
GEMINI_MODEL   = 'gemini-2.0-flash'

# ─── Groq (optional - faster chatbot) ───────────────────────────
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL   = 'llama-3.3-70b-versatile'

# ─── Email (Gmail) ───────────────────────────────────────────────
EMAIL_ENABLED  = False        # Set to True to enable emails
EMAIL_HOST     = 'smtp.gmail.com'
EMAIL_PORT     = 465
EMAIL_USER     = ''           # your Gmail e.g. voiceup33@gmail.com
EMAIL_PASSWORD = ''           # your 16-char Gmail App Password
EMAIL_FROM     = 'VoiceUp <noreply@voiceup.com>'

# ─── File Uploads ────────────────────────────────────────────────
UPLOAD_FOLDER      = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
MAX_FILE_SIZE      = 5 * 1024 * 1024  # 5MB

# ─── SLA Days by Priority ────────────────────────────────────────
SLA_DAYS = {
    'urgent': 1,
    'high':   3,
    'medium': 7,
    'low':    14
}

# ─── Security Settings ───────────────────────────────────────────
SESSION_COOKIE_HTTPONLY  = True
SESSION_COOKIE_SAMESITE  = 'Lax'
SESSION_LIFETIME_HOURS   = 24
MAX_LOGIN_ATTEMPTS       = 5
LOCKOUT_MINUTES          = 30
