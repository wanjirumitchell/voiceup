import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib, os, re, string, random, csv, io, smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ─── Configuration ─────────────────────────────────────────────────────────────
app.secret_key = os.environ.get('SECRET_KEY', 'voiceup-secret-key-v2')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL   = 'gemini-2.5-flash'

app.config['MYSQL_HOST']        = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER']        = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD']    = os.environ.get('MYSQL_PASSWORD', 'root1234')
app.config['MYSQL_DB']          = os.environ.get('MYSQL_DB', 'suggestion_system')
app.config['MYSQL_PORT']        = 3305
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# File upload config
UPLOAD_FOLDER   = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
MAX_FILE_SIZE   = 5 * 1024 * 1024  # 5MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── Email config — fill in to enable email notifications ──────────────────────
EMAIL_ENABLED   = False          # Set to True after adding credentials below
EMAIL_HOST      = 'smtp.gmail.com'
EMAIL_PORT      = 465
EMAIL_USER      = ''             # Your Gmail address e.g. yourname@gmail.com
EMAIL_PASSWORD  = ''             # Your Gmail App Password (16 chars, no spaces)
EMAIL_FROM      = 'VoiceUp <noreply@voiceup.com>'

mysql = MySQL(app)
app.jinja_env.globals.update(enumerate=enumerate)
app.jinja_env.globals.update(enumerate=enumerate)

# ─── SLA Intervals ─────────────────────────────────────────────────────────────
SLA_DAYS = {'urgent': 1, 'high': 3, 'medium': 7, 'low': 14}

# ─── Helpers ────────────────────────────────────────────────────────────────────
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def generate_suggestion_id():
    chars = string.ascii_uppercase + string.digits
    return 'SGT-' + ''.join(random.choices(chars, k=8))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_sla_status(due_date):
    if not due_date: return 'on_track'
    now = datetime.now()
    if isinstance(due_date, str):
        due_date = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
    diff = (due_date - now).total_seconds() / 3600
    if diff < 0:     return 'overdue'
    if diff < 24:    return 'at_risk'
    return 'on_track'

def build_email(title, message, suggestion_title='', tracking_id='', status='', cta_text='View Suggestion', cta_url=''):
    """Build a beautiful HTML email."""
    status_colors = {
        'under_review': '#3b82f6',
        'resolved':     '#10b981',
        'rejected':     '#ef4444',
        'pending':      '#f59e0b',
    }
    status_icons = {
        'under_review': '🔍',
        'resolved':     '✅',
        'rejected':     '❌',
        'pending':      '⏳',
    }
    color  = status_colors.get(status, '#6366f1')
    icon   = status_icons.get(status, '📬')
    cta_btn = f'<a href="{cta_url}" style="display:inline-block;background:{color};color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;margin-top:8px;">{cta_text}</a>' if cta_url else ''
    suggestion_block = f'''
        <div style="background:#f1f5f9;border-left:4px solid {color};padding:14px 18px;border-radius:8px;margin:20px 0;">
            <div style="font-size:12px;color:#64748b;margin-bottom:4px;">SUGGESTION</div>
            <div style="font-weight:600;color:#1e293b;font-size:15px;">{suggestion_title}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px;">Tracking ID: {tracking_id}</div>
        </div>''' if suggestion_title else ''

    return f'''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:16px 16px 0 0;padding:32px;text-align:center;">
          <div style="font-size:36px;margin-bottom:8px;">{icon}</div>
          <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;">{title}</h1>
        </td></tr>

        <!-- Body -->
        <tr><td style="background:#ffffff;padding:32px;border-radius:0 0 16px 16px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <p style="color:#475569;font-size:15px;line-height:1.7;margin-top:0;">{message}</p>
          {suggestion_block}
          {cta_btn}
          <hr style="border:none;border-top:1px solid #e2e8f0;margin:28px 0;">
          <p style="color:#94a3b8;font-size:12px;margin:0;">
            This email was sent by <strong style="color:#6366f1;">VoiceUp</strong> — School Suggestion System.<br>
            If you did not expect this email, please ignore it.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="text-align:center;padding:20px;">
          <p style="color:#94a3b8;font-size:12px;margin:0;">© 2026 VoiceUp. All rights reserved.</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>'''

def send_notification(to_email, subject, body, suggestion_title='', tracking_id='', status=''):
    """Send a beautiful HTML email notification."""
    if not EMAIL_ENABLED or not to_email: return
    try:
        html = build_email(
            title=subject,
            message=body,
            suggestion_title=suggestion_title,
            tracking_id=tracking_id,
            status=status
        )
        import smtplib
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'VoiceUp — {subject}'
        msg['From']    = EMAIL_FROM
        msg['To']      = to_email
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as s:
            s.login(EMAIL_USER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_USER, [to_email], msg.as_string())
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO email_log (to_email, subject) VALUES (%s,%s)", (to_email, subject))
        mysql.connection.commit()
        print(f'✅ Email sent to {to_email}')
    except Exception as e:
        print(f'❌ Email error: {e}')

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def get_stats():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM suggestions")
    total = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions WHERE status='pending'")
    pending = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions WHERE status='under_review'")
    under_review = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions WHERE status='resolved'")
    resolved = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions WHERE status='rejected'")
    rejected = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions WHERE sla_status='overdue'")
    overdue = cursor.fetchone()['cnt']
    return {'total': total, 'pending': pending, 'under_review': under_review,
            'resolved': resolved, 'rejected': rejected, 'overdue': overdue}

