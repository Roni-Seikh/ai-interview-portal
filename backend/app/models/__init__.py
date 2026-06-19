"""
SQLAlchemy ORM Models
"""
from datetime import datetime
from app import db
import json


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(500))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    role = db.Column(db.Enum('student', 'admin'), default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    resumes = db.relationship('Resume', backref='user', lazy=True)
    interviews = db.relationship('Interview', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'profile_picture': self.profile_picture,
            'phone': self.phone,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class OTPToken(db.Model):
    __tablename__ = 'otp_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(10), nullable=False)
    token_type = db.Column(db.Enum('email_verify', 'password_reset'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    file_type = db.Column(db.Enum('pdf', 'docx'), nullable=False)
    parsed_text = db.Column(db.Text)
    extracted_skills = db.Column(db.JSON)
    extracted_experience = db.Column(db.JSON)
    extracted_projects = db.Column(db.JSON)
    extracted_education = db.Column(db.JSON)
    extracted_certifications = db.Column(db.JSON)
    parse_status = db.Column(db.Enum('pending', 'processing', 'completed', 'failed'), default='pending')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'extracted_skills': self.extracted_skills,
            'extracted_experience': self.extracted_experience,
            'extracted_projects': self.extracted_projects,
            'extracted_education': self.extracted_education,
            'parse_status': self.parse_status,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False)
    job_role = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    experience_level = db.Column(db.Enum('fresher', 'internship', '1year', '2years', '3years', '5plus'), nullable=False)
    status = db.Column(db.Enum('setup', 'technical_round', 'hr_round', 'completed', 'abandoned'), default='setup')
    technical_start_time = db.Column(db.DateTime)
    technical_end_time = db.Column(db.DateTime)
    hr_start_time = db.Column(db.DateTime)
    hr_end_time = db.Column(db.DateTime)
    total_duration_seconds = db.Column(db.Integer, default=0)
    technical_score = db.Column(db.Numeric(5, 2), default=0)
    hr_score = db.Column(db.Numeric(5, 2), default=0)
    overall_score = db.Column(db.Numeric(5, 2), default=0)
    violation_count = db.Column(db.Integer, default=0)
    auto_submitted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = db.relationship('InterviewQuestion', backref='interview', lazy=True)
    answers = db.relationship('InterviewAnswer', backref='interview', lazy=True)
    result = db.relationship('InterviewResult', backref='interview', uselist=False)
    feedback = db.relationship('Feedback', backref='interview', uselist=False)
    violations = db.relationship('Violation', backref='interview', lazy=True)
    report = db.relationship('Report', backref='interview', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'job_role': self.job_role,
            'experience_level': self.experience_level,
            'status': self.status,
            'technical_score': float(self.technical_score),
            'hr_score': float(self.hr_score),
            'overall_score': float(self.overall_score),
            'violation_count': self.violation_count,
            'auto_submitted': self.auto_submitted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False)
    question_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id', ondelete='SET NULL'))
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.Enum('A', 'B', 'C', 'D'), nullable=False)
    question_type = db.Column(db.Enum('technical', 'hr'), nullable=False)
    round_number = db.Column(db.Integer, default=1)
    question_order = db.Column(db.Integer, nullable=False)
    time_limit_seconds = db.Column(db.Integer, default=20)
    skill_tag = db.Column(db.String(100))

    def to_dict(self, include_answer=False):
        data = {
            'id': self.id,
            'question_text': self.question_text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'question_type': self.question_type,
            'round_number': self.round_number,
            'question_order': self.question_order,
            'time_limit_seconds': self.time_limit_seconds,
            'skill_tag': self.skill_tag,
        }
        if include_answer:
            data['correct_answer'] = self.correct_answer
        return data


class InterviewAnswer(db.Model):
    __tablename__ = 'interview_answers'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('interview_questions.id', ondelete='CASCADE'), nullable=False)
    selected_answer = db.Column(db.Enum('A', 'B', 'C', 'D', 'skipped'), default='skipped')
    is_correct = db.Column(db.Boolean, default=False)
    time_taken_seconds = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)


class InterviewResult(db.Model):
    __tablename__ = 'interview_results'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False, unique=True)
    technical_total = db.Column(db.Integer, default=0)
    technical_correct = db.Column(db.Integer, default=0)
    technical_wrong = db.Column(db.Integer, default=0)
    technical_skipped = db.Column(db.Integer, default=0)
    technical_percentage = db.Column(db.Numeric(5, 2), default=0)
    hr_total = db.Column(db.Integer, default=0)
    hr_correct = db.Column(db.Integer, default=0)
    hr_wrong = db.Column(db.Integer, default=0)
    hr_skipped = db.Column(db.Integer, default=0)
    hr_percentage = db.Column(db.Numeric(5, 2), default=0)
    overall_percentage = db.Column(db.Numeric(5, 2), default=0)
    grade = db.Column(db.Enum('A+', 'A', 'B+', 'B', 'C', 'D', 'F'), default='F')
    skill_scores = db.Column(db.JSON)
    time_analysis = db.Column(db.JSON)
    percentile = db.Column(db.Numeric(5, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'interview_id': self.interview_id,
            'technical_total': self.technical_total,
            'technical_correct': self.technical_correct,
            'technical_wrong': self.technical_wrong,
            'technical_skipped': self.technical_skipped,
            'technical_percentage': float(self.technical_percentage),
            'hr_total': self.hr_total,
            'hr_correct': self.hr_correct,
            'hr_wrong': self.hr_wrong,
            'hr_skipped': self.hr_skipped,
            'hr_percentage': float(self.hr_percentage),
            'overall_percentage': float(self.overall_percentage),
            'grade': self.grade,
            'skill_scores': self.skill_scores,
            'time_analysis': self.time_analysis,
            'percentile': float(self.percentile),
        }


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False, unique=True)
    strengths = db.Column(db.JSON)
    weaknesses = db.Column(db.JSON)
    technical_gaps = db.Column(db.JSON)
    communication_analysis = db.Column(db.Text)
    resume_suggestions = db.Column(db.JSON)
    learning_roadmap = db.Column(db.JSON)
    overall_summary = db.Column(db.Text)
    confidence_score = db.Column(db.Numeric(5, 2), default=0)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'technical_gaps': self.technical_gaps,
            'communication_analysis': self.communication_analysis,
            'resume_suggestions': self.resume_suggestions,
            'learning_roadmap': self.learning_roadmap,
            'overall_summary': self.overall_summary,
            'confidence_score': float(self.confidence_score),
        }


class Violation(db.Model):
    __tablename__ = 'violations'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    violation_type = db.Column(db.Enum(
        'tab_switch', 'window_minimize', 'camera_off',
        'copy_attempt', 'paste_attempt', 'right_click',
        'keyboard_shortcut', 'fullscreen_exit', 'suspicious_activity'
    ), nullable=False)
    description = db.Column(db.String(500))
    screenshot_path = db.Column(db.String(500))
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    report_path = db.Column(db.String(500))
    report_size = db.Column(db.Integer, default=0)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)


class QuestionBank(db.Model):
    __tablename__ = 'question_bank'

    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.Enum('A', 'B', 'C', 'D'), nullable=False)
    explanation = db.Column(db.Text)
    question_type = db.Column(db.Enum('technical', 'hr', 'behavioral'), nullable=False)
    difficulty = db.Column(db.Enum('easy', 'medium', 'hard'), default='medium')
    skill_tags = db.Column(db.JSON)
    job_roles = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
