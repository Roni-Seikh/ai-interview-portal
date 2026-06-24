"""
Flask Configuration - Fixed for Brevo SMTP on Render
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY     = os.getenv('SECRET_KEY', 'change-me')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-change-me')
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # ── Database ──────────────────────────────────────────────
    _db_url = os.getenv('DATABASE_URL', '')
    if _db_url:
        if _db_url.startswith('mysql://'):
            _db_url = _db_url.replace('mysql://', 'mysql+pymysql://', 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://"
            f"{os.getenv('DB_USER','root')}:{os.getenv('DB_PASSWORD','')}"
            f"@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','3306')}"
            f"/{os.getenv('DB_NAME','ai_interview_portal')}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE        = 280
    SQLALCHEMY_POOL_TIMEOUT        = 20
    SQLALCHEMY_POOL_PRE_PING       = True
    SQLALCHEMY_ENGINE_OPTIONS      = {'pool_pre_ping': True, 'pool_recycle': 280}

    # ── Mail (Brevo SMTP) ─────────────────────────────────────
    MAIL_SERVER   = os.getenv('MAIL_SERVER', 'smtp-relay.brevo.com')
    MAIL_PORT     = int(os.getenv('MAIL_PORT', 587))
    # Port 587 = TLS (STARTTLS). Port 465 = SSL. Never mix them.
    MAIL_USE_TLS  = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL  = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')   # Brevo account email
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')   # Brevo SMTP key
    # Sender name + the display email (can be Gmail for display)
    MAIL_DEFAULT_SENDER = (
        'InterviewAI',
        os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))
    )

    # ── File Upload ───────────────────────────────────────────
    UPLOAD_FOLDER      = os.getenv('UPLOAD_FOLDER',
                         os.path.join(os.path.dirname(__file__), '..', 'uploads'))
    REPORTS_FOLDER     = os.getenv('REPORTS_FOLDER',
                         os.path.join(os.path.dirname(__file__), '..', 'reports'))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # ── Rate Limiting ─────────────────────────────────────────
    RATELIMIT_DEFAULT     = "300 per day;60 per hour"
    RATELIMIT_STORAGE_URL = "memory://"

    # ── AI ────────────────────────────────────────────────────
    ANTHROPIC_API_KEY            = os.getenv('ANTHROPIC_API_KEY', '')
    MAX_VIOLATIONS_BEFORE_SUBMIT = 3


class DevelopmentConfig(BaseConfig):
    DEBUG           = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(BaseConfig):
    DEBUG                    = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)


class TestingConfig(BaseConfig):
    TESTING                 = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
}