def log_timeline(suggestion_id, event_type, new_value=None, old_value=None,
                 actor_name='System', actor_type='system', note=None):
    """Log an event to the suggestion timeline."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO suggestion_timeline
            (suggestion_id, event_type, old_value, new_value, actor_name, actor_type, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (suggestion_id, event_type, old_value, new_value, actor_name, actor_type, note))
        mysql.connection.commit()
    except Exception as e:
        print(f'Timeline log error: {e}')

# ─── Home ────────────────────────────────────────────────────────────────────────
@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/')
def index():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions WHERE status='resolved'")
    resolved = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    users = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions")
    total = cursor.fetchone()['cnt']
    return render_template('index.html', resolved=resolved, users=users, total=total)

# ─── Public Board ───────────────────────────────────────────────────────────────
@app.route('/public')
def public_board():
    page     = int(request.args.get('page', 1))
    category = request.args.get('category', 'all')
    sort     = request.args.get('sort', 'votes')
    per_page = 9

    cursor = mysql.connection.cursor()
    base = """
        FROM suggestions s
        JOIN users u ON s.user_id = u.id
        WHERE s.is_anonymous = 0
    """
    params = []
    if category != 'all':
        base += " AND s.category = %s"
        params.append(category)

    order = "s.vote_count DESC, s.created_at DESC" if sort == 'votes' else "s.created_at DESC"
    cursor.execute("SELECT COUNT(*) as cnt " + base, params)
    total = cursor.fetchone()['cnt']
    offset = (page - 1) * per_page
    cursor.execute(
        "SELECT s.*, u.fullname, u.role as user_role " + base +
        f" ORDER BY {order} LIMIT %s OFFSET %s",
        params + [per_page, offset]
    )
    suggestions = cursor.fetchall()

    user_votes = set()
    if 'user_id' in session:
        cursor.execute("SELECT suggestion_id FROM votes WHERE user_id=%s", (session['user_id'],))
        user_votes = {r['suggestion_id'] for r in cursor.fetchall()}

    return render_template('public_board.html',
                           suggestions=suggestions, category=category,
                           sort=sort, page=page,
                           total_pages=(total + per_page - 1) // per_page,
                           user_votes=user_votes)

# ─── USER AUTH ──────────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname','').strip()
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        confirm  = request.form.get('confirm_password','')
        role     = request.form.get('role','student')
        errors   = []
        if not fullname: errors.append('Full name is required.')
        if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            errors.append('Valid email is required.')
        if len(password) < 8: errors.append('Password must be at least 8 characters.')
        if password != confirm: errors.append('Passwords do not match.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('register.html', fullname=fullname, email=email, role=role)
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash('An account with that email already exists.', 'danger')
            return render_template('register.html')
        cursor.execute(
            "INSERT INTO users (fullname,email,password,role,created_at) VALUES (%s,%s,%s,%s,NOW())",
            (fullname, email, hash_password(password), role)
        )
        mysql.connection.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('user_login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        if check_login_locked(email, 'user'):
            settings = get_all_settings()
            mins = settings.get('lockout_minutes', '30')
            flash(f'Too many failed attempts. Account locked for {mins} minutes.', 'danger')
            return render_template('login.html')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s",
                       (email, hash_password(password)))
        user = cursor.fetchone()
        if user:
            clear_login_attempts(email, 'user')
            session.update({'user_id': user['id'], 'user_name': user['fullname'],
                            'user_role': user['role'], 'user_email': user['email']})
            flash(f'Welcome back, {user["fullname"]}!', 'success')
            return redirect(url_for('dashboard'))
        record_login_attempt(email, 'user')
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    for k in ['user_id','user_name','user_role','user_email']: session.pop(k, None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ─── USER DASHBOARD ─────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.*, COUNT(ar.id) as response_count
        FROM suggestions s
        LEFT JOIN admin_responses ar ON s.id = ar.suggestion_id
        WHERE s.user_id=%s GROUP BY s.id ORDER BY s.created_at DESC LIMIT 5
    """, (session['user_id'],))
    recent = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*) as total, SUM(status='pending') as pending,
               SUM(status='under_review') as under_review, SUM(status='resolved') as resolved
        FROM suggestions WHERE user_id=%s
    """, (session['user_id'],))
    stats = cursor.fetchone()
    # Monthly chart data for current year
    cursor.execute("""
        SELECT MONTH(created_at) as month, COUNT(*) as cnt
        FROM suggestions WHERE user_id=%s AND YEAR(created_at)=YEAR(NOW())
        GROUP BY MONTH(created_at) ORDER BY month
    """, (session['user_id'],))
    monthly_raw = cursor.fetchall()
    monthly = [0]*12
    for r in monthly_raw: monthly[r['month']-1] = r['cnt']
    return render_template('dashboard.html', recent=recent, stats=stats, monthly=monthly)

# ─── SUBMIT SUGGESTION ──────────────────────────────────────────────────────────
@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_suggestion():
    if request.method == 'POST':
        title       = request.form.get('title','').strip()
        category    = request.form.get('category','')
        description = request.form.get('description','').strip()
        priority    = request.form.get('priority','medium')
        anonymous   = request.form.get('anonymous') == 'on'
        errors = []
        if not title or len(title) < 5:         errors.append('Title must be at least 5 characters.')
        if not category:                         errors.append('Please select a category.')
        if not description or len(description) < 20: errors.append('Description must be at least 20 characters.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('submit_suggestion.html', title=title, category=category,
                                   description=description, priority=priority)

        suggestion_id = generate_suggestion_id()
        cursor = mysql.connection.cursor()
        while True:
            cursor.execute("SELECT id FROM suggestions WHERE suggestion_id=%s", (suggestion_id,))
            if not cursor.fetchone(): break
            suggestion_id = generate_suggestion_id()

        days = SLA_DAYS.get(priority, 7)
        due_date = datetime.now() + timedelta(days=days)

        cursor.execute("""
            INSERT INTO suggestions
            (suggestion_id,user_id,title,category,description,priority,is_anonymous,status,due_date,sla_status,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'pending',%s,'on_track',NOW())
        """, (suggestion_id, session['user_id'], title, category, description, priority, anonymous, due_date))
        mysql.connection.commit()
        new_id = cursor.lastrowid
        log_timeline(new_id, 'submitted', new_value='pending',
                     actor_name=session['user_name'], actor_type='user')

        # Handle file uploads
        files = request.files.getlist('attachments')
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                original = f.filename
                safe     = secure_filename(f.filename)
                unique   = f"{new_id}_{int(datetime.now().timestamp())}_{safe}"
                path     = os.path.join(app.config['UPLOAD_FOLDER'], unique)
                f.save(path)
                size = os.path.getsize(path)
                cursor.execute(
                    "INSERT INTO attachments (suggestion_id,filename,original_name,file_size) VALUES (%s,%s,%s,%s)",
                    (new_id, unique, original, size)
                )
        mysql.connection.commit()
        # Trigger AI analysis in background
        try:
            ai_analyze_suggestion(new_id, title, description, category)
        except Exception as e:
            print(f'AI analysis error: {e}')

        flash(f'Suggestion submitted! Tracking ID: <strong>{new_id}</strong>', 'success')
        return redirect(url_for('my_suggestions'))
    return render_template('submit_suggestion.html')

# ─── VOTE ───────────────────────────────────────────────────────────────────────
@app.route('/vote/<int:sid>', methods=['POST'])
@login_required
def vote(sid):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM votes WHERE suggestion_id=%s AND user_id=%s",
                   (sid, session['user_id']))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("DELETE FROM votes WHERE suggestion_id=%s AND user_id=%s",
                       (sid, session['user_id']))
        cursor.execute("UPDATE suggestions SET vote_count=GREATEST(vote_count-1,0) WHERE id=%s", (sid,))
        voted = False
    else:
        cursor.execute("INSERT INTO votes (suggestion_id,user_id) VALUES (%s,%s)",
                       (sid, session['user_id']))
        cursor.execute("UPDATE suggestions SET vote_count=vote_count+1 WHERE id=%s", (sid,))
        voted = True
    mysql.connection.commit()
    cursor.execute("SELECT vote_count FROM suggestions WHERE id=%s", (sid,))
    count = cursor.fetchone()['vote_count']
    return jsonify({'voted': voted, 'count': count})

# ─── MY SUGGESTIONS ─────────────────────────────────────────────────────────────
@app.route('/my-suggestions')
@login_required
def my_suggestions():
    status_filter   = request.args.get('status','all')
    category_filter = request.args.get('category','all')
    page     = int(request.args.get('page',1))
    per_page = 6
    cursor   = mysql.connection.cursor()
    base     = """
        FROM suggestions s
        LEFT JOIN (SELECT suggestion_id, COUNT(*) as cnt FROM admin_responses GROUP BY suggestion_id) ar
            ON s.id = ar.suggestion_id
        WHERE s.user_id=%s
    """
    params = [session['user_id']]
    if status_filter   != 'all': base += " AND s.status=%s";   params.append(status_filter)
    if category_filter != 'all': base += " AND s.category=%s"; params.append(category_filter)
    cursor.execute("SELECT COUNT(*) as cnt " + base, params)
    total   = cursor.fetchone()['cnt']
    offset  = (page-1)*per_page
    cursor.execute("SELECT s.*, COALESCE(ar.cnt,0) as response_count " + base +
                   " ORDER BY s.created_at DESC LIMIT %s OFFSET %s", params+[per_page, offset])
    suggestions = cursor.fetchall()
    return render_template('my_suggestions.html', suggestions=suggestions,
                           status_filter=status_filter, category_filter=category_filter,
                           page=page, total_pages=(total+per_page-1)//per_page, total=total)

# ─── SUGGESTION DETAIL ──────────────────────────────────────────────────────────
@app.route('/suggestion/<suggestion_id>')
@login_required
def suggestion_detail(suggestion_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.*, u.fullname as submitter_name, u.role as submitter_role
        FROM suggestions s JOIN users u ON s.user_id=u.id
        WHERE s.suggestion_id=%s AND s.user_id=%s
    """, (suggestion_id, session['user_id']))
    suggestion = cursor.fetchone()
    if not suggestion:
        flash('Suggestion not found.', 'danger')
        return redirect(url_for('my_suggestions'))
    cursor.execute("""
        SELECT ar.*, a.username as admin_name FROM admin_responses ar
        JOIN admins a ON ar.admin_id=a.id WHERE ar.suggestion_id=%s ORDER BY ar.created_at ASC
    """, (suggestion['id'],))
    responses = cursor.fetchall()
    cursor.execute("SELECT * FROM attachments WHERE suggestion_id=%s", (suggestion['id'],))
    attachments = cursor.fetchall()
    cursor.execute("SELECT * FROM satisfaction_ratings WHERE suggestion_id=%s AND user_id=%s",
                   (suggestion['id'], session['user_id']))
    rating = cursor.fetchone()
    cursor.execute("SELECT * FROM votes WHERE suggestion_id=%s AND user_id=%s",
                   (suggestion['id'], session['user_id']))
    user_voted = bool(cursor.fetchone())
    cursor.execute("""
        SELECT c.*,
               COALESCE(u.fullname, a.username, 'Unknown') as author
        FROM comments c
        LEFT JOIN users u ON c.user_id = u.id
        LEFT JOIN admins a ON c.admin_id = a.id
        WHERE c.suggestion_id=%s
        ORDER BY c.created_at ASC
    """, (suggestion['id'],))
    comments = cursor.fetchall()
    suggestion['comments'] = comments
    cursor.execute("""
        SELECT * FROM suggestion_timeline
        WHERE suggestion_id=%s ORDER BY created_at ASC
    """, (suggestion['id'],))
    timeline = cursor.fetchall()
    return render_template('suggestion_detail.html', suggestion=suggestion,
                           responses=responses, attachments=attachments,
                           rating=rating, user_voted=user_voted,
                           timeline=timeline)

# ─── SATISFACTION RATING ────────────────────────────────────────────────────────
@app.route('/suggestion/<int:sid>/rate', methods=['POST'])
@login_required
def rate_suggestion(sid):
    rating  = int(request.form.get('rating', 0))
    comment = request.form.get('comment','').strip()
    if not 1 <= rating <= 5:
        flash('Please select a rating between 1 and 5.', 'danger')
        return redirect(request.referrer)
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM suggestions WHERE id=%s AND user_id=%s AND status='resolved'",
                   (sid, session['user_id']))
    if not cursor.fetchone():
        flash('You can only rate resolved suggestions.', 'danger')
        return redirect(request.referrer)
    cursor.execute("""
        INSERT INTO satisfaction_ratings (suggestion_id,user_id,rating,comment)
        VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE rating=%s, comment=%s
    """, (sid, session['user_id'], rating, comment, rating, comment))
    mysql.connection.commit()
    flash('Thank you for your feedback!', 'success')
    return redirect(request.referrer)

# ─── TRACK ──────────────────────────────────────────────────────────────────────
@app.route('/track', methods=['GET', 'POST'])
def track_suggestion():
    suggestion, responses = None, []
    if request.method == 'POST':
        track_id = request.form.get('track_id','').strip().upper()
        cursor   = mysql.connection.cursor()
        cursor.execute("""
            SELECT s.suggestion_id,s.title,s.category,s.status,s.priority,
                   s.created_at,s.updated_at,s.is_anonymous,s.vote_count,
                   s.due_date,s.sla_status,u.fullname
            FROM suggestions s JOIN users u ON s.user_id=u.id
            WHERE s.suggestion_id=%s
        """, (track_id,))
        suggestion = cursor.fetchone()
        if suggestion:
            cursor.execute("""
                SELECT ar.response_text,ar.created_at,a.username as admin_name
                FROM admin_responses ar JOIN admins a ON ar.admin_id=a.id
                WHERE ar.suggestion_id=(SELECT id FROM suggestions WHERE suggestion_id=%s)
                ORDER BY ar.created_at ASC
            """, (track_id,))
            responses = cursor.fetchall()
        else:
            flash('No suggestion found with that tracking ID.', 'danger')
    return render_template('track.html', suggestion=suggestion, responses=responses)

