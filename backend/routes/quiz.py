"""TamilAI - Quiz routes"""
from flask import Blueprint, request, jsonify, g
from database.db import get_db
from utils.jwt_helper import jwt_required
from services.gemini_service import generate_quiz
import json

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.post('/generate')
def generate():
    data = request.get_json(silent=True) or {}
    topic      = (data.get('topic') or '').strip()
    subject    = (data.get('subject') or 'General').strip()
    num_q      = min(int(data.get('num_questions', 5)), 20)
    difficulty = data.get('difficulty', 'medium')
    quiz_type  = data.get('quiz_type', 'mcq')
    context    = data.get('context', '')
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    user_id = None
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        from utils.jwt_helper import decode_token
        try:
            payload = decode_token(auth.split(' ', 1)[1])
            user_id = payload['sub']
        except Exception:
            pass

    try:
        questions = generate_quiz(topic=topic, subject=subject, num_questions=num_q,
                                  difficulty=difficulty, quiz_type=quiz_type, context=context)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 502

    quiz_id = None
    if user_id:
        db = get_db()
        try:
            cur = db.execute(
                'INSERT INTO quizzes (user_id, title, subject, topic, difficulty, questions) VALUES (?,?,?,?,?,?)',
                (user_id, f'{topic} Quiz', subject, topic, difficulty, json.dumps(questions))
            )
            db.commit()
            quiz_id = cur.lastrowid
        finally:
            db.close()

    return jsonify({'quiz_id': quiz_id, 'topic': topic, 'subject': subject,
                    'questions': questions, 'total': len(questions)})


@quiz_bp.post('/submit')
@jwt_required
def submit():
    data = request.get_json(silent=True) or {}
    quiz_id    = data.get('quiz_id')
    answers    = data.get('answers', [])
    time_taken = data.get('time_taken', 0)
    if not quiz_id or not answers:
        return jsonify({'error': 'quiz_id and answers required'}), 400

    db = get_db()
    try:
        quiz_row = db.execute('SELECT * FROM quizzes WHERE id=? AND user_id=?', (quiz_id, g.user_id)).fetchone()
        if not quiz_row:
            return jsonify({'error': 'Quiz not found'}), 404
        questions = json.loads(quiz_row['questions'])
        score, results = 0, []
        for q in questions:
            user_ans = next((a for a in answers if a.get('question_id') == q['id']), None)
            selected = user_ans.get('selected_index', -1) if user_ans else -1
            correct  = q.get('correct_index', 0)
            is_right = selected == correct
            if is_right: score += 1
            results.append({'question_id': q['id'], 'question': q['question'], 'selected': selected,
                            'correct': correct, 'correct_answer': q.get('correct',''),
                            'is_correct': is_right, 'explanation': q.get('explanation','')})
        total   = len(questions)
        pct     = round((score / total) * 100) if total else 0
        xp_gain = score * 10
        db.execute('INSERT INTO quiz_results (user_id, quiz_id, score, total, answers, time_taken) VALUES (?,?,?,?,?,?)',
                   (g.user_id, quiz_id, score, total, json.dumps(results), time_taken))
        db.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (xp_gain, g.user_id))
        db.commit()
        grade_pct = pct
        if grade_pct >= 90: grade = {'label':'Excellent! 🏆','color':'#10B981'}
        elif grade_pct >= 75: grade = {'label':'Good Job! 🎉','color':'#3B82F6'}
        elif grade_pct >= 50: grade = {'label':'Keep Going 💪','color':'#F59E0B'}
        else: grade = {'label':'Needs Practice 📚','color':'#EF4444'}
        return jsonify({'score':score,'total':total,'percentage':pct,'xp_gained':xp_gain,'results':results,'grade':grade})
    finally:
        db.close()


@quiz_bp.get('/history')
@jwt_required
def history():
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT qr.id, qr.score, qr.total, qr.time_taken, qr.completed_at,
                      q.title, q.subject, q.topic, q.difficulty
               FROM quiz_results qr JOIN quizzes q ON qr.quiz_id = q.id
               WHERE qr.user_id=? ORDER BY qr.completed_at DESC LIMIT 30''', (g.user_id,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        db.close()


@quiz_bp.get('/<int:quiz_id>')
@jwt_required
def get_quiz(quiz_id):
    db = get_db()
    try:
        row = db.execute('SELECT * FROM quizzes WHERE id=? AND user_id=?', (quiz_id, g.user_id)).fetchone()
        if not row: return jsonify({'error': 'Quiz not found'}), 404
        d = dict(row); d['questions'] = json.loads(d['questions'])
        return jsonify(d)
    finally:
        db.close()
