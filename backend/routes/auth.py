"""
TamilAI - Authentication routes
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
"""

from flask import Blueprint, request, jsonify, g
from database.db import get_db
from utils.jwt_helper import generate_token, jwt_required
import bcrypt
import re

auth_bp = Blueprint('auth', __name__)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _validate_email(email: str) -> bool:
    return bool(re.match(r'^[\w.+-]+@[\w-]+\.[a-z]{2,}$', email, re.I))


# ─── Register ─────────────────────────────────────────────────
@auth_bp.post('/register')
def register():
    data = request.get_json(silent=True) or {}
    name        = (data.get('name')        or '').strip()
    email       = (data.get('email')       or '').strip().lower()
    password    = (data.get('password')    or '')
    role        = (data.get('role')        or 'student')
    class_grade = (data.get('class_grade') or '').strip()
    school      = (data.get('school')      or '').strip()

    # Validation
    errors = {}
    if not name:
        errors['name'] = 'Name is required'
    if not _validate_email(email):
        errors['email'] = 'Enter a valid email address'
    if len(password) < 6:
        errors['password'] = 'Password must be at least 6 characters'
    if role not in ('student', 'teacher', 'parent'):
        errors['role'] = 'Invalid role'
    if errors:
        return jsonify({'errors': errors}), 422

    db = get_db()
    try:
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            return jsonify({'errors': {'email': 'This email is already registered'}}), 409

        cur = db.execute(
            '''INSERT INTO users (name, email, password, role, class_grade, school)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (name, email, _hash(password), role, class_grade, school)
        )
        db.commit()
        user_id = cur.lastrowid
        token = generate_token(user_id, role)

        return jsonify({
            'token': token,
            'user': {
                'id':          user_id,
                'name':        name,
                'email':       email,
                'role':        role,
                'class_grade': class_grade,
                'school':      school,
                'xp':          0,
                'coins':       0,
                'streak':      0,
            }
        }), 201

    finally:
        db.close()


# ─── Login ────────────────────────────────────────────────────
@auth_bp.post('/login')
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '')

    if not email or not password:
        return jsonify({'errors': {'general': 'Email and password are required'}}), 422

    db = get_db()
    try:
        row = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not row or not _verify(password, row['password']):
            return jsonify({'errors': {'general': 'Invalid email or password'}}), 401

        # Update last_active
        db.execute('UPDATE users SET last_active = DATE("now") WHERE id = ?', (row['id'],))
        db.commit()

        token = generate_token(row['id'], row['role'])
        return jsonify({
            'token': token,
            'user': {
                'id':          row['id'],
                'name':        row['name'],
                'email':       row['email'],
                'role':        row['role'],
                'class_grade': row['class_grade'],
                'school':      row['school'],
                'xp':          row['xp'],
                'coins':       row['coins'],
                'streak':      row['streak'],
                'avatar':      row['avatar'],
            }
        })
    finally:
        db.close()


# ─── Me (get current user) ────────────────────────────────────
@auth_bp.get('/me')
@jwt_required
def me():
    db = get_db()
    try:
        row = db.execute('SELECT * FROM users WHERE id = ?', (g.user_id,)).fetchone()
        if not row:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({
            'id':          row['id'],
            'name':        row['name'],
            'email':       row['email'],
            'role':        row['role'],
            'class_grade': row['class_grade'],
            'school':      row['school'],
            'xp':          row['xp'],
            'coins':       row['coins'],
            'streak':      row['streak'],
            'avatar':      row['avatar'],
        })
    finally:
        db.close()


# ─── Update profile ───────────────────────────────────────────
@auth_bp.put('/profile')
@jwt_required
def update_profile():
    data = request.get_json(silent=True) or {}
    allowed = ('name', 'class_grade', 'school', 'avatar')
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}

    if not updates:
        return jsonify({'error': 'Nothing to update'}), 400

    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values     = list(updates.values()) + [g.user_id]

    db = get_db()
    try:
        db.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
        db.commit()
        return jsonify({'message': 'Profile updated'})
    finally:
        db.close()
