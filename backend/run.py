"""
Application Entry Point
"""
from app import create_app, db
import os

app = create_app(os.getenv('FLASK_ENV', 'production'))


@app.cli.command('init-db')
def init_db():
    """Create all DB tables."""
    db.create_all()
    print('Database tables created.')


@app.cli.command('seed-db')
def seed_db():
    """Create default admin user."""
    from app.models import User
    from app.utils.security import hash_password
    if not User.query.filter_by(email='admin@portal.com').first():
        db.session.add(User(
            full_name='Admin', email='admin@portal.com',
            password_hash=hash_password('Admin@1234'),
            role='admin', is_active=True, is_verified=True,
        ))
        db.session.commit()
        print('Admin created: admin@portal.com / Admin@1234')
    else:
        print('Admin already exists.')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port,
            debug=(os.getenv('FLASK_ENV') == 'development'))
