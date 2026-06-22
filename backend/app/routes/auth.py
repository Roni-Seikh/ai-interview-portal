"""
Authentication Routes - Fixed email delivery for Render hosting
Uses direct smtplib as fallback when Flask-Mail fails on Render
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
import random, string, traceback, os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

auth_bp = Blueprint('auth', __name__)


# ── Email sender with dual method ────────────────────────────

def _send_otp_email(to_email: str, name: str, otp: str, purpose: str):
    """
    Send OTP email.
    Tries Flask-Mail first, falls back to direct smtplib if it fails.
    smtplib works more reliably on Render/cloud hosting.
    """
    username = os.getenv('MAIL_USERNAME', '')
    password = os.getenv('MAIL_PASSWORD', '')

    if not username or not password:
        raise ValueError("MAIL_USERNAME or MAIL_PASSWORD not set in environment")

    subject  = f"InterviewAI — {purpose} OTP: {otp}"
    html_body = f"""
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
    <p style="color:#64748b;font-size:13px;">🔒 Never share this OTP with anyone.</p>
    <hr style="border:none;border-top:1px solid #334155;margin:24px 0;" />
    <p style="color:#475569;font-size:12px;">
      If you did not request this, please ignore this email.
    </p>
  </div>
</body>
</html>"""

    last_error = None

    # Method 1: Try port 587 TLS (standard)
    try:
        current_app.logger.info(f"Trying SMTP port 587 TLS to {to_email}...")
        _send_via_smtplib(username, password, to_email, subject, html_body, port=587, use_ssl=False)
        current_app.logger.info(f"Email sent via port 587 to {to_email}")
        return
    except Exception as e:
        last_error = e
        current_app.logger.warning(f"Port 587 failed: {e}")

    # Method 2: Try port 465 SSL
    try:
        current_app.logger.info(f"Trying SMTP port 465 SSL to {to_email}...")
        _send_via_smtplib(username, password, to_email, subject, html_body, port=465, use_ssl=True)
        current_app.logger.info(f"Email sent via port 465 to {to_email}")
        return
    except Exception as e:
        last_error = e
        current_app.logger.warning(f"Port 465 failed: {e}")

    # Method 3: Try Flask-Mail as last resort
    try:
        current_app.logger.info(f"Trying Flask-Mail to {to_email}...")
        msg = Message(subject=subject, recipients=[to_email], html=html_body)
        mail.send(msg)
        current_app.logger.info(f"Email sent via Flask-Mail to {to_email}")
        return
    except Exception as e:
        last_error = e
        current_app.logger.warning(f"Flask-Mail failed: {e}")

    # All methods failed
    raise RuntimeError(f"All email methods failed. Last error: {last_error}")


def _send_via_smtplib(username, password, to_email, subject, html_body, port=587, use_ssl=False):
    """Send email via direct smtplib connection."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"InterviewAI <{username}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    if use_ssl:
        # Port 465 — SSL from start
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(username, password)
            server.sendmail(username, to_email, msg.as_string())
    else:
        # Port 587 — STARTTLS
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.sendmail(username, to_email, msg.as_string())


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
        current_app.logger.info(f'OTP email sent to {email}')
    except Exception as e:
        email_error = str(e)
        current_app.logger.error(f'Email failed for {email}: {traceback.format_exc()}')

    resp = {'message': 'Registration successful. Check your email for OTP.', 'user_id': user.id}
    if email_error:
        resp['message'] = 'Account created but email delivery failed. Contact support or use Resend OTP.'
        resp['email_error'] = email_error
    return jsonify(resp), 201


# ── Resend OTP ────────────────────────────────────────────────

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

    OTPToken.query.filter_by(user_id=user.id, token_type='email_verify', is_used=False).delete()

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
        return jsonify({
            'message': 'Please verify your email first.',
            'needs_verification': True,
            'user_id': user.id,
        }), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    expires       = timedelta(days=30) if remember else timedelta(hours=2)
    access_token  = create_access_token(identity=str(user.id), expires_delta=expires)
    refresh_token = create_refresh_token(identity=str(user.id))

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
            current_app.logger.info(f'Password reset OTP sent to {email}')
        except Exception as e:
            current_app.logger.error(f'Password reset email failed: {traceback.format_exc()}')
            return jsonify({
                'message': f'Email delivery failed: {str(e)}'
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


# ── SMTP Test ─────────────────────────────────────────────────

@auth_bp.route('/test-email', methods=['GET'])
def test_email():
    """Test SMTP — visit in browser: /api/auth/test-email"""
    username = os.getenv('MAIL_USERNAME', '')
    password = os.getenv('MAIL_PASSWORD', '')

    if not username:
        return jsonify({'status': 'FAILED', 'reason': 'MAIL_USERNAME not set'}), 500
    if not password:
        return jsonify({'status': 'FAILED', 'reason': 'MAIL_PASSWORD not set'}), 500

    results = {}

    # Test port 587
    try:
        _send_via_smtplib(username, password, username,
                          'InterviewAI SMTP Test (587)', '<p>Port 587 works!</p>', port=587, use_ssl=False)
        results['port_587'] = 'SUCCESS'
    except Exception as e:
        results['port_587'] = f'FAILED: {str(e)}'

    # Test port 465
    try:
        _send_via_smtplib(username, password, username,
                          'InterviewAI SMTP Test (465)', '<p>Port 465 works!</p>', port=465, use_ssl=True)
        results['port_465'] = 'SUCCESS'
    except Exception as e:
        results['port_465'] = f'FAILED: {str(e)}'

    any_success = any('SUCCESS' in v for v in results.values())
    return jsonify({
        'status': 'SUCCESS' if any_success else 'FAILED',
        'sender': username,
        'results': results,
        'message': 'Check your inbox!' if any_success else 'Both ports failed — check Gmail App Password',
    }), 200 if any_success else 500


# ── Claude API Test ───────────────────────────────────────────

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
            json={'model': 'claude-haiku-4-5', 'max_tokens': 30,
                  'messages': [{'role': 'user', 'content': 'Say OK'}]},
            timeout=30,
        )
        if resp.status_code == 200:
            return jsonify({'status': 'SUCCESS', 'response': resp.json()['content'][0]['text']}), 200
        return jsonify({'status': 'FAILED', 'http_status': resp.status_code, 'error': resp.text[:300]}), 500
    except Exception as e:
        return jsonify({'status': 'FAILED', 'error': str(e)}), 500
