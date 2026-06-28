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

    if User.query.filter_by(email=email).first():
        return jsonify({
            'message': 'Email already registered. Please login instead.',
            'errors': {'email': 'Already in use'}
        }), 409

    user = User(
        full_name=full_name, email=email,
        password_hash=hash_password(password),
        role='student', is_active=True, is_verified=True,
    )
    db.session.add(user)
    db.session.commit()

    access_token  = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=2))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'message': 'Account created! Welcome to InterviewAI.',
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


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    return jsonify({
        'access_token': create_access_token(identity=get_jwt_identity())
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("10 per minute")
def forgot_password():
    """Returns reset_token directly — no email needed."""
    data  = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'message': 'Email is required', 'found': False}), 400

    try:
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({
                'message': 'No account found with this email.',
                'found': False
            }), 200

        # Delete ALL old password_reset tokens for this user
        deleted = db.session.query(OTPToken).filter(
            OTPToken.user_id == user.id,
            OTPToken.token_type == 'password_reset'
        ).delete(synchronize_session=False)
        db.session.flush()

        current_app.logger.info(f"Deleted {deleted} old reset tokens for user {user.id}")

        # Create new token
        reset_token = secrets.token_urlsafe(32)
        expires     = datetime.utcnow() + timedelta(minutes=30)

        new_token = OTPToken(
            user_id    = user.id,
            token      = reset_token,
            token_type = 'password_reset',
            expires_at = expires,
            is_used    = False,
        )
        db.session.add(new_token)
        db.session.commit()

        # Verify it was saved
        saved = OTPToken.query.filter_by(
            user_id    = user.id,
            token      = reset_token,
            token_type = 'password_reset',
        ).first()

        if not saved:
            current_app.logger.error("Token was NOT saved to DB!")
            return jsonify({'message': 'Database error. Please try again.', 'found': False}), 500

        current_app.logger.info(
            f"Reset token saved for user {user.id} ({email}), "
            f"token_id={saved.id}, expires={expires}"
        )

        return jsonify({
            'message': 'Email verified. Set your new password.',
            'found': True,
            'reset_token': reset_token,
            'user_id': user.id,
        }), 200

    except Exception:
        db.session.rollback()
        err = traceback.format_exc()
        current_app.logger.error(f"forgot_password EXCEPTION:\n{err}")
        return jsonify({
            'message': f'Server error: {str(err[-200:])}',
            'found': False
        }), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data         = request.get_json() or {}
    user_id      = data.get('user_id')
    reset_token  = data.get('reset_token', '').strip()
    new_password = data.get('new_password', '')

    current_app.logger.info(
        f"reset_password called: user_id={user_id}, "
        f"token_len={len(reset_token)}, pwd_len={len(new_password)}"
    )

    if not user_id or not reset_token:
        return jsonify({'message': 'Missing user_id or reset_token'}), 400

    if not validate_password(new_password):
        return jsonify({
            'message': 'Password needs 8+ chars, uppercase, lowercase, number & special char'
        }), 422

    try:
        token = OTPToken.query.filter_by(
            user_id    = user_id,
            token      = reset_token,
            token_type = 'password_reset',
            is_used    = False,
        ).first()

        current_app.logger.info(f"Token lookup result: {token}")

        if not token:
            # Check if it exists but is used or expired
            any_token = OTPToken.query.filter_by(
                user_id=user_id, token_type='password_reset'
            ).first()
            if any_token:
                current_app.logger.warning(
                    f"Token exists but is_used={any_token.is_used}, "
                    f"expires={any_token.expires_at}"
                )
            return jsonify({'message': 'Invalid or expired reset link. Please start again.'}), 400

        if token.expires_at < datetime.utcnow():
            return jsonify({'message': 'Reset link expired. Please start again.'}), 400

        token.is_used = True
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        user.password_hash = hash_password(new_password)
        db.session.commit()

        current_app.logger.info(f"Password reset successful for user {user_id}")
        return jsonify({'message': 'Password reset! You can now login.'}), 200

    except Exception:
        db.session.rollback()
        err = traceback.format_exc()
        current_app.logger.error(f"reset_password EXCEPTION:\n{err}")
        return jsonify({'message': f'Server error. Try again.'}), 500


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
        'status': 'No email needed',
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
            headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01',
                     'content-type': 'application/json'},
            json={'model': 'claude-haiku-4-5', 'max_tokens': 20,
                  'messages': [{'role': 'user', 'content': 'Say OK'}]},
            timeout=30,
        )
        if resp.status_code == 200:
            return jsonify({'status': 'SUCCESS',
                            'response': resp.json()['content'][0]['text']}), 200
        return jsonify({'status': 'FAILED', 'http': resp.status_code,
                        'error': resp.text[:200]}), 500
    except Exception as e:
        return jsonify({'status': 'FAILED', 'error': str(e)}), 500


@auth_bp.route('/debug-reset/<email>', methods=['GET'])
def debug_reset(email):
    """Debug — check DB state for a user's reset tokens"""
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
        'now_utc':    datetime.utcnow().isoformat(),
        'tokens': [
            {
                'id':         t.id,
                'is_used':    t.is_used,
                'expires_at': t.expires_at.isoformat(),
                'expired':    t.expires_at < datetime.utcnow(),
                'token_preview': t.token[:10] + '...' if t.token else None,
            }
            for t in tokens
        ]
    }), 200


@auth_bp.route('/debug-db', methods=['GET'])
def debug_db():
    """Check if DB writes work at all"""
    try:
        # Try a simple write
        test_user = User.query.first()
        if not test_user:
            return jsonify({'error': 'no users in DB'}), 500

        test_token = OTPToken(
            user_id    = test_user.id,
            token      = 'DEBUGTEST123',
            token_type = 'password_reset',
            expires_at = datetime.utcnow() + timedelta(minutes=1),
            is_used    = False,
        )
        db.session.add(test_token)
        db.session.commit()

        # Verify
        found = OTPToken.query.filter_by(token='DEBUGTEST123').first()

        # Clean up
        if found:
            db.session.delete(found)
            db.session.commit()

        return jsonify({
            'db_write': 'SUCCESS' if found else 'FAILED',
            'token_id': found.id if found else None,
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            'db_write': 'EXCEPTION',
            'error': traceback.format_exc()[-500:]
        }), 500
