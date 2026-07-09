"""TamilAI - Notes routes"""

from flask import Blueprint, request, jsonify, g
from database.db import get_db
from utils.jwt_helper import jwt_required
from services.rag_services import generate_notes_from_book
import os
import json

notes_bp = Blueprint('notes', __name__)


@notes_bp.post('/generate')
def generate():

    data = request.get_json(silent=True) or {}

    topic = (data.get('topic') or '').strip()
    subject = (data.get('subject') or 'General').strip()

    if not topic:
        return jsonify({
            "error": "Topic is required"
        }), 400

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

        if not files:
            return jsonify({
                "error": "No textbook uploaded."
            }), 400

        latest = max(
            files,
            key=lambda x: os.path.getctime(
                os.path.join(index_folder, x)
            )
        )

        index_path = os.path.join(index_folder, latest)

        note_data = generate_notes_from_book(
            index_path,
            topic
        )
        
        # Convert RAG response to frontend format
        if "summary" in note_data:
            note_data = {
                "title": topic,
                "type": "summary",
                "subject": subject,
                "content": note_data.get("summary", ""),
                "key_terms": [],
                "important_formulas": [],
                "exam_tips": "",
                "sources": note_data.get("sources", [])
            }

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    note_id = None

    if user_id:

        db = get_db()

        try:

            cur = db.execute(
                """
                INSERT INTO notes
                (user_id, title, subject, topic, content)
                VALUES (?,?,?,?,?)
                """,
                (
                    user_id,
                    note_data.get("title", topic),
                    subject,
                    topic,
                    json.dumps(note_data)
                )
            )

            db.commit()

            note_id = cur.lastrowid

        finally:
            db.close()

    return jsonify({
        "note_id": note_id,
        "note": note_data
    })


@notes_bp.get("/my")
@jwt_required
def my_notes():

    db = get_db()

    try:

        rows = db.execute(
            """
            SELECT id,title,subject,topic,created_at
            FROM notes
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 30
            """,
            (g.user_id,)
        ).fetchall()

        return jsonify([dict(r) for r in rows])

    finally:
        db.close()


@notes_bp.get("/<int:note_id>")
@jwt_required
def get_note(note_id):

    db = get_db()

    try:

        row = db.execute(
            "SELECT * FROM notes WHERE id=? AND user_id=?",
            (note_id, g.user_id)
        ).fetchone()

        if not row:
            return jsonify({
                "error": "Note not found"
            }), 404

        data = dict(row)
        data["content"] = json.loads(data["content"])

        return jsonify(data)

    finally:
        db.close()


@notes_bp.delete("/<int:note_id>")
@jwt_required
def delete_note(note_id):

    db = get_db()

    try:

        db.execute(
            "DELETE FROM notes WHERE id=? AND user_id=?",
            (note_id, g.user_id)
        )

        db.commit()

        return jsonify({
            "message": "Note deleted"
        })

    finally:
        db.close()