"""
Admin Routes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Interview, Violation, QuestionBank
from functools import wraps

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    users = User.query.paginate(page=page, per_page=per_page)
    return jsonify({
        'users': [u.to_dict() for u in users.items],
        'total': users.total,
        'pages': users.pages,
        'current_page': page,
    }), 200


@admin_bp.route('/users/<int:user_id>/toggle', methods=['PUT'])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'message': f'User {"activated" if user.is_active else "deactivated"}', 'user': user.to_dict()}), 200


@admin_bp.route('/interviews', methods=['GET'])
@admin_required
def list_all_interviews():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    interviews = Interview.query.order_by(Interview.created_at.desc()).paginate(page=page, per_page=per_page)
    return jsonify({
        'interviews': [i.to_dict() for i in interviews.items],
        'total': interviews.total,
        'pages': interviews.pages,
    }), 200


@admin_bp.route('/violations', methods=['GET'])
@admin_required
def list_violations():
    violations = Violation.query.order_by(Violation.occurred_at.desc()).limit(100).all()
    return jsonify({
        'violations': [
            {
                'id': v.id,
                'interview_id': v.interview_id,
                'user_id': v.user_id,
                'type': v.violation_type,
                'description': v.description,
                'occurred_at': v.occurred_at.isoformat(),
            }
            for v in violations
        ]
    }), 200


@admin_bp.route('/analytics', methods=['GET'])
@admin_required
def analytics():
    total_users = User.query.filter_by(role='student').count()
    total_interviews = Interview.query.count()
    completed = Interview.query.filter_by(status='completed').count()

    from sqlalchemy import func
    avg = db.session.query(func.avg(Interview.overall_score)).filter_by(status='completed').scalar()

    return jsonify({
        'total_users': total_users,
        'total_interviews': total_interviews,
        'completed_interviews': completed,
        'avg_score': round(float(avg or 0), 1),
        'completion_rate': round((completed / total_interviews * 100) if total_interviews > 0 else 0, 1),
    }), 200


@admin_bp.route('/questions', methods=['POST'])
@admin_required
def add_question():
    user_id = get_jwt_identity()
    data = request.get_json()
    q = QuestionBank(
        question_text=data['question_text'],
        option_a=data['option_a'],
        option_b=data['option_b'],
        option_c=data['option_c'],
        option_d=data['option_d'],
        correct_answer=data['correct_answer'],
        explanation=data.get('explanation'),
        question_type=data['question_type'],
        difficulty=data.get('difficulty', 'medium'),
        skill_tags=data.get('skill_tags'),
        job_roles=data.get('job_roles'),
        created_by=user_id,
    )
    db.session.add(q)
    db.session.commit()
    return jsonify({'message': 'Question added', 'id': q.id}), 201
