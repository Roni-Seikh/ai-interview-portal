"""
Auth Routes - No email verification required
Registration is instant. Password reset uses security question instead of OTP.
"""
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
import traceback, os

auth_bp = Blueprint('auth', __name__)


# ── Register (instant - no email verification) ────────────────

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

    if User.query.filter_by(email=email).first():
        return jsonify({
            'message': 'Email already registered. Please login instead.',
            'errors': {'email': 'Already in use'}
        }), 409

    # Create user — instantly verified, no OTP needed
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role='student',
        is_active=True,
        is_verified=True,   # ← instantly verified
    )
    db.session.add(user)
    db.session.commit()

    # Auto-login after registration
    access_token  = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=2))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'message': 'Account created successfully! Welcome to InterviewAI.',
        'user_id': user.id,
        'auto_login': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
    }), 201


# ── Login ─────────────────────────────────────────────────────

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

    # Fix any stuck unverified accounts automatically
    if not user.is_verified:
        user.is_verified = True

    user.last_login = datetime.utcnow()
    db.session.commit()

    expires = timedelta(days=30) if remember else timedelta(hours=2)
    return jsonify({
        'message': 'Login successful',
        'access_token':  create_access_token(identity=str(user.id), expires_delta=expires),
        'refresh_token': create_refresh_token(identity=str(user.id)),
        'user': user.to_dict(),
    }), 200


# ── Refresh ───────────────────────────────────────────────────

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    return jsonify({
        'access_token': create_access_token(identity=get_jwt_identity())
    }), 200


# ── Forgot Password — returns token directly (no email needed) ─

@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("10 per minute")
def forgot_password():
    """
    Instead of email OTP, verify by checking email exists in DB.
    Returns a reset_token directly to the frontend.
    User must know their registered email to get the token.
    """
    data  = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        # Vague message to prevent email enumeration
        return jsonify({'message': 'If this email is registered, a reset link has been generated.', 'found': False}), 200

    # Generate a secure reset token and store it
    import secrets
    reset_token = secrets.token_urlsafe(32)

    # Invalidate old tokens
    OTPToken.query.filter_by(user_id=user.id, token_type='password_reset', is_used=False).delete()

    db.session.add(OTPToken(
        user_id=user.id,
        token=reset_token,
        token_type='password_reset',
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    ))
    db.session.commit()

    # Return the token directly — frontend will use it
    return jsonify({
        'message': 'Email found. You can now reset your password.',
        'found': True,
        'reset_token': reset_token,
        'user_id': user.id,
    }), 200


# ── Reset Password using token (no OTP needed) ────────────────

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data         = request.get_json() or {}
    user_id      = data.get('user_id')
    reset_token  = data.get('reset_token', '').strip()
    new_password = data.get('new_password', '')

    if not validate_password(new_password):
        return jsonify({
            'message': 'Password needs 8+ chars, uppercase, lowercase, number & special char'
        }), 422

    if not user_id or not reset_token:
        return jsonify({'message': 'Invalid request — missing user_id or reset_token'}), 400

    token = OTPToken.query.filter_by(
        user_id=user_id,
        token=reset_token,
        token_type='password_reset',
        is_used=False,
    ).first()

    if not token or token.expires_at < datetime.utcnow():
        return jsonify({'message': 'Reset link expired. Please start again.'}), 400

    token.is_used = True
    user = User.query.get(user_id)
    user.password_hash = hash_password(new_password)
    db.session.commit()

    return jsonify({'message': 'Password reset successfully! You can now login.'}), 200


# ── Get current user ──────────────────────────────────────────

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200


# ── Update profile ────────────────────────────────────────────

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


# ── Health check for email config ─────────────────────────────

@auth_bp.route('/test-email', methods=['GET'])
def test_email():
    return jsonify({
        'status': 'Email verification disabled',
        'message': 'Registration is now instant — no email required.',
        'MAIL_SERVER': os.getenv('MAIL_SERVER', 'not set'),
        'MAIL_USERNAME': os.getenv('MAIL_USERNAME', 'not set'),
    }), 200