# ─── ADMIN AUTH ─────────────────────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        cursor   = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admins WHERE username=%s AND password=%s AND is_active=1",
                       (username, hash_password(password)))
        admin = cursor.fetchone()
        if admin:
            session.update({'admin_id': admin['id'], 'admin_name': admin['username'],
                            'admin_role': admin['role'], 'is_super_admin': admin['role'] == 'super_admin'})
            cursor.execute("UPDATE admins SET last_login=NOW() WHERE id=%s", (admin['id'],))
            mysql.connection.commit()
            flash('Welcome to Admin Dashboard.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    for k in ['admin_id','admin_name','admin_role']: session.pop(k, None)
    return redirect(url_for('admin_login'))

# ─── ADMIN DASHBOARD ────────────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    cursor = mysql.connection.cursor()
    # Update SLA statuses
    cursor.execute("SELECT id, due_date, status FROM suggestions WHERE status NOT IN ('resolved','rejected')")
    for s in cursor.fetchall():
        sla = get_sla_status(s['due_date'])
        cursor.execute("UPDATE suggestions SET sla_status=%s WHERE id=%s", (sla, s['id']))
    mysql.connection.commit()

    status_filter   = request.args.get('status','all')
    category_filter = request.args.get('category','all')
    priority_filter = request.args.get('priority','all')
    search          = request.args.get('search','').strip()
    page     = int(request.args.get('page',1))
    per_page = 10

    base   = """
        FROM suggestions s JOIN users u ON s.user_id=u.id
        LEFT JOIN admins a2 ON s.assigned_to=a2.id
        LEFT JOIN (SELECT suggestion_id,COUNT(*) as cnt FROM admin_responses GROUP BY suggestion_id) ar
            ON s.id=ar.suggestion_id
        WHERE 1=1
    """
    params = []
    if status_filter   != 'all': base += " AND s.status=%s";   params.append(status_filter)
    if category_filter != 'all': base += " AND s.category=%s"; params.append(category_filter)
    if priority_filter != 'all': base += " AND s.priority=%s"; params.append(priority_filter)
    if search:
        base += " AND (s.title LIKE %s OR s.suggestion_id LIKE %s OR s.description LIKE %s)"
        params += [f'%{search}%']*3

    cursor.execute("SELECT COUNT(*) as cnt " + base, params)
    total   = cursor.fetchone()['cnt']
    offset  = (page-1)*per_page
    cursor.execute(
        "SELECT s.*, u.fullname, u.role as user_role, COALESCE(ar.cnt,0) as response_count, "
        "a2.username as assigned_name " + base +
        " ORDER BY s.created_at DESC LIMIT %s OFFSET %s",
        params+[per_page, offset]
    )
    suggestions = cursor.fetchall()
    stats = get_stats()

    # Category stats for chart
    cursor.execute("SELECT category, COUNT(*) as cnt FROM suggestions GROUP BY category ORDER BY cnt DESC")
    cat_stats = cursor.fetchall()

    # Monthly stats for chart
    cursor.execute("""
        SELECT MONTH(created_at) as month, COUNT(*) as cnt
        FROM suggestions WHERE YEAR(created_at)=YEAR(NOW())
        GROUP BY MONTH(created_at) ORDER BY month
    """)
    monthly_raw = cursor.fetchall()
    monthly = [0]*12
    for r in monthly_raw: monthly[r['month']-1] = r['cnt']

    # Avg satisfaction rating
    cursor.execute("SELECT AVG(rating) as avg_rating FROM satisfaction_ratings")
    avg_rating = cursor.fetchone()['avg_rating'] or 0

    # All admins for assignment dropdown
    cursor.execute("SELECT id, username FROM admins WHERE is_active=1")
    admins = cursor.fetchall()

    return render_template('admin/dashboard.html',
                           suggestions=suggestions, stats=stats, cat_stats=cat_stats,
                           monthly=monthly, avg_rating=round(avg_rating,1),
                           status_filter=status_filter, category_filter=category_filter,
                           priority_filter=priority_filter, search=search,
                           page=page, total_pages=(total+per_page-1)//per_page,
                           total=total, admins=admins)

# ─── ADMIN SUGGESTION DETAIL ────────────────────────────────────────────────────
@app.route('/admin/suggestion/<int:sid>', methods=['GET','POST'])
@admin_required
def admin_suggestion_detail(sid):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.*, u.fullname, u.email, u.role as user_role
        FROM suggestions s JOIN users u ON s.user_id=u.id WHERE s.id=%s
    """, (sid,))
    suggestion = cursor.fetchone()
    if not suggestion:
        flash('Suggestion not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_status':
            new_status = request.form.get('status')
            old_status = suggestion['status']
            cursor.execute("UPDATE suggestions SET status=%s, updated_at=NOW() WHERE id=%s",
                           (new_status, sid))
            mysql.connection.commit()
            log_timeline(sid, 'status_changed',
                         old_value=old_status, new_value=new_status,
                         actor_name=session['admin_name'], actor_type='admin')
            # Email notification
            if new_status in ('under_review', 'resolved', 'rejected'):
                labels   = {'under_review': 'Under Review', 'resolved': 'Resolved', 'rejected': 'Rejected'}
                messages = {
                    'under_review': f'Great news! Your suggestion is now being reviewed by our team. We will get back to you soon.',
                    'resolved':     f'Your suggestion has been resolved! Thank you for helping us improve. Your voice matters.',
                    'rejected':     f'After careful consideration, your suggestion has been reviewed and closed. We appreciate your input and encourage you to submit more ideas.',
                }
                send_notification(
                    suggestion['email'],
                    f'Suggestion Status: {labels.get(new_status)}',
                    messages.get(new_status, ''),
                    suggestion_title=suggestion['title'],
                    tracking_id=suggestion['suggestion_id'],
                    status=new_status
                )
            flash('Status updated.', 'success')

        elif action == 'add_response':
            text = request.form.get('response_text','').strip()
            if text:
                cursor.execute(
                    "INSERT INTO admin_responses (suggestion_id,admin_id,response_text,created_at) VALUES (%s,%s,%s,NOW())",
                    (sid, session['admin_id'], text)
                )
                mysql.connection.commit()
                log_timeline(sid, 'response_added',
                             actor_name=session['admin_name'], actor_type='admin',
                             note=text[:100])
                send_notification(
                    suggestion['email'],
                    'New Response on Your Suggestion',
                    f'An admin has responded to your suggestion:<br><br><em>"{text}"</em><br><br>Login to view the full response and continue the conversation.',
                    suggestion_title=suggestion['title'],
                    tracking_id=suggestion['suggestion_id'],
                    status='under_review'
                )
                flash('Response added.', 'success')
            else:
                flash('Response cannot be empty.', 'danger')

        elif action == 'add_note':
            note = request.form.get('note_text','').strip()
            if note:
                cursor.execute(
                    "INSERT INTO admin_notes (suggestion_id,admin_id,note_text) VALUES (%s,%s,%s)",
                    (sid, session['admin_id'], note)
                )
                mysql.connection.commit()
                flash('Internal note added.', 'success')

        elif action == 'assign':
            assigned_to = request.form.get('assigned_to')
            cursor.execute(
                "UPDATE suggestions SET assigned_to=%s, assigned_at=NOW() WHERE id=%s",
                (assigned_to or None, sid)
            )
            mysql.connection.commit()
            flash('Suggestion assigned.', 'success')

        return redirect(url_for('admin_suggestion_detail', sid=sid))

    cursor.execute("""
        SELECT ar.*, a.username as admin_name FROM admin_responses ar
        JOIN admins a ON ar.admin_id=a.id WHERE ar.suggestion_id=%s ORDER BY ar.created_at ASC
    """, (sid,))
    responses = cursor.fetchall()
    cursor.execute("""
        SELECT an.*, a.username as admin_name FROM admin_notes an
        JOIN admins a ON an.admin_id=a.id WHERE an.suggestion_id=%s ORDER BY an.created_at ASC
    """, (sid,))
    notes = cursor.fetchall()
    cursor.execute("SELECT * FROM attachments WHERE suggestion_id=%s", (sid,))
    attachments = cursor.fetchall()
    cursor.execute("SELECT * FROM satisfaction_ratings WHERE suggestion_id=%s", (sid,))
    rating = cursor.fetchone()
    cursor.execute("SELECT id, username FROM admins WHERE is_active=1")
    admins = cursor.fetchall()
    cursor.execute("""
        SELECT c.*, COALESCE(u.fullname, a.username, 'Unknown') as author
        FROM comments c
        LEFT JOIN users u ON c.user_id = u.id
        LEFT JOIN admins a ON c.admin_id = a.id
        WHERE c.suggestion_id=%s ORDER BY c.created_at ASC
    """, (sid,))
    comments = cursor.fetchall()
    cursor.execute("""
        SELECT * FROM suggestion_timeline
        WHERE suggestion_id=%s ORDER BY created_at ASC
    """, (sid,))
    timeline = cursor.fetchall()

    return render_template('admin/suggestion_detail.html', suggestion=suggestion,
                           responses=responses, notes=notes, attachments=attachments,
                           rating=rating, admins=admins, comments=comments,
                           timeline=timeline,
                           sla_status=get_sla_status(suggestion.get('due_date')))

# ─── ADMIN ANALYTICS API ────────────────────────────────────────────────────────
@app.route('/admin/api/analytics')
@admin_required
def admin_analytics():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT MONTH(created_at) as m, COUNT(*) as cnt
        FROM suggestions WHERE YEAR(created_at)=YEAR(NOW())
        GROUP BY MONTH(created_at)
    """)
    monthly_raw = cursor.fetchall()
    monthly = [0]*12
    for r in monthly_raw: monthly[r['m']-1] = r['cnt']

    cursor.execute("SELECT category, COUNT(*) as cnt FROM suggestions GROUP BY category")
    cats = cursor.fetchall()
    cursor.execute("SELECT status, COUNT(*) as cnt FROM suggestions GROUP BY status")
    statuses = cursor.fetchall()
    cursor.execute("SELECT AVG(rating) as avg FROM satisfaction_ratings")
    avg_rating = cursor.fetchone()['avg'] or 0
    return jsonify({'monthly': monthly, 'categories': cats,
                    'statuses': statuses, 'avg_rating': round(float(avg_rating),1)})

# ─── EXPORT CSV ─────────────────────────────────────────────────────────────────
@app.route('/admin/export/csv')
@admin_required
def export_csv():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.suggestion_id, s.title, s.category, s.priority, s.status,
               s.vote_count, s.sla_status, s.created_at, s.due_date,
               u.fullname, u.email, u.role
        FROM suggestions s JOIN users u ON s.user_id=u.id
        ORDER BY s.created_at DESC
    """)
    rows = cursor.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Title','Category','Priority','Status','Votes',
                     'SLA','Created','Due Date','Submitted By','Email','Role'])
    for r in rows:
        writer.writerow([r['suggestion_id'], r['title'], r['category'], r['priority'],
                         r['status'], r['vote_count'], r['sla_status'],
                         r['created_at'], r['due_date'], r['fullname'], r['email'], r['role']])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=voiceup_export.csv'})

# ─── EXPORT REPORT ──────────────────────────────────────────────────────────────
@app.route('/admin/export/report')
@admin_required
def export_report():
    cursor = mysql.connection.cursor()
    stats  = get_stats()
    cursor.execute("""
        SELECT s.*, u.fullname FROM suggestions s JOIN users u ON s.user_id=u.id
        ORDER BY s.created_at DESC LIMIT 50
    """)
    suggestions = cursor.fetchall()
    cursor.execute("SELECT AVG(rating) as avg FROM satisfaction_ratings")
    avg_rating = cursor.fetchone()['avg'] or 0
    cursor.execute("SELECT category, COUNT(*) as cnt FROM suggestions GROUP BY category ORDER BY cnt DESC")
    cat_stats = cursor.fetchall()
    return render_template('admin/report.html', stats=stats, suggestions=suggestions,
                           avg_rating=round(float(avg_rating),1), cat_stats=cat_stats,
                           generated_at=datetime.now().strftime('%B %d, %Y %H:%M'))

@app.route('/admin/api/stats')
@admin_required
def admin_stats_api():
    return jsonify(get_stats())

# ─── SUPER ADMIN DECORATOR ───────────────────────────────────────────────────
def super_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        if session.get('admin_role') != 'super_admin':
            flash('Super Admin access required.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─── SUPER ADMIN — MANAGE ADMINS ────────────────────────────────────────────
@app.route('/admin/manage-admins')
@super_admin_required
def manage_admins():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT a.*,
               COUNT(DISTINCT ar.id) as response_count,
               COUNT(DISTINCT s.id)  as assigned_count
        FROM admins a
        LEFT JOIN admin_responses ar ON a.id = ar.admin_id
        LEFT JOIN suggestions s ON s.assigned_to = a.id
        GROUP BY a.id
        ORDER BY a.role ASC, a.created_at ASC
    """)
    admins = cursor.fetchall()
    return render_template('admin/manage_admins.html', admins=admins)


@app.route('/admin/create-admin', methods=['GET', 'POST'])
@super_admin_required
def create_admin():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'admin')
        errors   = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if role not in ('super_admin', 'admin', 'moderator'):
            errors.append('Invalid role selected.')
        if errors:
            for e in errors: flash(e, 'danger')
            return redirect(url_for('manage_admins'))

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM admins WHERE username=%s", (username,))
        if cursor.fetchone():
            flash('Username already exists.', 'danger')
            return redirect(url_for('manage_admins'))

        cursor.execute("""
            INSERT INTO admins (username, password, role, is_active, created_at)
            VALUES (%s, %s, %s, 1, NOW())
        """, (username, hash_password(password), role))
        mysql.connection.commit()
        flash(f'Admin "{username}" created successfully!', 'success')
        return redirect(url_for('manage_admins'))

    return redirect(url_for('manage_admins'))


@app.route('/admin/toggle-admin/<int:aid>', methods=['POST'])
@super_admin_required
def toggle_admin(aid):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM admins WHERE id=%s", (aid,))
    admin = cursor.fetchone()
    if not admin:
        flash('Admin not found.', 'danger')
        return redirect(url_for('manage_admins'))
    if admin['role'] == 'super_admin':
        flash('Cannot deactivate a super admin.', 'danger')
        return redirect(url_for('manage_admins'))
    new_status = 0 if admin['is_active'] else 1
    cursor.execute("UPDATE admins SET is_active=%s WHERE id=%s", (new_status, aid))
    mysql.connection.commit()
    label = 'activated' if new_status else 'deactivated'
    flash(f'Admin "{admin["username"]}" {label}.', 'success')
    return redirect(url_for('manage_admins'))


@app.route('/admin/delete-admin/<int:aid>', methods=['POST'])
@super_admin_required
def delete_admin(aid):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM admins WHERE id=%s", (aid,))
    admin = cursor.fetchone()
    if not admin:
        flash('Admin not found.', 'danger')
        return redirect(url_for('manage_admins'))
    if admin['role'] == 'super_admin':
        flash('Cannot delete a super admin.', 'danger')
        return redirect(url_for('manage_admins'))
    if admin['id'] == session['admin_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('manage_admins'))
    cursor.execute("DELETE FROM admins WHERE id=%s", (aid,))
    mysql.connection.commit()
    flash(f'Admin "{admin["username"]}" deleted.', 'success')
    return redirect(url_for('manage_admins'))


@app.route('/admin/change-role/<int:aid>', methods=['POST'])
@super_admin_required
def change_admin_role(aid):
    new_role = request.form.get('role')
    if new_role not in ('super_admin', 'admin', 'moderator'):
        flash('Invalid role.', 'danger')
        return redirect(url_for('manage_admins'))
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM admins WHERE id=%s", (aid,))
    admin = cursor.fetchone()
    if not admin:
        flash('Admin not found.', 'danger')
        return redirect(url_for('manage_admins'))
    cursor.execute("UPDATE admins SET role=%s WHERE id=%s", (new_role, aid))
    mysql.connection.commit()
    flash(f'Role updated for "{admin["username"]}".', 'success')
    return redirect(url_for('manage_admins'))


# ─── SUPER ADMIN — ACTIVITY LOG ─────────────────────────────────────────────
@app.route('/admin/activity')
@super_admin_required
def admin_activity():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT ar.*, a.username as admin_name, s.title as suggestion_title,
               s.suggestion_id as tracking_id
        FROM admin_responses ar
        JOIN admins a ON ar.admin_id = a.id
        JOIN suggestions s ON ar.suggestion_id = s.id
        ORDER BY ar.created_at DESC
        LIMIT 100
    """)
    activities = cursor.fetchall()
    cursor.execute("""
        SELECT an.*, a.username as admin_name, s.title as suggestion_title
        FROM admin_notes an
        JOIN admins a ON an.admin_id = a.id
        JOIN suggestions s ON an.suggestion_id = s.id
        ORDER BY an.created_at DESC
        LIMIT 50
    """)
    notes = cursor.fetchall()
    return render_template('admin/activity.html', activities=activities, notes=notes)


# ═══════════════════════════════════════════════════════════════════
# V3 NEW FEATURES
# ═══════════════════════════════════════════════════════════════════

# ─── HELPERS v3 ─────────────────────────────────────────────────────────────
def get_setting(key, default=''):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT setting_val FROM system_settings WHERE setting_key=%s", (key,))
        row = cursor.fetchone()
        return row['setting_val'] if row else default
    except: return default

def get_all_settings():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT setting_key, setting_val FROM system_settings")
        return {r['setting_key']: r['setting_val'] for r in cursor.fetchall()}
    except: return {}

def create_notification(user_id, title, message, link=''):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO notifications (user_id, title, message, link) VALUES (%s,%s,%s,%s)",
            (user_id, title, message, link)
        )
        mysql.connection.commit()
    except Exception as e:
        print(f'Notification error: {e}')

def get_unread_count(user_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM notifications WHERE user_id=%s AND is_read=0", (user_id,))
        return cursor.fetchone()['cnt']
    except: return 0

def check_login_locked(identifier, type='user'):
    try:
        settings = get_all_settings()
        max_attempts = int(settings.get('max_login_attempts', 5))
        lockout_mins = int(settings.get('lockout_minutes', 30))
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM login_attempts
            WHERE identifier=%s AND type=%s
            AND attempted_at > DATE_SUB(NOW(), INTERVAL %s MINUTE)
        """, (identifier, type, lockout_mins))
        count = cursor.fetchone()['cnt']
        return count >= max_attempts
    except: return False

def record_login_attempt(identifier, type='user'):
    try:
        cursor = mysql.connection.cursor()
        ip = request.remote_addr or '0.0.0.0'
        cursor.execute(
            "INSERT INTO login_attempts (identifier, type, ip_address) VALUES (%s,%s,%s)",
            (identifier, type, ip)
        )
        mysql.connection.commit()
    except: pass

def clear_login_attempts(identifier, type='user'):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM login_attempts WHERE identifier=%s AND type=%s", (identifier, type))
        mysql.connection.commit()
    except: pass

# Inject notification count into all templates
@app.context_processor
def inject_globals():
    unread = 0
    announcement = ''
    announcement_active = False
    try:
        if 'user_id' in session:
            unread = get_unread_count(session['user_id'])
        announcement = get_setting('announcement', '')
        announcement_active = get_setting('announcement_active', '0') == '1'
    except: pass
    # Avatar color helper
    def avatar_color(name):
        colors = ['#6366f1','#8b5cf6','#ec4899','#ef4444','#f59e0b',
                  '#10b981','#06b6d4','#3b82f6','#84cc16','#f97316']
        idx = sum(ord(c) for c in (name or 'U')) % len(colors)
        return colors[idx]
    def avatar_initials(name):
        if not name: return 'U'
        parts = name.strip().split()
        if len(parts) >= 2: return (parts[0][0] + parts[-1][0]).upper()
        return name[0].upper()
    return dict(unread_count=unread, announcement=announcement,
                announcement_active=announcement_active,
                avatar_color=avatar_color, avatar_initials=avatar_initials)

