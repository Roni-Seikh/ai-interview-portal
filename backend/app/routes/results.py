"""
Results Routes
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Interview, InterviewResult, Feedback, InterviewQuestion, InterviewAnswer, Violation

results_bp = Blueprint('results', __name__)


@results_bp.route('/<int:interview_id>', methods=['GET'])
@jwt_required()
def get_results(interview_id):
    user_id = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404

    result = InterviewResult.query.filter_by(interview_id=interview_id).first()
    feedback = Feedback.query.filter_by(interview_id=interview_id).first()

    # Q&A review
    questions = InterviewQuestion.query.filter_by(interview_id=interview_id).order_by(
        InterviewQuestion.round_number, InterviewQuestion.question_order
    ).all()
    answers = InterviewAnswer.query.filter_by(interview_id=interview_id).all()
    answer_map = {a.question_id: a for a in answers}

    qa_review = []
    for q in questions:
        ans = answer_map.get(q.id)
        qa_review.append({
            **q.to_dict(include_answer=True),
            'selected_answer': ans.selected_answer if ans else 'skipped',
            'is_correct': ans.is_correct if ans else False,
            'time_taken': ans.time_taken_seconds if ans else 0,
        })

    violations = Violation.query.filter_by(interview_id=interview_id).all()
    violation_list = [
        {'type': v.violation_type, 'description': v.description, 'time': v.occurred_at.isoformat()}
        for v in violations
    ]

    return jsonify({
        'interview': interview.to_dict(),
        'result': result.to_dict() if result else None,
        'feedback': feedback.to_dict() if feedback else None,
        'qa_review': qa_review,
        'violations': violation_list,
    }), 200
