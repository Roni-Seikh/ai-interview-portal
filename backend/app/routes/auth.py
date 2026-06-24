"""
Authentication Routes - Brevo SMTP version
Clean implementation, no complex fallbacks
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from app import db, mail, limiter
from app.models import User, OTPToken
from app.utils.validators import validate_password, validate_email
from app.utils.security import hash_password, check_password
from flask_mail import Message
from datetime import datetime, timedelta
import random, string, traceback, os

auth_bp = Blueprint('auth', __name__)


# ── Email sender ──────────────────────────────────────────────

def _send_otp_email(to_email: str, name: str, otp: str, purpose: str):
    """Send OTP via Brevo SMTP using Flask-Mail."""
    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#1e293b;
              border-radius:16px;padding:40px;border:1px solid #334155;">
    <h2 style="color:#6366f1;margin:0 0 4px 0;">InterviewAI</h2>
    <p style="color:#64748b;font-size:13px;margin:0 0 24px 0;">AI Mock Interview Portal</p>
    <p style="color:#e2e8f0;">Hi <strong>{name}</strong>,</p>
    <p style="color:#94a3b8;">Your <strong style="color:#e2e8f0;">{purpose}</strong> OTP:</p>
    <div style="background:#0f172a;border:2px solid #6366f1;border-radius:12px;
                padding:24px;text-align:center;margin:20px 0;">
      <span style="color:#6366f1;font-size:40px;font-weight:bold;
                   letter-spacing:16px;font-family:monospace;">{otp}</span>
    </div>
    <p style="color:#64748b;font-size:13px;">⏱ Expires in 10 minutes.</p>
    <p style="color:#64748b;font-size:13px;">🔒 Never share this OTP.</p>
  </div>
</body>
</html>"""

    sender_email = os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('MAIL_USERNAME')
    msg = Message(
        subject=f"InterviewAI — {purpose} OTP: {otp}",
        sender=('InterviewAI', sender_email),
        recipients=[to_email],
        html=html,
    )
    mail.send(msg)
    current_app.logger.info(f"OTP email sent to {to_email} via {os.getenv('MAIL_SERVER')}")


# ── Register ──────────────────────────────────────────────────

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
        return jsonify({'message': 'Email already registered',
                        'errors': {'email': 'Already in use'}}), 409

    user = User(
        full_name=full_name, email=email,
        password_hash=hash_password(password),
        role='student', is_active=True, is_verified=False,
    )
    db.session.add(user)
    db.session.flush()

    otp = ''.join(random.choices(string.digits, k=6))
    db.session.add(OTPToken(
        user_id=user.id, token=otp,
        token_type='email_verify',
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    ))
    db.session.commit()

    try:
        _send_otp_email(email, full_name, otp, 'Email Verification')
        return jsonify({
            'message': 'Registration successful! Check your email for OTP.',
            'user_id': user.id,
        }), 201
    except Exception as e:
        err = traceback.format_exc()
        current_app.logger.error(f"Email send FAILED:\n{err}")
        # Account is created — user can use resend OTP
        return jsonify({
            'message': 'Account created but email failed. Use Resend OTP button.',
            'user_id': user.id,
            'email_error': str(e),
        }), 201


# ── Resend OTP ────────────────────────────────────────────────

@auth_bp.route('/resend-otp', methods=['POST'])
@limiter.limit("5 per minute")
def resend_otp():
    data    = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'message': 'user_id required'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    if user.is_verified:
        return jsonify({'message': 'Email already verified'}), 400

    OTPToken.query.filter_by(
        user_id=user.id, token_type='email_verify', is_used=False
    ).delete()

    otp = ''.join(random.choices(string.digits, k=6))
    db.session.add(OTPToken(
        user_id=user.id, token=otp, token_type='email_verify',
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    ))
    db.session.commit()

    try:
        _send_otp_email(user.email, user.full_name, otp, 'Email Verification')
        return jsonify({'message': 'OTP resent! Check your email.'}), 200
    except Exception as e:
        current_app.logger.error(f"Resend OTP failed:\n{traceback.format_exc()}")
        return jsonify({'message': f'Email failed: {str(e)}'}), 500


