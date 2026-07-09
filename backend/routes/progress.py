"""TamilAI - Progress routes"""
from flask import Blueprint, request, jsonify, g
from database.db import get_db
from utils.jwt_helper import jwt_required
import json, datetime

progress_bp = Blueprint('progress', __name__)

@progress_bp.get('/summary')
@jwt_required
def summary():
    db = get_db()
    try:
        user = db.execute('SELECT xp, coins, streak FROM users WHERE id=?', (g.user_id,)).fetchone()
        quiz_stats = db.execute(
            'SELECT COUNT(*) as total, SUM(score) as scored, SUM(total) as possible FROM quiz_results WHERE user_id=?',
            (g.user_id,)
        ).fetchone()
        chat_count = db.execute('SELECT COUNT(*) as c FROM chats WHERE user_id=? AND role="user"', (g.user_id,)).fetchone()
        return jsonify({
            'xp': user['xp'], 'coins': user['coins'], 'streak': user['streak'],
            'quiz_count': quiz_stats['total'] or 0,
            'accuracy': round((quiz_stats['scored'] or 0) / max(quiz_stats['possible'] or 1, 1) * 100),
            'questions_asked': chat_count['c'] or 0,
        })
    finally:
        db.close()

@progress_bp.post('/log')
@jwt_required
def log_progress():
    data    = request.get_json(silent=True) or {}
    subject = (data.get('subject') or 'General').strip()
    minutes = int(data.get('minutes', 0))
    topics  = data.get('topics', [])
    today   = datetime.date.today().isoformat()
    db = get_db()
    try:
        db.execute(
            '''INSERT INTO progress (user_id, date, subject, minutes, topics, xp_earned)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(user_id, date, subject) DO UPDATE SET
               minutes = minutes + excluded.minutes,
               xp_earned = xp_earned + excluded.xp_earned''',
            (g.user_id, today, subject, minutes, json.dumps(topics), minutes // 5)
        )
        db.commit()
        return jsonify({'message': 'Progress logged'})
    finally:
        db.close()

@progress_bp.get('/weekly')
@jwt_required
def weekly():
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT date, subject, SUM(minutes) as minutes FROM progress
               WHERE user_id=? AND date >= date('now', '-7 days')
               GROUP BY date, subject ORDER BY date''',
            (g.user_id,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        db.close()
