"""
TamilAI - Chat routes (AI Tutor)
POST /api/chat/ask
GET  /api/chat/history
GET  /api/chat/sessions
GET  /api/chat/session/<session_id>
POST /api/chat/like/<chat_id>
"""

import os
import uuid

from flask import Blueprint, request, jsonify, g
from database.db import get_db
from utils.jwt_helper import jwt_required
from services.gemini_service import get_tamil_tutor_response
from services.rag_services import rag_query

chat_bp = Blueprint('chat', __name__)


@chat_bp.post('/ask')
def ask():

    data = request.get_json(silent=True) or {}

    message = (data.get('message') or '').strip()
    subject = (data.get('subject') or 'General').strip()
    session_id = data.get('session_id') or str(uuid.uuid4())
    history = data.get('history', [])

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    user_id = None

    auth = request.headers.get("Authorization", "")

    if auth.startswith("Bearer "):
        from utils.jwt_helper import decode_token

        try:
            payload = decode_token(auth.split(" ", 1)[1])
            user_id = payload["sub"]
        except Exception:
            pass

    try:

        index_folder = os.path.join(
            os.path.dirname(__file__),
            "..",
            "faiss_indexes"
        )

        files = [
            f for f in os.listdir(index_folder)
            if f.endswith(".pkl")
        ]

        if files:

            latest = max(
                files,
                key=lambda x: os.path.getctime(
                    os.path.join(index_folder, x)
                )
            )

            index_path = os.path.join(index_folder, latest)

            response_text, sources = rag_query(
                message,
                index_path
            )

            related_topics = []

        else:

            response_text, related_topics = get_tamil_tutor_response(
                message=message,
                subject=subject,
                history=history
            )

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    if user_id:

        db = get_db()

        try:

            db.execute(
                'INSERT INTO chats (user_id, session_id, role, content, subject) VALUES (?,?,?,?,?)',
                (user_id, session_id, 'user', message, subject)
            )

            db.execute(
                'INSERT INTO chats (user_id, session_id, role, content, subject) VALUES (?,?,?,?,?)',
                (user_id, session_id, 'assistant', response_text, subject)
            )

            db.execute(
                'UPDATE users SET xp = xp + 10 WHERE id = ?',
                (user_id,)
            )

            db.commit()

        finally:
            db.close()

    return jsonify({
        'response': response_text,
        'related_topics': related_topics,
        'session_id': session_id,
        'xp_awarded': 10 if user_id else 0,
    })


@chat_bp.get('/history')
@jwt_required
def history():

    limit = int(request.args.get('limit', 50))

    db = get_db()

    try:

        rows = db.execute(
            'SELECT session_id, role, content, subject, created_at FROM chats WHERE user_id=? ORDER BY created_at DESC LIMIT ?',
            (g.user_id, limit)
        ).fetchall()

        return jsonify([dict(r) for r in rows])

    finally:
        db.close()


@chat_bp.get('/sessions')
@jwt_required
def sessions():

    db = get_db()

    try:

        rows = db.execute(
            '''
            SELECT
                session_id,
                MIN(created_at) AS started_at,
                COUNT(*) AS message_count,
                MAX(subject) AS subject,
                (
                    SELECT content
                    FROM chats c2
                    WHERE c2.session_id = c.session_id
                    AND c2.role='user'
                    ORDER BY c2.created_at
                    LIMIT 1
                ) AS first_message
            FROM chats c
            WHERE user_id=?
            GROUP BY session_id
            ORDER BY started_at DESC
            LIMIT 20
            ''',
            (g.user_id,)
        ).fetchall()

        return jsonify([dict(r) for r in rows])

    finally:
        db.close()


@chat_bp.get('/session/<session_id>')
@jwt_required
def session_messages(session_id):

    db = get_db()

    try:

        rows = db.execute(
            '''
            SELECT
                role,
                content,
                subject,
                created_at,
                liked
            FROM chats
            WHERE user_id=?
            AND session_id=?
            ORDER BY created_at
            ''',
            (g.user_id, session_id)
        ).fetchall()

        return jsonify([dict(r) for r in rows])

    finally:
        db.close()


@chat_bp.post('/like/<int:chat_id>')
@jwt_required
def like_message(chat_id):

    data = request.get_json(silent=True) or {}

    liked = 1 if data.get('liked') else -1

    db = get_db()

    try:

        db.execute(
            'UPDATE chats SET liked=? WHERE id=? AND user_id=?',
            (liked, chat_id, g.user_id)
        )

        db.commit()

        return jsonify({
            'message': 'Updated'
        })

    finally:
        db.close()