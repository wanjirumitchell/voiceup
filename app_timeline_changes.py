# ═══════════════════════════════════════════════════════════════════
# TIMELINE FEATURE — CHANGES TO ADD TO YOUR app.py
# ═══════════════════════════════════════════════════════════════════
# 
# STEP 1: Add this helper function near your other helpers (after get_stats)
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: In your submit_suggestion() route, after mysql.connection.commit()
# where new_id is set, ADD this line to log the submission event:
#
#   log_timeline(new_id, 'submitted', new_value='pending',
#                actor_name=session['user_name'], actor_type='user')
#
# It should look like this after your INSERT:
#
#   mysql.connection.commit()
#   new_id = cursor.lastrowid
#   log_timeline(new_id, 'submitted', new_value='pending',
#                actor_name=session['user_name'], actor_type='user')
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: In admin_suggestion_detail(), find the update_status block and
# REPLACE it with this version that logs the timeline:
# ─────────────────────────────────────────────────────────────────────────────

        if action == 'update_status':
            new_status = request.form.get('status')
            old_status = suggestion['status']
            cursor.execute("UPDATE suggestions SET status=%s, updated_at=NOW() WHERE id=%s",
                           (new_status, sid))
            mysql.connection.commit()
            # Log to timeline
            log_timeline(sid, 'status_changed',
                         old_value=old_status, new_value=new_status,
                         actor_name=session['admin_name'], actor_type='admin')
            # Email notification
            if new_status in ('under_review', 'resolved', 'rejected'):
                labels = {'under_review': 'Under Review', 'resolved': 'Resolved', 'rejected': 'Rejected'}
                send_notification(
                    suggestion['email'],
                    f'Your suggestion status changed to {labels.get(new_status, new_status)}',
                    f'<p>Your suggestion <strong>{suggestion["title"]}</strong> is now <strong>{labels.get(new_status)}</strong>.</p>'
                )
            flash('Status updated.', 'success')


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: In admin_suggestion_detail(), find the add_response block and
# REPLACE it with this version:
# ─────────────────────────────────────────────────────────────────────────────

        elif action == 'add_response':
            text = request.form.get('response_text', '').strip()
            if text:
                cursor.execute(
                    "INSERT INTO admin_responses (suggestion_id,admin_id,response_text,created_at) VALUES (%s,%s,%s,NOW())",
                    (sid, session['admin_id'], text)
                )
                mysql.connection.commit()
                # Log to timeline
                log_timeline(sid, 'response_added',
                             actor_name=session['admin_name'], actor_type='admin',
                             note=text[:100] + '...' if len(text) > 100 else text)
                send_notification(suggestion['email'], 'New response on your suggestion',
                    f'<p>An admin has responded to <strong>{suggestion["title"]}</strong>.</p><p>{text}</p>')
                flash('Response added.', 'success')
            else:
                flash('Response cannot be empty.', 'danger')


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: In admin_suggestion_detail(), find the assign block and
# REPLACE it with this version:
# ─────────────────────────────────────────────────────────────────────────────

        elif action == 'assign':
            assigned_to = request.form.get('assigned_to')
            cursor.execute(
                "UPDATE suggestions SET assigned_to=%s, assigned_at=NOW() WHERE id=%s",
                (assigned_to or None, sid)
            )
            mysql.connection.commit()
            # Get assigned admin name for timeline
            if assigned_to:
                cursor.execute("SELECT username FROM admins WHERE id=%s", (assigned_to,))
                assigned_admin = cursor.fetchone()
                assigned_name = assigned_admin['username'] if assigned_admin else 'Admin'
                log_timeline(sid, 'assigned', new_value=assigned_name,
                             actor_name=session['admin_name'], actor_type='admin')
            flash('Suggestion assigned.', 'success')


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: In your suggestion_detail() route (user view), ADD the timeline
# query before the return render_template line:
# ─────────────────────────────────────────────────────────────────────────────

    cursor.execute("""
        SELECT * FROM suggestion_timeline
        WHERE suggestion_id=%s ORDER BY created_at ASC
    """, (suggestion['id'],))
    timeline = cursor.fetchall()

    return render_template('suggestion_detail.html', suggestion=suggestion,
                           responses=responses, attachments=attachments,
                           rating=rating, user_voted=user_voted,
                           timeline=timeline)   # <-- add timeline=timeline here


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: Also add timeline to admin_suggestion_detail() view, before its
# return render_template line:
# ─────────────────────────────────────────────────────────────────────────────

    cursor.execute("""
        SELECT * FROM suggestion_timeline
        WHERE suggestion_id=%s ORDER BY created_at ASC
    """, (sid,))
    timeline = cursor.fetchall()

    return render_template('admin/suggestion_detail.html', suggestion=suggestion,
                           responses=responses, notes=notes, attachments=attachments,
                           rating=rating, admins=admins, comments=comments,
                           timeline=timeline,   # <-- add this
                           sla_status=get_sla_status(suggestion.get('due_date')))
