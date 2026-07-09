"""
TamilAI - JWT authentication utilities
"""

import jwt
import datetime
import os
from functools import wraps
from flask import request, jsonify, current_app


SECRET = os.getenv('SECRET_KEY', 'tamilai-secret-change-in-production')


def generate_token(user_id: int, role: str) -> str:
    payload = {
        'sub': user_id,
        'role': role,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET, algorithm='HS256')


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=['HS256'])


def jwt_required(f):
    """Decorator: protect a route — injects g.user_id and g.role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import g
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Authorization header missing'}), 401
        token = auth.split(' ', 1)[1]
        try:
            payload = decode_token(token)
            g.user_id = payload['sub']
            g.role    = payload['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired — please log in again'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated
