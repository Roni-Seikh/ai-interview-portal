from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from app import db, limiter
from app.models import User, OTPToken
from app.utils.validators import validate_password, validate_email
from app.utils.security import hash_password, check_password
from datetime import datetime, timedelta
import traceback, os, secrets

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("10 per minute")
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    full_name        = data.get('full_name', '').strip()
    email            = data.get('email', '').strip().lower()
    password         = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    errors = {}
    if not full_name or len(full_name) < 2:
        errors['full_name'] = 'Minimum 2 characters'
    if not validate_email(email):
        errors['email'] = 'Invalid email address'
    if not validate_password(password):
        errors['password'] = '8+ chars, uppercase, lowercase, number & special char'
    if password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match'
    if errors:
        return jsonify({'message': 'Validation failed', 'errors': errors}), 422

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({
            'message': 'Email already registered. Please login instead.',
            'errors': {'email': 'Already in use'}
        }), 409

    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role='student',
        is_active=True,
        is_verified=True,
    )
    db.session.add(user)
    db.session.commit()

    access_token  = create_access_token(
        identity=str(user.id), expires_delta=timedelta(hours=2))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'message': 'Account created successfully! Welcome to InterviewAI.',
        'user_id': user.id,
        'auto_login': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
    }), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("20 per minute")
def login():
    data     = request.get_json() or {}
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = data.get('remember_me', False)

    user = User.query.filter_by(email=email).first()
    if not user or not check_password(password, user.password_hash):
        return jsonify({'message': 'Invalid email or password'}), 401
    if not user.is_active:
        return jsonify({'message': 'Account deactivated. Contact support.'}), 403

    # Auto-fix any stuck unverified accounts
    if not user.is_verified:
        user.is_verified = True

    user.last_login = datetime.utcnow()
    db.session.commit()

    expires = timedelta(days=30) if remember else timedelta(hours=2)
    return jsonify({
        'message': 'Login successful',
        'access_token':  create_access_token(
            identity=str(user.id), expires_delta=expires),
        'refresh_token': create_refresh_token(identity=str(user.id)),
        'user': user.to_dict(),
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    return jsonify({
        'access_token': create_access_token(identity=get_jwt_identity())
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("10 per minute")
def forgot_password():
    """
    No email sent. Returns reset_token directly if email exists.
    """
    try:
        data  = request.get_json() or {}
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({'message': 'Email is required', 'found': False}), 400

        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({
                'message': 'No account found with this email address.',
                'found': False
            }), 200

        # Delete old tokens
        OTPToken.query.filter_by(
            user_id=user.id,
            token_type='password_reset',
            is_used=False
        ).delete()
        db.session.flush()

        # Generate secure token
        reset_token = secrets.token_urlsafe(32)

        db.session.add(OTPToken(
            user_id=user.id,
            token=reset_token,
            token_type='password_reset',
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        ))
        db.session.commit()

        current_app.logger.info(
            f"Password reset token generated for user {user.id} ({email})"
        )

        return jsonify({
            'message': 'Email found. You can now reset your password.',
            'found': True,
            'reset_token': reset_token,
            'user_id': user.id,
        }), 200

    except Exception:
        current_app.logger.error(
            f"forgot_password error:\n{traceback.format_exc()}"
        )
        db.session.rollback()
        return jsonify({'message': 'Server error. Please try again.', 'found': False}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data         = request.get_json() or {}
        user_id      = data.get('user_id')
        reset_token  = data.get('reset_token', '').strip()
        new_password = data.get('new_password', '')

        if not user_id or not reset_token:
            return jsonify({
                'message': 'Invalid request — missing user_id or reset_token'
            }), 400

        if not validate_password(new_password):
            return jsonify({
                'message': 'Password needs 8+ chars, uppercase, lowercase, number & special char (!@#$%^&*)'
            }), 422

        token = OTPToken.query.filter_by(
            user_id=user_id,
            token=reset_token,
            token_type='password_reset',
            is_used=False,
        ).first()

        if not token:
            return jsonify({'message': 'Invalid reset token. Please start again.'}), 400

        if token.expires_at < datetime.utcnow():
            return jsonify({'message': 'Reset token expired. Please start again.'}), 400

        token.is_used = True
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        user.password_hash = hash_password(new_password)
        db.session.commit()

        current_app.logger.info(f"Password reset successful for user {user_id}")
        return jsonify({'message': 'Password reset successfully! You can now login.'}), 200

    except Exception:
        current_app.logger.error(
            f"reset_password error:\n{traceback.format_exc()}"
        )
        db.session.rollback()
        return jsonify({'message': 'Server error. Please try again.'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user = User.query.get(get_jwt_identity())
    data = request.get_json() or {}
    if data.get('full_name'):
        user.full_name = data['full_name'].strip()
    if data.get('phone'):
        user.phone = data['phone'].strip()
    db.session.commit()
    return jsonify({'message': 'Profile updated', 'user': user.to_dict()}), 200


@auth_bp.route('/test-email', methods=['GET'])
def test_email():
    return jsonify({
        'status': 'Email verification disabled',
        'message': 'Registration is instant. Password reset uses secure tokens.',
    }), 200


@auth_bp.route('/test-claude', methods=['GET'])
def test_claude():
    import requests as req
    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'status': 'FAILED', 'reason': 'ANTHROPIC_API_KEY not set'}), 500
    try:
        resp = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-haiku-4-5',
                'max_tokens': 20,
                'messages': [{'role': 'user', 'content': 'Say OK'}]
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return jsonify({
                'status': 'SUCCESS',
                'response': resp.json()['content'][0]['text']
            }), 200
        return jsonify({
            'status': 'FAILED',
            'http': resp.status_code,
            'error': resp.text[:200]
        }), 500
    except Exception as e:
        return jsonify({'status': 'FAILED', 'error': str(e)}), 500


# ── Debug endpoint — check what otp_tokens table has ─────────
@auth_bp.route('/debug-reset/<email>', methods=['GET'])
def debug_reset(email):
    """Temporary debug — remove after fixing"""
    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        return jsonify({'error': 'user not found', 'email': email}), 404

    tokens = OTPToken.query.filter_by(
        user_id=user.id, token_type='password_reset'
    ).all()

    return jsonify({
        'user_id':    user.id,
        'email':      user.email,
        'is_verified': user.is_verified,
        'tokens': [
            {
                'id':         t.id,
                'is_used':    t.is_used,
                'expires_at': t.expires_at.isoformat(),
                'expired':    t.expires_at < datetime.utcnow(),
            }
            for t in tokens
        ]
    }), 200