# ─── NOTIFICATIONS ───────────────────────────────────────────────────────────
@app.route('/notifications')
@login_required
def notifications():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 50
    """, (session['user_id'],))
    notifs = cursor.fetchall()
    cursor.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session['user_id'],))
    mysql.connection.commit()
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session['user_id'],))
    mysql.connection.commit()
    return jsonify({'success': True})

@app.route('/notifications/count')
@login_required
def notification_count():
    return jsonify({'count': get_unread_count(session['user_id'])})

# ─── COMMENTS ────────────────────────────────────────────────────────────────
@app.route('/suggestion/<suggestion_id>/comment', methods=['POST'])
@login_required
def add_comment(suggestion_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, user_id FROM suggestions WHERE suggestion_id=%s", (suggestion_id,))
    sug = cursor.fetchone()
    if not sug or sug['user_id'] != session['user_id']:
        flash('Not found.', 'danger')
        return redirect(url_for('my_suggestions'))
    body = request.form.get('body', '').strip()
    if not body:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('suggestion_detail', suggestion_id=suggestion_id))
    cursor.execute(
        "INSERT INTO comments (suggestion_id, user_id, body) VALUES (%s,%s,%s)",
        (sug['id'], session['user_id'], body)
    )
    mysql.connection.commit()
    flash('Comment added.', 'success')
    return redirect(url_for('suggestion_detail', suggestion_id=suggestion_id))

@app.route('/admin/suggestion/<int:sid>/comment', methods=['POST'])
@admin_required
def admin_add_comment(sid):
    body = request.form.get('body', '').strip()
    if body:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO comments (suggestion_id, admin_id, body) VALUES (%s,%s,%s)",
            (sid, session['admin_id'], body)
        )
        mysql.connection.commit()
        # Notify the user
        cursor.execute("SELECT user_id, title, suggestion_id FROM suggestions WHERE id=%s", (sid,))
        sug = cursor.fetchone()
        if sug:
            create_notification(
                sug['user_id'],
                'New comment on your suggestion',
                f'An admin commented on: {sug["title"]}',
                url_for('suggestion_detail', suggestion_id=sug['suggestion_id'])
            )
        flash('Comment added.', 'success')
    return redirect(url_for('admin_suggestion_detail', sid=sid))

# ─── PASSWORD RESET ──────────────────────────────────────────────────────────
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, fullname FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        if user:
            token = hashlib.sha256(os.urandom(32)).hexdigest()
            expires = datetime.now() + timedelta(hours=1)
            cursor.execute(
                "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s,%s,%s)",
                (user['id'], token, expires)
            )
            mysql.connection.commit()
            reset_link = url_for('reset_password', token=token, _external=True)
            send_notification(email, 'Password Reset — VoiceUp',
                f'<p>Hi {user["fullname"]},</p><p>Click to reset your password: <a href="{reset_link}">{reset_link}</a></p><p>Expires in 1 hour.</p>')
            flash(f'Reset link generated! Link: <code>{reset_link}</code>', 'success')
        else:
            flash('If that email exists, a reset link has been sent.', 'info')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT pr.*, u.email FROM password_resets pr
        JOIN users u ON pr.user_id = u.id
        WHERE pr.token=%s AND pr.used=0 AND pr.expires_at > NOW()
    """, (token,))
    reset = cursor.fetchone()
    if not reset:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('user_login'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            cursor.execute("UPDATE users SET password=%s WHERE id=%s",
                           (hash_password(password), reset['user_id']))
            cursor.execute("UPDATE password_resets SET used=1 WHERE token=%s", (token,))
            mysql.connection.commit()
            flash('Password reset successfully! Please log in.', 'success')
            return redirect(url_for('user_login'))
    return render_template('reset_password.html', token=token)

# ─── UPDATED LOGIN WITH LOCKOUT ─────────────────────────────────────────────
# Override the original login to add lockout
# (the original /login route handles this via updated logic in the template check)

# ─── USER MANAGEMENT (Super Admin) ──────────────────────────────────────────
@app.route('/admin/users')
@super_admin_required
def manage_users():
    search = request.args.get('search', '').strip()
    page   = int(request.args.get('page', 1))
    per_page = 15
    cursor = mysql.connection.cursor()
    base = "FROM users u LEFT JOIN (SELECT user_id, COUNT(*) as cnt FROM suggestions GROUP BY user_id) s ON u.id=s.user_id WHERE 1=1"
    params = []
    if search:
        base += " AND (u.fullname LIKE %s OR u.email LIKE %s)"
        params += [f'%{search}%', f'%{search}%']
    cursor.execute("SELECT COUNT(*) as cnt " + base, params)
    total = cursor.fetchone()['cnt']
    offset = (page - 1) * per_page
    cursor.execute(
        "SELECT u.*, COALESCE(s.cnt,0) as suggestion_count " + base +
        " ORDER BY u.created_at DESC LIMIT %s OFFSET %s",
        params + [per_page, offset]
    )
    users = cursor.fetchall()
    return render_template('admin/manage_users.html', users=users, search=search,
                           page=page, total_pages=(total+per_page-1)//per_page, total=total)

@app.route('/admin/users/<int:uid>/ban', methods=['POST'])
@super_admin_required
def ban_user(uid):
    reason = request.form.get('reason', 'Violation of terms').strip()
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE users SET is_banned=1, ban_reason=%s WHERE id=%s", (reason, uid))
    mysql.connection.commit()
    flash('User banned successfully.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/users/<int:uid>/unban', methods=['POST'])
@super_admin_required
def unban_user(uid):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE id=%s", (uid,))
    mysql.connection.commit()
    flash('User unbanned successfully.', 'success')
    return redirect(url_for('manage_users'))

# ─── SYSTEM SETTINGS (Super Admin) ──────────────────────────────────────────
@app.route('/admin/settings', methods=['GET', 'POST'])
@super_admin_required
def system_settings():
    if request.method == 'POST':
        keys = ['site_name', 'announcement', 'announcement_active', 'maintenance_mode',
                'sla_urgent', 'sla_high', 'sla_medium', 'sla_low',
                'max_login_attempts', 'lockout_minutes', 'categories']
        cursor = mysql.connection.cursor()
        for key in keys:
            val = request.form.get(key, '')
            if key == 'announcement_active':
                val = '1' if request.form.get('announcement_active') else '0'
            if key == 'maintenance_mode':
                val = '1' if request.form.get('maintenance_mode') else '0'
            cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_val, updated_at)
                VALUES (%s,%s,NOW())
                ON DUPLICATE KEY UPDATE setting_val=%s, updated_at=NOW()
            """, (key, val, val))
        mysql.connection.commit()
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('system_settings'))
    settings = get_all_settings()
    return render_template('admin/system_settings.html', settings=settings)

# ─── MERGE SUGGESTIONS (Admin) ───────────────────────────────────────────────
@app.route('/admin/suggestion/<int:sid>/merge', methods=['POST'])
@admin_required
def merge_suggestion(sid):
    target_id = request.form.get('merge_into', '').strip()
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM suggestions WHERE suggestion_id=%s", (target_id,))
    target = cursor.fetchone()
    if not target:
        flash('Target suggestion ID not found.', 'danger')
        return redirect(url_for('admin_suggestion_detail', sid=sid))
    if target['id'] == sid:
        flash('Cannot merge a suggestion into itself.', 'danger')
        return redirect(url_for('admin_suggestion_detail', sid=sid))
    # Move votes and responses to target
    cursor.execute("UPDATE votes SET suggestion_id=%s WHERE suggestion_id=%s", (target['id'], sid))
    cursor.execute("UPDATE admin_responses SET suggestion_id=%s WHERE suggestion_id=%s", (target['id'], sid))
    cursor.execute("UPDATE comments SET suggestion_id=%s WHERE suggestion_id=%s", (target['id'], sid))
    # Update vote count on target
    cursor.execute("SELECT COUNT(*) as cnt FROM votes WHERE suggestion_id=%s", (target['id'],))
    vote_count = cursor.fetchone()['cnt']
    cursor.execute("UPDATE suggestions SET vote_count=%s WHERE id=%s", (vote_count, target['id']))
    # Mark original as merged
    cursor.execute("UPDATE suggestions SET is_merged=1, merged_into=%s, status='resolved' WHERE id=%s",
                   (target['id'], sid))
    mysql.connection.commit()
    flash(f'Suggestion merged into {target_id} successfully.', 'success')
    return redirect(url_for('admin_suggestion_detail', sid=target['id']))

# ─── ADMIN PERFORMANCE LEADERBOARD ──────────────────────────────────────────
@app.route('/admin/leaderboard')
@admin_required
def admin_leaderboard():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT
            a.id, a.username, a.role,
            COUNT(DISTINCT ar.id)  as total_responses,
            COUNT(DISTINCT s_assigned.id) as total_assigned,
            COUNT(DISTINCT s_resolved.id) as total_resolved,
            AVG(sr.rating) as avg_satisfaction,
            MIN(ar.created_at) as first_response,
            MAX(ar.created_at) as last_response
        FROM admins a
        LEFT JOIN admin_responses ar ON a.id = ar.admin_id
        LEFT JOIN suggestions s_assigned ON s_assigned.assigned_to = a.id
        LEFT JOIN suggestions s_resolved ON s_resolved.assigned_to = a.id AND s_resolved.status = 'resolved'
        LEFT JOIN satisfaction_ratings sr ON sr.suggestion_id IN (
            SELECT id FROM suggestions WHERE assigned_to = a.id
        )
        WHERE a.is_active = 1
        GROUP BY a.id
        ORDER BY total_responses DESC
    """)
    admins = cursor.fetchall()

    # Monthly response trend for chart
    cursor.execute("""
        SELECT a.username, MONTH(ar.created_at) as month, COUNT(*) as cnt
        FROM admin_responses ar
        JOIN admins a ON ar.admin_id = a.id
        WHERE YEAR(ar.created_at) = YEAR(NOW())
        GROUP BY a.id, MONTH(ar.created_at)
        ORDER BY a.username, month
    """)
    trend_raw = cursor.fetchall()

    return render_template('admin/leaderboard.html', admins=admins, trend_raw=trend_raw)

# ─── BANNED USER CHECK MIDDLEWARE ────────────────────────────────────────────
@app.before_request
def check_banned():
    if 'user_id' in session:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT is_banned FROM users WHERE id=%s", (session['user_id'],))
            user = cursor.fetchone()
            if user and user['is_banned']:
                for k in ['user_id','user_name','user_role','user_email']: session.pop(k, None)
                flash('Your account has been suspended. Please contact administration.', 'danger')
                return redirect(url_for('index'))
        except: pass




# ═══════════════════════════════════════════════════════════════════
# V4 — AI FEATURES (Claude API)
# ═══════════════════════════════════════════════════════════════════

import json
import urllib.request
import urllib.error

def claude_api(prompt, system='You are a helpful assistant.', max_tokens=800):
    """Call Gemini API and return text response."""
    try:
        full_prompt = f"{system}\n\n{prompt}"
        payload = json.dumps({
            'contents': [{'parts': [{'text': full_prompt}]}],
            'generationConfig': {'maxOutputTokens': max_tokens}
        }).encode('utf-8')
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}'
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f'Gemini API error: {e}')
        return None

def claude_json(prompt, system='Respond only with valid JSON. No markdown, no explanation.', max_tokens=600):
    """Call Claude API and return parsed JSON."""
    result = claude_api(prompt, system, max_tokens)
    if not result:
        return None
    try:
        clean = result.strip().replace('```json','').replace('```','').strip()
        return json.loads(clean)
    except:
        return None

# ─── AI AUTO-ANALYZE (runs when suggestion is submitted) ────────────────────
def ai_analyze_suggestion(suggestion_id, title, description, category):
    """Analyze a suggestion with AI: sentiment, auto-category, priority, summary."""
    try:
        result = claude_json(f"""
Analyze this suggestion and return JSON with these exact keys:
- sentiment: one of "positive", "neutral", "frustrated", "urgent", "angry"
- sentiment_score: float 0.0-1.0 (1.0 = very positive)
- auto_category: best category from: academics, facilities, welfare, technology, administration, sports, other
- auto_priority: one of "low", "medium", "high", "urgent"
- summary: one sentence summary under 20 words
- keywords: comma-separated top 3 keywords

Title: {title}
Category: {category}
Description: {description}
""")
        if result:
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO ai_analysis 
                (suggestion_id, sentiment, sentiment_score, auto_category, auto_priority, summary, keywords)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                sentiment=%s, sentiment_score=%s, auto_category=%s,
                auto_priority=%s, summary=%s, keywords=%s, analyzed_at=NOW()
            """, (
                suggestion_id,
                result.get('sentiment','neutral'),
                result.get('sentiment_score', 0.5),
                result.get('auto_category', category),
                result.get('auto_priority','medium'),
                result.get('summary',''),
                result.get('keywords',''),
                result.get('sentiment','neutral'),
                result.get('sentiment_score', 0.5),
                result.get('auto_category', category),
                result.get('auto_priority','medium'),
                result.get('summary',''),
                result.get('keywords','')
            ))
            cursor.execute("UPDATE suggestions SET ai_sentiment=%s, ai_summary=%s WHERE id=%s",
                           (result.get('sentiment'), result.get('summary'), suggestion_id))
            mysql.connection.commit()
    except Exception as e:
        print(f'AI analyze error: {e}')

# ─── AI AUTO-CATEGORIZE API ─────────────────────────────────────────────────
@app.route('/api/ai/categorize', methods=['POST'])
@login_required
def ai_categorize():
    """Called from submit form to suggest category and priority."""
    title       = request.json.get('title','')
    description = request.json.get('description','')
    if not title and not description:
        return jsonify({'error': 'No content'})
    result = claude_json(f"""
