with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add realtime routes before the if __name__ block
realtime_routes = '''
# ═══════════════════════════════════════════════════════════════════
# REAL-TIME API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/suggestion-status/<suggestion_id>')
@login_required
def api_suggestion_status(suggestion_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT status, updated_at FROM suggestions WHERE suggestion_id=%s AND user_id=%s",
                   (suggestion_id, session['user_id']))
    s = cursor.fetchone()
    if s:
        return jsonify({'status': s['status'],
                       'updated_at': str(s['updated_at']) if s['updated_at'] else ''})
    return jsonify({'status': 'unknown'})

@app.route('/api/vote-counts')
def api_vote_counts():
    ids = request.args.get('ids', '').split(',')
    ids = [i.strip() for i in ids if i.strip()]
    if not ids:
        return jsonify({'counts': []})
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT id, vote_count FROM suggestions WHERE id IN (%s)" % ','.join(['%s']*len(ids)),
        ids
    )
    rows = cursor.fetchall()
    return jsonify({'counts': [{'id': r['id'], 'count': r['vote_count']} for r in rows]})

@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) as total, SUM(status='pending') as pending,
               SUM(status='under_review') as under_review, SUM(status='resolved') as resolved
        FROM suggestions WHERE user_id=%s
    """, (session['user_id'],))
    stats = cursor.fetchone()
    return jsonify(stats)

'''

content = content.replace(
    "if __name__ == '__main__':",
    realtime_routes + "if __name__ == '__main__':"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Real-time routes added to app.py")