# ── Verify Email ──────────────────────────────────────────────

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data    = request.get_json() or {}
    user_id = data.get('user_id')
    otp     = data.get('otp', '').strip()

    token = OTPToken.query.filter_by(
        user_id=user_id, token=otp,
        token_type='email_verify', is_used=False
    ).first()

    if not token or token.expires_at < datetime.utcnow():
        return jsonify({'message': 'Invalid or expired OTP.'}), 400

    token.is_used = True
    User.query.get(user_id).is_verified = True
    db.session.commit()
    return jsonify({'message': 'Email verified! You can now login.'}), 200


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
        return jsonify({'message': 'Account deactivated.'}), 403
    if not user.is_verified:
        return jsonify({
            'message': 'Please verify your email first.',
            'needs_verification': True,
            'user_id': user.id,
        }), 403

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


# ── Forgot Password ───────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("5 per minute")
def forgot_password():
    data  = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    user  = User.query.filter_by(email=email).first()

    if user:
        OTPToken.query.filter_by(
            user_id=user.id, token_type='password_reset', is_used=False
        ).delete()
        otp = ''.join(random.choices(string.digits, k=6))
        db.session.add(OTPToken(
            user_id=user.id, token=otp, token_type='password_reset',
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        ))
        db.session.commit()
        try:
            _send_otp_email(email, user.full_name, otp, 'Password Reset')
        except Exception as e:
            current_app.logger.error(f"Forgot password email failed:\n{traceback.format_exc()}")
            return jsonify({'message': f'Email failed: {str(e)}'}), 500

    return jsonify({'message': 'If this email exists, an OTP has been sent.'}), 200


# ── Reset Password ────────────────────────────────────────────

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data         = request.get_json() or {}
    email        = data.get('email', '').strip().lower()
    otp          = data.get('otp', '').strip()
    new_password = data.get('new_password', '')

    if not validate_password(new_password):
        return jsonify({'message': 'Password needs 8+ chars, upper, lower, number & special'}), 422

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Invalid request'}), 400

    token = OTPToken.query.filter_by(
        user_id=user.id, token=otp,
        token_type='password_reset', is_used=False
    ).first()
    if not token or token.expires_at < datetime.utcnow():
        return jsonify({'message': 'Invalid or expired OTP'}), 400

    token.is_used      = True
    user.password_hash = hash_password(new_password)
    db.session.commit()
    return jsonify({'message': 'Password reset successfully!'}), 200


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


# ── Test Email ────────────────────────────────────────────────

@auth_bp.route('/test-email', methods=['GET'])
def test_email():
    """Test Brevo SMTP — open in browser"""
    username = os.getenv('MAIL_USERNAME', 'NOT SET')
    server   = os.getenv('MAIL_SERVER',   'NOT SET')
    port     = os.getenv('MAIL_PORT',     'NOT SET')
    sender   = os.getenv('MAIL_DEFAULT_SENDER', username)

    config_info = {
        'MAIL_SERVER':   server,
        'MAIL_PORT':     port,
        'MAIL_USERNAME': username,
        'MAIL_DEFAULT_SENDER': sender,
        'MAIL_USE_TLS':  os.getenv('MAIL_USE_TLS', 'not set'),
        'MAIL_USE_SSL':  os.getenv('MAIL_USE_SSL', 'not set'),
        'password_set':  bool(os.getenv('MAIL_PASSWORD')),
    }

    if username == 'NOT SET' or not os.getenv('MAIL_PASSWORD'):
        return jsonify({
            'status': 'FAILED',
            'reason': 'MAIL_USERNAME or MAIL_PASSWORD not configured',
            'config': config_info,
        }), 500

    try:
        msg = Message(
            subject='InterviewAI — SMTP Test ✅',
            sender=('InterviewAI', sender),
            recipients=[sender],
            html='<div style="font-family:Arial;padding:20px;">'
                 '<h2 style="color:#6366f1;">✅ Email is working!</h2>'
                 f'<p>Sent via {server}:{port}</p></div>',
        )
        mail.send(msg)
        return jsonify({
            'status': 'SUCCESS',
            'message': f'Test email sent to {sender}. Check inbox!',
            'config': config_info,
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'FAILED',
            'error': str(e),
            'config': config_info,
            'hint': (
                'Wrong SMTP key — regenerate on Brevo dashboard'
                if 'authentication' in str(e).lower() else
                'Connection refused — check MAIL_SERVER and MAIL_PORT'
                if 'connect' in str(e).lower() else
                str(e)
            ),
        }), 500


# ── Test Claude ───────────────────────────────────────────────

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