Analyze this suggestion and return JSON with:
- category: one of: academics, facilities, welfare, technology, administration, sports, other
- priority: one of: low, medium, high, urgent  
- reason: one sentence why

Title: {title}
Description: {description}
""")
    if result:
        return jsonify(result)
    return jsonify({'category': '', 'priority': 'medium'})

# ─── AI WRITING HELPER ───────────────────────────────────────────────────────
@app.route('/api/ai/improve', methods=['POST'])
@login_required
def ai_improve_writing():
    """Improve suggestion text."""
    text = request.json.get('text','')
    if not text or len(text) < 10:
        return jsonify({'error': 'Text too short'})
    result = claude_api(
        f"Improve this suggestion to be clearer, more professional and constructive. Keep it under 150 words. Return only the improved text, nothing else:\n\n{text}",
        "You are a writing assistant helping students write better suggestions."
    )
    if result:
        return jsonify({'improved': result.strip()})
    return jsonify({'error': 'Could not improve text'})

# ─── AI DUPLICATE DETECTOR ──────────────────────────────────────────────────
@app.route('/api/ai/duplicates', methods=['POST'])
@login_required
def ai_find_duplicates():
    """Find similar existing suggestions."""
    title       = request.json.get('title','')
    description = request.json.get('description','')
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT suggestion_id, title, description, status, vote_count
        FROM suggestions WHERE user_id != %s
        ORDER BY created_at DESC LIMIT 20
    """, (session['user_id'],))
    existing = cursor.fetchall()
    if not existing or (not title and not description):
        return jsonify({'duplicates': []})

    existing_list = '\n'.join([f"- ID:{s['suggestion_id']} | {s['title']}: {s['description'][:80]}" for s in existing])
    result = claude_json(f"""
New suggestion:
Title: {title}
Description: {description}

Existing suggestions:
{existing_list}

Return JSON with key "duplicates" containing an array of objects with:
- id: the suggestion ID (e.g. SGT-XXXX)
- title: the suggestion title
- similarity: percentage 0-100
Only include suggestions with similarity above 50%. Max 3 results.
""")
    if result:
        return jsonify(result)
    return jsonify({'duplicates': []})

# ─── AI DRAFT RESPONSE ──────────────────────────────────────────────────────
@app.route('/admin/suggestion/<int:sid>/ai-draft', methods=['POST'])
@admin_required
def ai_draft_response(sid):
    """Generate an AI draft response for admin to review."""
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM suggestions WHERE id=%s", (sid,))
    sug = cursor.fetchone()
    if not sug:
        return jsonify({'error': 'Not found'})

    draft = claude_api(
        f"""Write a professional, empathetic response to this student suggestion.
Be constructive, acknowledge their concern, and explain next steps.
Keep it under 100 words.

Title: {sug['title']}
Category: {sug['category']}
Priority: {sug['priority']}
Description: {sug['description']}""",
        "You are a school administrator responding to student suggestions professionally."
    )
    if draft:
        cursor.execute(
            "INSERT INTO ai_drafts (suggestion_id, draft_text) VALUES (%s,%s)",
            (sid, draft.strip())
        )
        mysql.connection.commit()
        return jsonify({'draft': draft.strip()})
    return jsonify({'error': 'Could not generate draft'})

# ─── AI TREND DETECTION ─────────────────────────────────────────────────────
@app.route('/admin/ai/trends')
@admin_required
def ai_trends():
    """AI-powered trend analysis of all suggestions."""
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.title, s.category, s.description, s.status, s.vote_count,
               s.created_at, aa.sentiment, aa.keywords
        FROM suggestions s
        LEFT JOIN ai_analysis aa ON s.id = aa.suggestion_id
        ORDER BY s.created_at DESC LIMIT 50
    """)
    suggestions = cursor.fetchall()

    # Build summary for Claude
    sug_text = '\n'.join([
        f"- [{s['category']}] {s['title']} (votes:{s['vote_count']}, sentiment:{s.get('sentiment','?')})"
        for s in suggestions
    ])

    analysis = claude_json(f"""
Analyze these recent suggestions from a school suggestion system and return JSON with:
- top_issues: array of top 3 recurring issues (each with "issue" and "count" fields)
- trending_categories: array of categories gaining traction (each with "category" and "trend" fields)  
- sentiment_summary: overall mood: "positive", "mixed", or "concerning"
- urgent_patterns: array of up to 2 patterns that need immediate attention
- recommendations: array of 3 actionable recommendations for admin

Suggestions:
{sug_text}
""", max_tokens=1000)

    # Get saved reports
    cursor.execute("SELECT * FROM ai_reports ORDER BY generated_at DESC LIMIT 5")
    past_reports = cursor.fetchall()

    return render_template('admin/ai_trends.html',
                           analysis=analysis, suggestions=suggestions,
                           past_reports=past_reports)

# ─── AI INSIGHTS REPORT ─────────────────────────────────────────────────────
@app.route('/admin/ai/insights-report', methods=['POST'])
@admin_required
def ai_generate_report():
    """Generate a full AI insights report."""
    cursor = mysql.connection.cursor()
    stats = get_stats()
    cursor.execute("""
        SELECT s.category, s.priority, s.status, s.vote_count,
               aa.sentiment, aa.keywords, aa.summary
        FROM suggestions s
        LEFT JOIN ai_analysis aa ON s.id = aa.suggestion_id
        ORDER BY s.created_at DESC LIMIT 100
    """)
    data = cursor.fetchall()

    cursor.execute("SELECT AVG(rating) as avg FROM satisfaction_ratings")
    avg_rating = cursor.fetchone()['avg'] or 0

    data_text = '\n'.join([
        f"[{d['category']}|{d['priority']}|{d['status']}|votes:{d['vote_count']}|sentiment:{d.get('sentiment','?')}] {d.get('summary','') or ''}"
        for d in data
    ])

    report = claude_api(f"""
Generate a comprehensive institutional suggestion system report. Write in professional prose.
Include:
1. Executive Summary (2-3 sentences)
2. Key Statistics Analysis
3. Top Issues Identified
4. Sentiment Analysis Overview
5. Department/Category Breakdown
6. Recommendations (numbered list of 5)
7. Conclusion

Data:
- Total suggestions: {stats['total']}
- Pending: {stats['pending']}, Under Review: {stats['under_review']}, Resolved: {stats['resolved']}
- Average satisfaction: {round(float(avg_rating),1)}/5
- Recent suggestions: {data_text[:2000]}
""", "You are an institutional analyst writing a formal report.", max_tokens=1500)

    if report:
        cursor.execute(
            "INSERT INTO ai_reports (report_type, content) VALUES ('insights', %s)",
            (report,)
        )
        mysql.connection.commit()
        return jsonify({'report': report})
    return jsonify({'error': 'Could not generate report'})

# ─── AI CHATBOT ──────────────────────────────────────────────────────────────
@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    """AI chatbot for students to get help before submitting."""
    data     = request.json
    message  = data.get('message','').strip()
    history  = data.get('history', [])

    if not message:
        return jsonify({'error': 'Empty message'})

    # Build conversation
    messages = []
    for h in history[-6:]:  # Keep last 6 messages for context
        messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': message})

    try:
        system_msg = """You are VoiceBot, a helpful AI assistant for VoiceUp — a school suggestion system.
Help students:
1. Decide whether to submit a suggestion
2. Improve their suggestion wording
3. Choose the right category and priority
4. Understand how the system works
5. Track their suggestions

Be friendly, concise and encouraging. If they seem to have a valid suggestion, encourage them to submit it."""

        history_text = '\n'.join([f"{h['role']}: {h['content']}" for h in history[-6:]])
        full_prompt = f"{system_msg}\n\nConversation history:\n{history_text}\n\nUser: {message}"
        payload = json.dumps({
            'contents': [{'parts': [{'text': full_prompt}]}],
            'generationConfig': {'maxOutputTokens': 400}
        }).encode('utf-8')
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}'
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            reply = result['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'reply': "I'm having trouble connecting right now. Please try again shortly."})

# ─── AI SENTIMENT BADGE API ─────────────────────────────────────────────────
@app.route('/admin/api/sentiment-overview')
@admin_required
def sentiment_overview():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT aa.sentiment, COUNT(*) as cnt
        FROM ai_analysis aa
        GROUP BY aa.sentiment
    """)
    data = cursor.fetchall()
    return jsonify({'sentiments': data})


# ─── ADMIN PROFILE ───────────────────────────────────────────────────────────
@app.route('/admin/profile')
@admin_required
def admin_profile():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM admins WHERE id=%s", (session['admin_id'],))
    admin = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as cnt FROM admin_responses WHERE admin_id=%s", (session['admin_id'],))
    total_responses = cursor.fetchone()['cnt']

    cursor.execute("""SELECT COUNT(*) as cnt FROM suggestions
        WHERE assigned_to=%s AND status='resolved'""", (session['admin_id'],))
    resolved = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM suggestions WHERE assigned_to=%s", (session['admin_id'],))
    assigned = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM admin_notes WHERE admin_id=%s", (session['admin_id'],))
    notes = cursor.fetchone()['cnt']

    stats = {'total_responses': total_responses, 'resolved': resolved,
             'assigned': assigned, 'notes': notes}

    return render_template('admin/admin_profile.html', admin=admin, stats=stats)


@app.route('/admin/change-username', methods=['POST'])
@admin_required
def admin_change_username():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    cursor   = mysql.connection.cursor()
    cursor.execute("SELECT password FROM admins WHERE id=%s", (session['admin_id'],))
    admin = cursor.fetchone()

    if admin['password'] != hash_password(password):
        flash('Incorrect password.', 'danger')
    elif len(username) < 3:
        flash('Username must be at least 3 characters.', 'danger')
    else:
        cursor.execute("SELECT id FROM admins WHERE username=%s AND id != %s",
                       (username, session['admin_id']))
        if cursor.fetchone():
            flash('Username already taken.', 'danger')
        else:
            cursor.execute("UPDATE admins SET username=%s WHERE id=%s",
                           (username, session['admin_id']))
            mysql.connection.commit()
            session['admin_name'] = username
            flash('Username updated successfully!', 'success')
    return redirect(url_for('admin_profile'))


