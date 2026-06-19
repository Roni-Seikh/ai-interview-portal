"""
Authentication Routes - Fixed email sender + resend OTP
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
import random, string, traceback

auth_bp = Blueprint('auth', __name__)


# ── Core email sender ─────────────────────────────────────────

def _send_otp_email(to_email: str, name: str, otp: str, purpose: str):
    """
    Send OTP email via Gmail SMTP.
    Sender = MAIL_USERNAME (Gmail requires this to match authenticated account).
    """
    username = current_app.config.get('MAIL_USERNAME')
    if not username:
        raise ValueError("MAIL_USERNAME not set in .env file")

    msg = Message(
        subject=f'InterviewAI — {purpose} OTP: {otp}',
        recipients=[to_email],
        html=f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#1e293b;border-radius:16px;
              padding:40px;border:1px solid #334155;">
    <h2 style="color:#6366f1;margin:0 0 4px 0;font-size:24px;">InterviewAI</h2>
    <p style="color:#64748b;font-size:13px;margin:0 0 28px 0;">AI Mock Interview Portal</p>
    <p style="color:#e2e8f0;font-size:15px;">Hi <strong>{name}</strong>,</p>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px;">
      Your <strong style="color:#e2e8f0;">{purpose}</strong> OTP is:
    </p>
    <div style="background:#0f172a;border:2px solid #6366f1;border-radius:12px;
                padding:28px;text-align:center;margin:0 0 24px 0;">
      <span style="color:#6366f1;font-size:42px;font-weight:bold;
                   letter-spacing:18px;font-family:monospace;">{otp}</span>
    </div>
    <p style="color:#64748b;font-size:13px;">⏱ Expires in <strong>10 minutes</strong>.</p>
    <p style="color:#64748b;font-size:13px;">🔒 Never share this with anyone.</p>
    <hr style="border:none;border-top:1px solid #334155;margin:24px 0;" />
    <p style="color:#475569;font-size:12px;">
      If you did not request this, please ignore this email.
    </p>
  </div>
</body>
</html>""",
    )
    mail.send(msg)


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
        errors['full_name'] = 'Full name must be at least 2 characters'
    if not validate_email(email):
        errors['email'] = 'Invalid email address'
    if not validate_password(password):
        errors['password'] = 'Need 8+ chars, uppercase, lowercase, number & special char'
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
        user_id=user.id, token=otp, token_type='email_verify',
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    ))
    db.session.commit()

    email_error = None
    try:
        _send_otp_email(email, full_name, otp, 'Email Verification')
        current_app.logger.info(f'Verification OTP sent to {email}')
    except Exception as e:
        email_error = str(e)
        current_app.logger.error(f'Email failed for {email}: {traceback.format_exc()}')

    resp = {'message': 'Registration successful. Check your email for OTP.', 'user_id': user.id}
    if email_error:
        resp['message'] = 'Account created but email delivery failed. Use Resend OTP.'
        resp['email_error'] = email_error
    return jsonify(resp), 201


# ── Resend OTP (POST) ─────────────────────────────────────────

@auth_bp.route('/resend-otp', methods=['POST'])
@limiter.limit("5 per minute")
def resend_otp():
    data    = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'message': 'user_id is required'}), 400

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
        return jsonify({'message': 'OTP resent successfully'}), 200
    except Exception as e:
        current_app.logger.error(f'Resend OTP failed: {traceback.format_exc()}')
        return jsonify({'message': f'Email delivery failed: {str(e)}'}), 500


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
        return jsonify({'message': 'Invalid or expired OTP. Request a new one.'}), 400

    token.is_used = True
    user = User.query.get(user_id)
    user.is_verified = True
    db.session.commit()
    return jsonify({'message': 'Email verified! You can now login.'}), 200


# ── Login ─────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("20 per minute")
def login():
    data = request.get_json() or {}
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = data.get('remember_me', False)

    user = User.query.filter_by(email=email).first()
    if not user or not check_password(password, user.password_hash):
        return jsonify({'message': 'Invalid email or password'}), 401
    if not user.is_active:
        return jsonify({'message': 'Account deactivated. Contact support.'}), 403
    if not user.is_verified:
        return jsonify({
            'message': 'Please verify your email first.',
            'needs_verification': True,
            'user_id': user.id,
        }), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    expires      = timedelta(days=30) if remember else timedelta(hours=2)
    access_token = create_access_token(identity=str(user.id), expires_delta=expires)
    refresh_token= create_refresh_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
    }), 200


