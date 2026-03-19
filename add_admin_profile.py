with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

admin_profile_routes = '''
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

'''

content = content.replace(
    "if __name__ == '__main__':",
    admin_profile_routes + "if __name__ == '__main__':"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Admin profile routes added.")
