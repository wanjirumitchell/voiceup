with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_routes = '''
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

# ─── SMS NOTIFICATIONS (Africa\'s Talking) ───────────────────────────────────
AT_USERNAME = ''   # Your Africa\'s Talking username
AT_API_KEY  = ''   # Your Africa\'s Talking API key
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
        print(f\'SMS error: {e}\')

# ─── PROFILE ─────────────────────────────────────────────────────────────────
@app.route(\'/profile\', methods=[\'GET\', \'POST\'])
@login_required
def profile():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id=%s", (session[\'user_id\'],))
    user = cursor.fetchone()

    if request.method == \'POST\':
        fullname   = request.form.get(\'fullname\', \'\').strip()
        student_id = request.form.get(\'student_id\', \'\').strip()
        phone      = request.form.get(\'phone\', \'\').strip()
        department = request.form.get(\'department\', \'\').strip()
        bio        = request.form.get(\'bio\', \'\').strip()

        # Handle photo upload
        photo_filename = user[\'profile_photo\']
        photo = request.files.get(\'profile_photo\')
        if photo and photo.filename and allowed_file(photo.filename):
            safe   = secure_filename(photo.filename)
            unique = f"profile_{session[\'user_id\']}_{int(datetime.now().timestamp())}_{safe}"
            path   = os.path.join(app.config[\'UPLOAD_FOLDER\'], unique)
            photo.save(path)
            photo_filename = unique

        cursor.execute("""
            UPDATE users SET fullname=%s, student_id=%s, phone=%s,
            department=%s, bio=%s, profile_photo=%s WHERE id=%s
        """, (fullname, student_id or None, phone or None,
              department or None, bio or None, photo_filename, session[\'user_id\']))
        mysql.connection.commit()
        session[\'user_name\'] = fullname
        flash(\'Profile updated successfully!\', \'success\')
        return redirect(url_for(\'profile\'))

    cursor.execute("""
        SELECT COUNT(*) as total, SUM(status=\'pending\') as pending,
               SUM(status=\'resolved\') as resolved
        FROM suggestions WHERE user_id=%s
    """, (session[\'user_id\'],))
    stats = cursor.fetchone()
    return render_template(\'profile.html\', user=user, stats=stats)


@app.route(\'/change-password\', methods=[\'POST\'])
@login_required
def change_password():
    current  = request.form.get(\'current_password\', \'\')
    new_pass = request.form.get(\'new_password\', \'\')
    confirm  = request.form.get(\'confirm_password\', \'\')
    cursor   = mysql.connection.cursor()
    cursor.execute("SELECT password FROM users WHERE id=%s", (session[\'user_id\'],))
    user = cursor.fetchone()
    if user[\'password\'] != hash_password(current):
        flash(\'Current password is incorrect.\', \'danger\')
    elif len(new_pass) < 8:
        flash(\'New password must be at least 8 characters.\', \'danger\')
    elif new_pass != confirm:
        flash(\'Passwords do not match.\', \'danger\')
    else:
        cursor.execute("UPDATE users SET password=%s WHERE id=%s",
                       (hash_password(new_pass), session[\'user_id\']))
        mysql.connection.commit()
        flash(\'Password updated successfully!\', \'success\')
    return redirect(url_for(\'profile\'))

# ─── LOGIN WITH STUDENT ID ───────────────────────────────────────────────────
@app.route(\'/login-student\', methods=[\'GET\', \'POST\'])
def student_login():
    if \'user_id\' in session:
        return redirect(url_for(\'dashboard\'))
    if request.method == \'POST\':
        student_id = request.form.get(\'student_id\', \'\').strip()
        password   = request.form.get(\'password\', \'\')
        cursor     = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE student_id=%s AND password=%s",
                       (student_id, hash_password(password)))
        user = cursor.fetchone()
        if user:
            session.update({\'user_id\': user[\'id\'], \'user_name\': user[\'fullname\'],
                            \'user_role\': user[\'role\'], \'user_email\': user[\'email\']})
            flash(f\'Welcome back, {user["fullname"]}!\', \'success\')
            return redirect(url_for(\'dashboard\'))
        flash(\'Invalid Student ID or password.\', \'danger\')
    return render_template(\'login_student.html\')

# ─── SUGGESTION TEMPLATES ────────────────────────────────────────────────────
@app.route(\'/templates\')
@login_required
def suggestion_templates():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM suggestion_templates WHERE is_active=1 ORDER BY use_count DESC")
    templates = cursor.fetchall()
    return render_template(\'templates.html\',
                           templates=templates,
                           templates_json=_json.dumps([dict(t) for t in templates], default=str))

@app.route(\'/api/template/<int:tid>\')
@login_required
def get_template(tid):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM suggestion_templates WHERE id=%s", (tid,))
    t = cursor.fetchone()
    if t:
        cursor.execute("UPDATE suggestion_templates SET use_count=use_count+1 WHERE id=%s", (tid,))
        mysql.connection.commit()
        return jsonify(dict(t))
    return jsonify({\'error\': \'Not found\'})

# ─── BULK STATUS UPDATE ──────────────────────────────────────────────────────
@app.route(\'/admin/bulk-update\', methods=[\'GET\', \'POST\'])
@admin_required
def admin_bulk_update():
    cursor = mysql.connection.cursor()
    if request.method == \'POST\':
        ids        = request.form.getlist(\'suggestion_ids\')
        new_status = request.form.get(\'new_status\', \'\')
        if ids and new_status:
            placeholders = \',\'.join([\'%s\'] * len(ids))
            cursor.execute(
                f"UPDATE suggestions SET status=%s, updated_at=NOW() WHERE id IN ({placeholders})",
                [new_status] + ids
            )
            mysql.connection.commit()
            flash(f\'Updated {len(ids)} suggestions to {new_status.replace("_"," ").title()}.\', \'success\')
        return redirect(url_for(\'admin_dashboard\'))

    cursor.execute("""
        SELECT s.*, u.fullname FROM suggestions s
        JOIN users u ON s.user_id=u.id
        ORDER BY s.created_at DESC
    """)
    suggestions = cursor.fetchall()
    return render_template(\'admin/bulk_update.html\', suggestions=suggestions)

# ─── PROFILE CSS ADDITIONS ───────────────────────────────────────────────────
# Add profile styles to CSS (already in style.css additions below)

'''

content = content.replace(
    "if __name__ == '__main__':",
    new_routes + "if __name__ == '__main__':"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! V5 routes added to app.py")