@app.route('/admin/change-password', methods=['POST'])
@admin_required
def admin_change_password():
    current  = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm  = request.form.get('confirm_password', '')
    cursor   = mysql.connection.cursor()
    cursor.execute("SELECT password FROM admins WHERE id=%s", (session['admin_id'],))
    admin = cursor.fetchone()

    if admin['password'] != hash_password(current):
        flash('Current password is incorrect.', 'danger')
    elif len(new_pass) < 8:
        flash('New password must be at least 8 characters.', 'danger')
    elif new_pass != confirm:
        flash('Passwords do not match.', 'danger')
    else:
        cursor.execute("UPDATE admins SET password=%s WHERE id=%s",
                       (hash_password(new_pass), session['admin_id']))
        mysql.connection.commit()
        flash('Password updated successfully!', 'success')
    return redirect(url_for('admin_profile'))


# ═══════════════════════════════════════════════════════════════════
# V5 — PROFILE, TEMPLATES, BULK UPDATE, SMS, PWA
# ═══════════════════════════════════════════════════════════════════

import json as _json

# ─── PWA ROUTES ──────────────────────────────────────────────────────────────
@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

# ─── SMS NOTIFICATIONS (Africa's Talking) ───────────────────────────────────
AT_USERNAME = ''   # Your Africa's Talking username
AT_API_KEY  = ''   # Your Africa's Talking API key
AT_ENABLED  = False

