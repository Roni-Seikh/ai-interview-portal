"""
Dashboard Routes
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Interview, InterviewResult, User
from sqlalchemy import func
from app import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()

    interviews = Interview.query.filter_by(user_id=user_id).all()
    completed = [i for i in interviews if i.status == 'completed']

    total = len(interviews)
    total_completed = len(completed)
    avg_score = 0
    avg_technical = 0
    avg_hr = 0

    if completed:
        avg_score = sum(float(i.overall_score) for i in completed) / total_completed
        avg_technical = sum(float(i.technical_score) for i in completed) / total_completed
        avg_hr = sum(float(i.hr_score) for i in completed) / total_completed

    # Recent history (last 6)
    recent = (
        Interview.query
        .filter_by(user_id=user_id, status='completed')
        .order_by(Interview.created_at.desc())
        .limit(6)
        .all()
    )

    # Progress trend (last 10 scores)
    trend = (
        Interview.query
        .filter_by(user_id=user_id, status='completed')
        .order_by(Interview.created_at.asc())
        .limit(10)
        .all()
    )

    return jsonify({
        'total_interviews': total,
        'completed_interviews': total_completed,
        'avg_score': round(avg_score, 1),
        'avg_technical': round(avg_technical, 1),
        'avg_hr': round(avg_hr, 1),
        'recent_interviews': [i.to_dict() for i in recent],
        'score_trend': [
            {'date': i.created_at.strftime('%b %d'), 'score': float(i.overall_score)}
            for i in trend
        ],
    }), 200
