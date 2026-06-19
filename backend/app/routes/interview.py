"""
Interview Routes - with detailed error reporting on feedback
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import (
    Interview, InterviewQuestion, InterviewAnswer,
    InterviewResult, Resume, Violation, Feedback
)
from app.services.ai_service import generate_interview_questions, generate_feedback
from datetime import datetime
import traceback, os, requests as req

interview_bp = Blueprint('interview', __name__)


@interview_bp.route('/setup', methods=['POST'])
@jwt_required()
def setup_interview():
    user_id = get_jwt_identity()
    data = request.get_json()
    resume_id        = data.get('resume_id')
    job_role         = data.get('job_role', '').strip()
    job_description  = data.get('job_description', '').strip()
    experience_level = data.get('experience_level', 'fresher')

    if not all([resume_id, job_role, job_description]):
        return jsonify({'message': 'resume_id, job_role and job_description are required'}), 400

    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return jsonify({'message': 'Resume not found'}), 404

    interview = Interview(
        user_id=user_id, resume_id=resume_id,
        job_role=job_role, job_description=job_description,
        experience_level=experience_level, status='setup',
    )
    db.session.add(interview)
    db.session.commit()

    try:
        questions_data = generate_interview_questions(
            job_role=job_role,
            job_description=job_description,
            experience_level=experience_level,
            skills=resume.extracted_skills or [],
            projects=resume.extracted_projects or [],
            education=resume.extracted_education or [],
            resume_text=resume.parsed_text or "",
        )
    except Exception as e:
        current_app.logger.error(f'Question generation error:\n{traceback.format_exc()}')
        db.session.delete(interview)
        db.session.commit()
        return jsonify({'message': f'Failed to generate questions: {str(e)}'}), 500

    for i, q in enumerate(questions_data.get('technical', [])):
        db.session.add(InterviewQuestion(
            interview_id=interview.id,
            question_text=q['question'],
            option_a=q['options']['A'], option_b=q['options']['B'],
            option_c=q['options']['C'], option_d=q['options']['D'],
            correct_answer=q['correct'],
            question_type='technical', round_number=1,
            question_order=i + 1, time_limit_seconds=20,
            skill_tag=q.get('skill_tag', ''),
        ))
    for i, q in enumerate(questions_data.get('hr', [])):
        db.session.add(InterviewQuestion(
            interview_id=interview.id,
            question_text=q['question'],
            option_a=q['options']['A'], option_b=q['options']['B'],
            option_c=q['options']['C'], option_d=q['options']['D'],
            correct_answer=q['correct'],
            question_type='hr', round_number=2,
            question_order=i + 1, time_limit_seconds=20,
            skill_tag=q.get('skill_tag', ''),
        ))
    db.session.commit()
    return jsonify({
        'message': 'Interview setup complete',
        'interview_id': interview.id,
        'technical_count': len(questions_data.get('technical', [])),
        'hr_count': len(questions_data.get('hr', [])),
    }), 201


@interview_bp.route('/<int:interview_id>/questions/<round_type>', methods=['GET'])
@jwt_required()
def get_questions(interview_id, round_type):
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404
    if round_type not in ('technical', 'hr'):
        return jsonify({'message': 'Invalid round type'}), 400

    questions = (InterviewQuestion.query
                 .filter_by(interview_id=interview_id, question_type=round_type)
                 .order_by(InterviewQuestion.question_order).all())

    if round_type == 'technical' and interview.status == 'setup':
        interview.status = 'technical_round'
        interview.technical_start_time = datetime.utcnow()
        db.session.commit()
    elif round_type == 'hr' and interview.status == 'technical_round':
        interview.status = 'hr_round'
        interview.hr_start_time = datetime.utcnow()
        db.session.commit()

    return jsonify({
        'questions': [q.to_dict(include_answer=False) for q in questions],
        'total': len(questions),
        'time_per_question': 20,
        'total_time_seconds': len(questions) * 20,
    }), 200


@interview_bp.route('/<int:interview_id>/submit-round', methods=['POST'])
@jwt_required()
def submit_round(interview_id):
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404

    data       = request.get_json()
    answers    = data.get('answers', [])
    round_type = data.get('round_type', 'technical')

    for ans in answers:
        q_id       = ans.get('question_id')
        selected   = ans.get('selected_answer', 'skipped')
        time_taken = ans.get('time_taken_seconds', 0)
        question   = InterviewQuestion.query.filter_by(id=q_id, interview_id=interview_id).first()
        if not question:
            continue
        is_correct = (selected == question.correct_answer)
        existing   = InterviewAnswer.query.filter_by(interview_id=interview_id, question_id=q_id).first()
        if existing:
            existing.selected_answer    = selected
            existing.is_correct         = is_correct
            existing.time_taken_seconds = time_taken
        else:
            db.session.add(InterviewAnswer(
                interview_id=interview_id, question_id=q_id,
                selected_answer=selected, is_correct=is_correct,
                time_taken_seconds=time_taken,
            ))

    if round_type == 'technical':
        interview.technical_end_time = datetime.utcnow()
    elif round_type == 'hr':
        interview.hr_end_time = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': f'{round_type.title()} round submitted'}), 200


@interview_bp.route('/<int:interview_id>/complete', methods=['POST'])
@jwt_required()
def complete_interview(interview_id):
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404

    _calculate_scores(interview)
    interview.status = 'completed'
    db.session.commit()

    feedback_status = 'pending'
    try:
        resume = Resume.query.get(interview.resume_id)
        generate_feedback(interview, resume)
        fb = Feedback.query.filter_by(interview_id=interview_id).first()
        feedback_status = 'generated' if (fb and fb.overall_summary) else 'empty'
    except Exception:
        current_app.logger.error(f'Feedback error:\n{traceback.format_exc()}')
        feedback_status = 'failed'

    return jsonify({
        'message': 'Interview completed',
        'interview_id': interview.id,
        'overall_score': float(interview.overall_score),
        'feedback_status': feedback_status,
    }), 200


@interview_bp.route('/<int:interview_id>/regenerate-feedback', methods=['POST'])
@jwt_required()
def regenerate_feedback(interview_id):
    """Regenerate feedback — returns detailed error if it fails."""
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404
    if interview.status != 'completed':
        return jsonify({'message': 'Interview not completed yet'}), 400

    try:
        resume = Resume.query.get(interview.resume_id)
        generate_feedback(interview, resume)
        fb = Feedback.query.filter_by(interview_id=interview_id).first()
        if fb and fb.overall_summary:
            return jsonify({'message': 'Feedback generated successfully'}), 200
        else:
            return jsonify({'message': 'Feedback generation returned empty result'}), 500
    except Exception:
        err = traceback.format_exc()
        current_app.logger.error(f'Regenerate feedback failed:\n{err}')
        # Return the real error to the frontend for debugging
        return jsonify({
            'message': 'Feedback generation failed',
            'error': err[-1000:]   # last 1000 chars of traceback
        }), 500


# NEW: debug endpoint — call this in browser to see exact error
@interview_bp.route('/<int:interview_id>/debug-feedback', methods=['GET'])
@jwt_required()
def debug_feedback(interview_id):
    """
    GET /api/interview/{id}/debug-feedback
    Shows exactly what is failing in feedback generation.
    """
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    debug   = {
        'interview_id':    interview_id,
        'interview_status': interview.status,
        'job_role':        interview.job_role,
        'api_key_set':     bool(api_key),
        'api_key_prefix':  api_key[:15] + '...' if len(api_key) > 15 else '(empty)',
        'api_key_length':  len(api_key),
    }

    # Test Claude API directly
    if not api_key:
        debug['claude_test'] = 'FAILED - ANTHROPIC_API_KEY is empty in .env'
        return jsonify(debug), 500

    try:
        resp = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 50,
                'messages': [{'role': 'user', 'content': 'Reply with just: {"ok": true}'}],
            },
            timeout=30,
        )
        debug['claude_http_status'] = resp.status_code
        debug['claude_response']    = resp.text[:300]
        if resp.status_code == 200:
            debug['claude_test'] = 'SUCCESS - Claude API is reachable'
        else:
            debug['claude_test'] = f'FAILED - HTTP {resp.status_code}'
    except Exception as e:
        debug['claude_test'] = f'FAILED - {str(e)}'

    # Check resume
    resume = Resume.query.get(interview.resume_id)
    debug['resume_found']  = bool(resume)
    debug['resume_skills'] = (resume.extracted_skills or [])[:5] if resume else []
    debug['resume_text_len'] = len(resume.parsed_text or '') if resume else 0

    # Check existing feedback
    fb = Feedback.query.filter_by(interview_id=interview_id).first()
    debug['feedback_exists']  = bool(fb)
    debug['feedback_summary'] = bool(fb and fb.overall_summary)

    # Try generating feedback and catch exact error
    try:
        generate_feedback(interview, resume)
        debug['generate_feedback'] = 'SUCCESS'
    except Exception:
        debug['generate_feedback'] = 'FAILED'
        debug['generate_error']    = traceback.format_exc()

    return jsonify(debug), 200


@interview_bp.route('/<int:interview_id>/violation', methods=['POST'])
@jwt_required()
def log_violation(interview_id):
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404

    data           = request.get_json()
    violation_type = data.get('violation_type')
    description    = data.get('description', '')

    valid = ['tab_switch','window_minimize','camera_off','copy_attempt',
             'paste_attempt','right_click','keyboard_shortcut','fullscreen_exit','suspicious_activity']
    if violation_type not in valid:
        return jsonify({'message': 'Invalid violation type'}), 400

    db.session.add(Violation(
        interview_id=interview_id, user_id=user_id,
        violation_type=violation_type, description=description,
    ))
    interview.violation_count += 1
    max_v       = current_app.config.get('MAX_VIOLATIONS_BEFORE_SUBMIT', 3)
    auto_submit = interview.violation_count >= max_v

    if auto_submit and interview.status not in ('completed', 'abandoned'):
        interview.auto_submitted = True
        _calculate_scores(interview)
        interview.status = 'completed'
        db.session.commit()
        try:
            resume = Resume.query.get(interview.resume_id)
            generate_feedback(interview, resume)
        except Exception:
            current_app.logger.error(traceback.format_exc())

    db.session.commit()
    return jsonify({
        'message': 'Violation logged',
        'violation_count': interview.violation_count,
        'auto_submitted': auto_submit,
        'warnings_remaining': max(0, max_v - interview.violation_count),
    }), 200


@interview_bp.route('/history', methods=['GET'])
@jwt_required()
def interview_history():
    user_id    = get_jwt_identity()
    interviews = (Interview.query.filter_by(user_id=user_id)
                  .order_by(Interview.created_at.desc()).all())
    return jsonify({'interviews': [i.to_dict() for i in interviews]}), 200


@interview_bp.route('/<int:interview_id>', methods=['GET'])
@jwt_required()
def get_interview(interview_id):
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404
    return jsonify({'interview': interview.to_dict()}), 200


# ── Score Calculation ─────────────────────────────────────────

def _calculate_scores(interview):
    tech_qs = InterviewQuestion.query.filter_by(interview_id=interview.id, question_type='technical').all()
    hr_qs   = InterviewQuestion.query.filter_by(interview_id=interview.id, question_type='hr').all()

    def score_round(questions):
        total = len(questions)
        correct = wrong = skipped = 0
        for q in questions:
            ans = InterviewAnswer.query.filter_by(interview_id=interview.id, question_id=q.id).first()
            if not ans or ans.selected_answer == 'skipped':
                skipped += 1
            elif ans.is_correct:
                correct += 1
            else:
                wrong += 1
        pct = round((correct / total) * 100, 2) if total > 0 else 0
        return total, correct, wrong, skipped, pct

    tt, tc, tw, ts, tp = score_round(tech_qs)
    ht, hc, hw, hs, hp = score_round(hr_qs)
    overall = round((tp + hp) / 2, 2)

    interview.technical_score = tp
    interview.hr_score        = hp
    interview.overall_score   = overall
    grade = ('A+' if overall>=90 else 'A' if overall>=80 else 'B+' if overall>=70
             else 'B' if overall>=60 else 'C' if overall>=50 else 'D' if overall>=40 else 'F')

    skill_scores = {}
    for q in tech_qs + hr_qs:
        tag = q.skill_tag or 'General'
        if tag not in skill_scores:
            skill_scores[tag] = {'correct': 0, 'total': 0}
        skill_scores[tag]['total'] += 1
        ans = InterviewAnswer.query.filter_by(interview_id=interview.id, question_id=q.id).first()
        if ans and ans.is_correct:
            skill_scores[tag]['correct'] += 1
    for tag in skill_scores:
        v = skill_scores[tag]
        v['percentage'] = round(v['correct'] / v['total'] * 100, 2) if v['total'] else 0

    result = InterviewResult.query.filter_by(interview_id=interview.id).first()
    if not result:
        result = InterviewResult(interview_id=interview.id)
        db.session.add(result)

    result.technical_total      = tt
    result.technical_correct    = tc
    result.technical_wrong      = tw
    result.technical_skipped    = ts
    result.technical_percentage = tp
    result.hr_total             = ht
    result.hr_correct           = hc
    result.hr_wrong             = hw
    result.hr_skipped           = hs
    result.hr_percentage        = hp
    result.overall_percentage   = overall
    result.grade                = grade
    result.skill_scores         = skill_scores
    db.session.flush()