def send_sms(phone, message):
    if not AT_ENABLED or not phone: return
    try:
        import urllib.parse
        payload = urllib.parse.urlencode({
            'username': AT_USERNAME,
            'to': phone,
            'message': message
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.africastalking.com/version1/messaging',
            data=payload,
            headers={
                'apiKey': AT_API_KEY,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO sms_log (phone, message) VALUES (%s,%s)", (phone, message))
            mysql.connection.commit()
    except Exception as e:
        print(f'SMS error: {e}')

# ─── PROFILE ─────────────────────────────────────────────────────────────────
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()

    if request.method == 'POST':
        fullname   = request.form.get('fullname', '').strip()
        student_id = request.form.get('student_id', '').strip()
        phone      = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        bio        = request.form.get('bio', '').strip()

        # Handle photo upload
        photo_filename = user['profile_photo']
        photo = request.files.get('profile_photo')
        if photo and photo.filename and allowed_file(photo.filename):
            safe   = secure_filename(photo.filename)
            unique = f"profile_{session['user_id']}_{int(datetime.now().timestamp())}_{safe}"
            path   = os.path.join(app.config['UPLOAD_FOLDER'], unique)
            photo.save(path)
            photo_filename = unique

        cursor.execute("""
            UPDATE users SET fullname=%s, student_id=%s, phone=%s,
            department=%s, bio=%s, profile_photo=%s WHERE id=%s
        """, (fullname, student_id or None, phone or None,
              department or None, bio or None, photo_filename, session['user_id']))
        mysql.connection.commit()
        session['user_name'] = fullname
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    cursor.execute("""
        SELECT COUNT(*) as total, SUM(status='pending') as pending,
               SUM(status='resolved') as resolved
        FROM suggestions WHERE user_id=%s
    """, (session['user_id'],))
    stats = cursor.fetchone()
    return render_template('profile.html', user=user, stats=stats)


@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current  = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm  = request.form.get('confirm_password', '')
    cursor   = mysql.connection.cursor()
    cursor.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()
    if user['password'] != hash_password(current):
        flash('Current password is incorrect.', 'danger')
    elif len(new_pass) < 8:
        flash('New password must be at least 8 characters.', 'danger')
    elif new_pass != confirm:
        flash('Passwords do not match.', 'danger')
    else:
        cursor.execute("UPDATE users SET password=%s WHERE id=%s",
                       (hash_password(new_pass), session['user_id']))
        mysql.connection.commit()
        flash('Password updated successfully!', 'success')
    return redirect(url_for('profile'))

# ─── LOGIN WITH STUDENT ID ───────────────────────────────────────────────────
@app.route('/login-student', methods=['GET', 'POST'])
def student_login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        password   = request.form.get('password', '')
        cursor     = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE student_id=%s AND password=%s",
                       (student_id, hash_password(password)))
        user = cursor.fetchone()
        if user:
            session.update({'user_id': user['id'], 'user_name': user['fullname'],
                            'user_role': user['role'], 'user_email': user['email']})
            flash(f'Welcome back, {user["fullname"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid Student ID or password.', 'danger')
    return render_template('login_student.html')

# ─── SUGGESTION TEMPLATES ────────────────────────────────────────────────────
@app.route('/templates')
@login_required
def suggestion_templates():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM suggestion_templates WHERE is_active=1 ORDER BY use_count DESC")
    templates = cursor.fetchall()
    return render_template('templates.html',
                           templates=templates,
                           templates_json=_json.dumps([dict(t) for t in templates], default=str))

@app.route('/api/template/<int:tid>')
@login_required
def get_template(tid):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM suggestion_templates WHERE id=%s", (tid,))
    t = cursor.fetchone()
    if t:
        cursor.execute("UPDATE suggestion_templates SET use_count=use_count+1 WHERE id=%s", (tid,))
        mysql.connection.commit()
        return jsonify(dict(t))
    return jsonify({'error': 'Not found'})

# ─── BULK STATUS UPDATE ──────────────────────────────────────────────────────
@app.route('/admin/bulk-update', methods=['GET', 'POST'])
@admin_required
def admin_bulk_update():
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        ids        = request.form.getlist('suggestion_ids')
        new_status = request.form.get('new_status', '')
        if ids and new_status:
            placeholders = ','.join(['%s'] * len(ids))
            cursor.execute(
                f"UPDATE suggestions SET status=%s, updated_at=NOW() WHERE id IN ({placeholders})",
                [new_status] + ids
            )
            mysql.connection.commit()
            flash(f'Updated {len(ids)} suggestions to {new_status.replace("_"," ").title()}.', 'success')
        return redirect(url_for('admin_dashboard'))

    cursor.execute("""
        SELECT s.*, u.fullname FROM suggestions s
        JOIN users u ON s.user_id=u.id
        ORDER BY s.created_at DESC
    """)
    suggestions = cursor.fetchall()
    return render_template('admin/bulk_update.html', suggestions=suggestions)

# ─── PROFILE CSS ADDITIONS ───────────────────────────────────────────────────
# Add profile styles to CSS (already in style.css additions below)


# ═══════════════════════════════════════════════════════════════════
# V6 — EMAIL SETTINGS, DEPARTMENTS, PDF REPORT
# ═══════════════════════════════════════════════════════════════════

# ─── DYNAMIC EMAIL SETTINGS ──────────────────────────────────────────────────
def get_email_config():
    """Get email config from database settings."""
    try:
        settings = get_all_settings()
        return {
            'enabled':   settings.get('email_enabled','0') == '1',
            'host':      settings.get('email_host','smtp.gmail.com'),
            'port':      int(settings.get('email_port','587')),
            'user':      settings.get('email_user',''),
            'password':  settings.get('email_password',''),
            'from_name': settings.get('email_from_name','VoiceUp System')
        }
    except:
        return {'enabled': False}

def send_email(to_email, subject, body):
    """Send email using settings from database."""
    cfg = get_email_config()
    if not cfg['enabled'] or not cfg['user'] or not to_email:
        return False
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText as MIMETextMsg
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{cfg['from_name']} <{cfg['user']}>"
        msg['To']      = to_email
        msg.attach(MIMETextMsg(body, 'html'))
        with smtplib.SMTP(cfg['host'], cfg['port']) as s:
            s.starttls()
            s.login(cfg['user'], cfg['password'])
            s.sendmail(cfg['user'], [to_email], msg.as_string())
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO email_log (to_email, subject) VALUES (%s,%s)", (to_email, subject))
        mysql.connection.commit()
        return True
    except Exception as e:
        print(f'Email error: {e}')
        return False

# ─── EMAIL SETTINGS PAGE ─────────────────────────────────────────────────────
@app.route('/admin/email-settings', methods=['GET'])
@super_admin_required
def email_settings():
    settings = get_all_settings()
    cursor   = mysql.connection.cursor()
    cursor.execute("SELECT * FROM email_log ORDER BY sent_at DESC LIMIT 10")
    email_log = cursor.fetchall()
    return render_template('admin/email_settings.html', settings=settings, email_log=email_log)

@app.route('/admin/email-settings/save', methods=['POST'])
@super_admin_required
def save_email_settings():
    cursor = mysql.connection.cursor()
    keys   = ['email_user','email_password','email_from_name','email_host','email_port']
    for key in keys:
        val = request.form.get(key,'')
        cursor.execute("""
            INSERT INTO system_settings (setting_key, setting_val, updated_at)
            VALUES (%s,%s,NOW()) ON DUPLICATE KEY UPDATE setting_val=%s, updated_at=NOW()
        """, (key, val, val))
    enabled = '1' if request.form.get('email_enabled') else '0'
    cursor.execute("""
        INSERT INTO system_settings (setting_key, setting_val, updated_at)
        VALUES ('email_enabled',%s,NOW()) ON DUPLICATE KEY UPDATE setting_val=%s, updated_at=NOW()
    """, (enabled, enabled))
    mysql.connection.commit()
    flash('Email settings saved successfully!', 'success')
    return redirect(url_for('email_settings'))

@app.route('/admin/test-email', methods=['POST'])
@super_admin_required
def test_email():
    cfg = get_email_config()
    if not cfg['enabled']:
        return jsonify({'message': 'Email is disabled. Enable it first.'})
    success = send_email(
        cfg['user'],
        'VoiceUp — Test Email',
        '<h2>VoiceUp Email Test</h2><p>Your email settings are working correctly!</p>'
    )
    if success:
        return jsonify({'message': 'Test email sent successfully to ' + cfg['user']})
    return jsonify({'message': 'Failed to send. Check your Gmail and App Password.'})

# ─── DEPARTMENTS ─────────────────────────────────────────────────────────────
@app.route('/admin/departments')
@admin_required
def departments():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT d.*, a.username as head_name,
               COUNT(s.id) as suggestion_count
        FROM departments d
        LEFT JOIN admins a ON d.head_admin = a.id
        LEFT JOIN suggestions s ON s.department_id = d.id
        WHERE d.is_active = 1
        GROUP BY d.id
        ORDER BY d.name
    """)
    depts = cursor.fetchall()
    cursor.execute("SELECT * FROM category_departments")
    routing = cursor.fetchall()
    cursor.execute("SELECT id, username FROM admins WHERE is_active=1")
    admins = cursor.fetchall()
    return render_template('admin/departments.html',
                           departments=depts, routing=routing, admins=admins)

@app.route('/admin/departments/save', methods=['POST'])
@admin_required
def save_department():
    dept_id     = request.form.get('dept_id','').strip()
    name        = request.form.get('name','').strip()
    description = request.form.get('description','').strip()
    email       = request.form.get('email','').strip()
    color       = request.form.get('color','#6366f1')
    icon        = request.form.get('icon','fa-building')
    head_admin  = request.form.get('head_admin','') or None
    cursor      = mysql.connection.cursor()
    if dept_id:
        cursor.execute("""UPDATE departments SET name=%s, description=%s, email=%s,
            color=%s, icon=%s, head_admin=%s WHERE id=%s""",
            (name, description, email, color, icon, head_admin, dept_id))
        flash('Department updated!', 'success')
    else:
        cursor.execute("""INSERT INTO departments (name,description,email,color,icon,head_admin)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (name, description, email, color, icon, head_admin))
        flash('Department created!', 'success')
    mysql.connection.commit()
    return redirect(url_for('departments'))

@app.route('/admin/departments/delete/<int:did>', methods=['POST'])
@super_admin_required
def delete_department(did):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE departments SET is_active=0 WHERE id=%s", (did,))
    mysql.connection.commit()
    flash('Department deleted.', 'success')
    return redirect(url_for('departments'))

@app.route('/admin/departments/routing', methods=['POST'])
@admin_required
def update_routing():
    cursor = mysql.connection.cursor()
    categories = ['academics','facilities','welfare','technology','administration','sports','other']
    for cat in categories:
        dept_id = request.form.get(f'route_{cat}','')
        cursor.execute("DELETE FROM category_departments WHERE category=%s", (cat,))
        if dept_id:
            cursor.execute("INSERT INTO category_departments (category, department_id) VALUES (%s,%s)",
                           (cat, dept_id))
    mysql.connection.commit()
    flash('Routing updated successfully!', 'success')
    return redirect(url_for('departments'))

# ─── PDF REPORT ──────────────────────────────────────────────────────────────
@app.route('/admin/pdf-report')
@admin_required
def pdf_report():
    cursor = mysql.connection.cursor()
    stats  = get_stats()
    cursor.execute("""
        SELECT s.*, u.fullname FROM suggestions s
        JOIN users u ON s.user_id=u.id
        ORDER BY s.created_at DESC
    """)
    suggestions = cursor.fetchall()
    cursor.execute("SELECT AVG(rating) as avg FROM satisfaction_ratings")
    avg_rating = float(cursor.fetchone()['avg'] or 0)
    cursor.execute("SELECT category, COUNT(*) as cnt FROM suggestions GROUP BY category ORDER BY cnt DESC")
    cat_stats = cursor.fetchall()
    cursor.execute("""
        SELECT MONTH(created_at) as month, COUNT(*) as cnt
        FROM suggestions WHERE YEAR(created_at)=YEAR(NOW())
        GROUP BY MONTH(created_at) ORDER BY month
    """)
    monthly_raw = cursor.fetchall()
    monthly = [0]*12
    for r in monthly_raw: monthly[r['month']-1] = r['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cursor.fetchone()['cnt']
    resolution_rate = round(stats['resolved'] / stats['total'] * 100) if stats['total'] > 0 else 0
    cursor.execute("""
        SELECT d.name,
               COUNT(s.id) as total,
               SUM(s.status='resolved') as resolved,
               SUM(s.status='pending') as pending
        FROM departments d
        LEFT JOIN suggestions s ON s.department_id = d.id
        WHERE d.is_active=1
        GROUP BY d.id
        HAVING total > 0
    """)
    dept_stats = cursor.fetchall()
    return render_template('admin/pdf_report.html',
                           stats=stats, suggestions=suggestions,
                           avg_rating=avg_rating, cat_stats=cat_stats,
                           monthly=monthly, total_users=total_users,
                           resolution_rate=resolution_rate, dept_stats=dept_stats,
                           generated_at=datetime.now().strftime('%B %d, %Y at %H:%M'))

# ─── AUTO-ASSIGN DEPARTMENT ON SUBMIT ────────────────────────────────────────
def auto_assign_department(suggestion_id, category):
    """Auto-assign department based on category routing."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""SELECT department_id FROM category_departments WHERE category=%s""", (category,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE suggestions SET department_id=%s WHERE id=%s",
                           (row['department_id'], suggestion_id))
            mysql.connection.commit()
    except Exception as e:
        print(f'Auto-assign dept error: {e}')


# ═══════════════════════════════════════════════════════════════════
# V7 — LEADERBOARD, SLA ALERTS, BULK EMAIL, WEEKLY AI SUMMARY
# ═══════════════════════════════════════════════════════════════════

# ─── STUDENT LEADERBOARD ─────────────────────────────────────────────────────
@app.route('/leaderboard')
@login_required
def leaderboard():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT u.id, u.fullname, u.role,
               COUNT(s.id) as total_suggestions,
               SUM(s.status='resolved') as resolved_count,
               SUM(s.vote_count) as total_votes,
               MAX(s.created_at) as last_submitted
        FROM users u
        LEFT JOIN suggestions s ON u.id = s.user_id
        GROUP BY u.id
        HAVING total_suggestions > 0
        ORDER BY total_suggestions DESC, total_votes DESC
        LIMIT 20
    """)
    leaders = cursor.fetchall()

    # Current user rank
    cursor.execute("""
        SELECT COUNT(*) + 1 as user_rank FROM (
            SELECT u.id, COUNT(s.id) as cnt
            FROM users u LEFT JOIN suggestions s ON u.id=s.user_id
            GROUP BY u.id HAVING cnt > (
                SELECT COUNT(*) FROM suggestions WHERE user_id=%s
            )
        ) t
    """, (session['user_id'],))
    my_rank = cursor.fetchone()['user_rank']

    return render_template('leaderboard.html', leaders=leaders, my_rank=my_rank)


# ─── SLA WARNING ALERTS API ──────────────────────────────────────────────────
@app.route('/admin/api/sla-alerts')
@admin_required
def sla_alerts():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.id, s.suggestion_id, s.title, s.priority,
               s.due_date, s.sla_status, u.fullname,
               TIMESTAMPDIFF(HOUR, NOW(), s.due_date) as hours_left
        FROM suggestions s
        JOIN users u ON s.user_id = u.id
        WHERE s.status NOT IN ('resolved','rejected')
        AND s.due_date IS NOT NULL
        AND s.due_date <= DATE_ADD(NOW(), INTERVAL 24 HOUR)
        ORDER BY s.due_date ASC
        LIMIT 10
    """)
    alerts = cursor.fetchall()
    result = []
    for a in alerts:
        result.append({
            'id': a['id'],
            'suggestion_id': a['suggestion_id'],
            'title': a['title'],
            'priority': a['priority'],
            'sla_status': a['sla_status'],
            'hours_left': a['hours_left'],
            'fullname': a['fullname']
        })
    return jsonify({'alerts': result, 'count': len(result)})


# ─── BULK EMAIL TO STUDENTS ──────────────────────────────────────────────────
@app.route('/admin/bulk-email', methods=['GET','POST'])
@super_admin_required
def bulk_email():
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        subject  = request.form.get('subject','').strip()
        message  = request.form.get('message','').strip()
        audience = request.form.get('audience','all')
        if not subject or not message:
            flash('Subject and message are required.', 'danger')
            return redirect(url_for('bulk_email'))

        # Get recipients
        if audience == 'students':
            cursor.execute("SELECT email, fullname FROM users WHERE role='student'")
        elif audience == 'active':
            cursor.execute("""
                SELECT DISTINCT u.email, u.fullname FROM users u
                JOIN suggestions s ON u.id=s.user_id
            """)
        else:
            cursor.execute("SELECT email, fullname FROM users")

        recipients = cursor.fetchall()
        sent = 0
        for r in recipients:
            try:
                send_notification(
                    r['email'], subject, message,
                    suggestion_title='', tracking_id='', status=''
                )
                sent += 1
            except:
                pass

        flash(f'Announcement sent to {sent} users successfully! 📧', 'success')
        return redirect(url_for('bulk_email'))

    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role='student'")
    total_students = cursor.fetchone()['cnt']
    cursor.execute("""
        SELECT COUNT(DISTINCT u.id) as cnt FROM users u
        JOIN suggestions s ON u.id=s.user_id
    """)
    active_users = cursor.fetchone()['cnt']

    return render_template('admin/bulk_email.html',
                           total_users=total_users,
                           total_students=total_students,
                           active_users=active_users)


# ─── AI WEEKLY SUMMARY EMAIL ─────────────────────────────────────────────────
@app.route('/admin/ai/weekly-summary', methods=['POST'])
@admin_required
def ai_weekly_summary():
    """Generate and send AI weekly summary to all admins."""
    cursor = mysql.connection.cursor()
    stats = get_stats()

    # Get this week's data
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM suggestions
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)
    new_this_week = cursor.fetchone()['cnt']

    cursor.execute("""
        SELECT COUNT(*) as cnt FROM suggestions
        WHERE status='resolved' AND updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)
    resolved_this_week = cursor.fetchone()['cnt']

    cursor.execute("""
        SELECT category, COUNT(*) as cnt FROM suggestions
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY category ORDER BY cnt DESC LIMIT 3
    """)
    top_categories = cursor.fetchall()

    cursor.execute("""
        SELECT s.title, s.vote_count, s.category FROM suggestions s
        WHERE s.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ORDER BY s.vote_count DESC LIMIT 3
    """)
    top_suggestions = cursor.fetchall()

    cat_text = ', '.join([f"{c['category']} ({c['cnt']})" for c in top_categories])
    sug_text = '\n'.join([f"- {s['title']} ({s['vote_count']} votes)" for s in top_suggestions])

    summary = claude_api(f"""
Generate a concise weekly summary report for school administrators.
Write in friendly, professional prose. Keep it under 200 words.

This week's stats:
- New suggestions: {new_this_week}
- Resolved this week: {resolved_this_week}
- Total pending: {stats['pending']}
- Top categories: {cat_text}
- Top voted suggestions this week:
{sug_text}

Include: what went well, what needs attention, and one actionable recommendation.
""", "You are a helpful school administration assistant.")

    if not summary:
        return jsonify({'error': 'Could not generate summary'})

    # Send to all admins
    cursor.execute("SELECT username, email FROM admins WHERE is_active=1 AND email IS NOT NULL AND email != ''")
    admins = cursor.fetchall()
    sent = 0
    for admin in admins:
        try:
            send_notification(
                admin['email'],
                f'VoiceUp Weekly Summary — {datetime.now().strftime("%B %d, %Y")}',
                summary.replace('\n', '<br>'),
                suggestion_title='', tracking_id='', status=''
            )
            sent += 1
        except:
            pass

    return jsonify({
        'summary': summary,
        'sent_to': sent,
        'message': f'Weekly summary sent to {sent} admin(s)!'
    })


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080)