# ── Refresh ───────────────────────────────────────────────────

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    return jsonify({'access_token': create_access_token(identity=get_jwt_identity())}), 200


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
            current_app.logger.info(f'Password reset OTP sent to {email}')
        except Exception as e:
            current_app.logger.error(f'Password reset email failed: {traceback.format_exc()}')
            return jsonify({
                'message': f'Email delivery failed: {str(e)}',
                'hint': 'Check your .env MAIL_USERNAME / MAIL_PASSWORD'
            }), 500

    return jsonify({'message': 'If this email exists, an OTP has been sent.'}), 200


# ── Reset Password ────────────────────────────────────────────

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data         = request.get_json() or {}
    email        = data.get('email', '').strip().lower()
    otp          = data.get('otp', '').strip()
    new_password = data.get('new_password', '')

    if not validate_password(new_password):
        return jsonify({'message': 'Password must be 8+ chars with uppercase, lowercase, number & special char'}), 422

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


# ── SMTP Test (GET) ───────────────────────────────────────────

@auth_bp.route('/test-email', methods=['GET'])
def test_email():
    """
    Open in browser to verify Gmail SMTP works.
    GET http://localhost:5000/api/auth/test-email
    """
    username = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')

    # Diagnose config first
    if not username:
        return jsonify({
            'status': 'FAILED',
            'reason': 'MAIL_USERNAME is empty in .env',
            'fix': 'Set MAIL_USERNAME=roniseikh2004@gmail.com in backend/.env'
        }), 500
    if not password:
        return jsonify({
            'status': 'FAILED',
            'reason': 'MAIL_PASSWORD is empty in .env',
            'fix': 'Set MAIL_PASSWORD=your_16_char_app_password in backend/.env'
        }), 500

    try:
        msg = Message(
            subject='InterviewAI — SMTP Test ✅',
            recipients=[username],
            html=f"""
<div style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:30px;border-radius:12px;">
  <h2 style="color:#6366f1;">✅ SMTP is working!</h2>
  <p>Your Gmail SMTP configuration is correct.</p>
  <p style="color:#64748b;font-size:13px;">Sent from: {username}</p>
</div>""",
        )
        mail.send(msg)
        return jsonify({
            'status': 'SUCCESS',
            'message': f'Test email sent to {username}. Check your inbox!',
            'sender': username,
        }), 200
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f'SMTP test failed:\n{tb}')

        # Give specific diagnosis
        err_str = str(e).lower()
        if 'username and password not accepted' in err_str or '535' in err_str:
            hint = ('Gmail rejected your password. '
                    'Make sure you are using a 16-char App Password '
                    '(NOT your Gmail login password). '
                    'Enable 2FA first at myaccount.google.com, '
                    'then create App Password under Security.')
        elif 'connect' in err_str or 'timeout' in err_str:
            hint = 'Cannot connect to smtp.gmail.com:587. Check your internet / firewall.'
        elif 'none' in err_str:
            hint = 'MAIL_USERNAME or MAIL_PASSWORD is None in .env. Check the file was saved.'
        else:
            hint = str(e)

        return jsonify({
            'status': 'FAILED',
            'error': str(e),
            'hint': hint,
            'your_mail_username': username,
            'password_length': len(password) if password else 0,
        }), 500


# ── Public Claude API test (no auth needed) ───────────────────
@auth_bp.route('/test-claude', methods=['GET'])
def test_claude():
    """GET /api/auth/test-claude — test if Claude API key works"""
    import requests as req, os, traceback
    api_key = os.getenv('ANTHROPIC_API_KEY', '')

    if not api_key:
        return jsonify({'status': 'FAILED', 'reason': 'ANTHROPIC_API_KEY is empty'}), 500

    try:
        resp = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-haiku-4-5',
                'max_tokens': 30,
                'messages': [{'role': 'user', 'content': 'Say OK'}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return jsonify({
                'status': 'SUCCESS',
                'message': 'Claude API is working',
                'response': resp.json()['content'][0]['text'],
                'key_prefix': api_key[:20] + '...',
            }), 200
        else:
            return jsonify({
                'status': 'FAILED',
                'http_status': resp.status_code,
                'error': resp.text[:500],
                'hint': (
                    'Invalid API key' if resp.status_code == 401 else
                    'API overloaded' if resp.status_code == 529 else
                    'Check Anthropic account'
                ),
            }), 500
    except Exception:
        return jsonify({'status': 'FAILED', 'error': traceback.format_exc()[-500:]}), 500
