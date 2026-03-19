# VoiceUp — School Suggestion System
## Full-Stack: Flask + MySQL + HTML/CSS/JS

---

## 🚀 Quick Setup

### 1. Requirements
- Python 3.8+
- MySQL 8.0+
- pip

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup
```bash
# Log into MySQL
mysql -u root -p

# Run schema
source schema.sql
```

### 4. Configure Environment (optional)
```bash
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DB=suggestion_system
export SECRET_KEY=your-secret-key-here
```

### 5. Run the App
```bash
python app.py
```
Visit: http://localhost:5000

---

## 👤 Default Credentials

### Admin Login
- **URL:** `/admin/login`
- **Username:** `admin`
- **Password:** `Admin@1234`

### User Registration
- Visit `/register` to create a user account

---

## 📁 Project Structure

```
suggestion_system/
├── app.py                          # Flask application
├── schema.sql                      # Database schema + seed data
├── requirements.txt
├── static/
│   ├── css/style.css               # Full design system
│   └── js/main.js                  # Interactions & validation
└── templates/
    ├── base.html                   # Base layout with nav
    ├── index.html                  # Landing page
    ├── login.html                  # User login
    ├── register.html               # User registration
    ├── dashboard.html              # User dashboard
    ├── submit_suggestion.html      # Suggestion form
    ├── my_suggestions.html         # Suggestion list + filters
    ├── suggestion_detail.html      # Detail + status timeline
    ├── track.html                  # Public tracking page
    └── admin/
        ├── login.html              # Admin login
        ├── dashboard.html          # Admin dashboard + table
        └── suggestion_detail.html  # Admin review + respond
```

---

## 🔑 Features

### User Side
- Register/Login with role (Student / Teacher / Staff)
- Submit suggestions with title, category, description, priority
- Toggle anonymous submission
- Unique tracking ID per suggestion (SGT-XXXXXXXX)
- View all submissions with status filters
- Detailed view with admin response timeline
- Public tracking by ID (no login required)

### Admin Side
- Secure admin login (separate from users)
- Dashboard with total/pending/review/resolved stats
- Search + filter by status, category, priority
- Review individual suggestions
- Update status (Pending → Under Review → In Progress → Resolved/Rejected)
- Add written responses visible to submitter
- Category breakdown chart

### Security
- Passwords hashed with SHA-256
- Session-based auth (separate for users/admins)
- Anonymous submissions truly unlinked from admin view
- SQL parameterized queries (no injection)
- Login required decorators on all protected routes
- CSRF-ready structure (add flask-wtf for production)

---

## 🗃️ Database Schema

```
users           - id, fullname, email, password, role, created_at
admins          - id, username, email, password, role, is_active, last_login
suggestions     - id, suggestion_id, user_id, title, category, description,
                  priority, status, is_anonymous, created_at, updated_at
admin_responses - id, suggestion_id, admin_id, response_text, created_at
```

---

## 🔒 For Production
1. Use `flask-wtf` for CSRF tokens
2. Use `bcrypt` instead of SHA-256 for passwords
3. Set `SESSION_COOKIE_SECURE=True` and `SESSION_COOKIE_HTTPONLY=True`
4. Store `SECRET_KEY` in environment variable
5. Use HTTPS (SSL/TLS)
6. Use a production WSGI server (Gunicorn/uWSGI)
