with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

v6_routes = '''
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

'''

content = content.replace(
    "if __name__ == '__main__':",
    v6_routes + "if __name__ == '__main__':"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! V6 routes added to app.py")
