"""
Resume Upload & Parsing Routes + AI Service
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db
from app.models import Resume
import os
import re
import json

resume_bp = Blueprint('resume', __name__)

# ── helpers ──────────────────────────────────────────────────


def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def extract_text_from_pdf(path):
    """Extract raw text from PDF using pdfplumber."""
    try:
        import pdfplumber
        text = ''
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
        return text
    except Exception as e:
        current_app.logger.error(f'PDF extraction error: {e}')
        return ''


def extract_text_from_docx(path):
    """Extract raw text from DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(path)
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        current_app.logger.error(f'DOCX extraction error: {e}')
        return ''


# ── NLP-based skill extraction ────────────────────────────────

KNOWN_TECH_SKILLS = [
    'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
    'node', 'express', 'flask', 'django', 'fastapi', 'spring', 'docker',
    'kubernetes', 'aws', 'azure', 'gcp', 'sql', 'mysql', 'postgresql',
    'mongodb', 'redis', 'elasticsearch', 'git', 'ci/cd', 'jenkins', 'linux',
    'html', 'css', 'tailwind', 'bootstrap', 'rest', 'graphql', 'kafka',
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp',
    'data analysis', 'pandas', 'numpy', 'opencv', 'c++', 'c#', 'go', 'rust',
    'kotlin', 'swift', 'flutter', 'react native', 'firebase', 'nextjs',
    'microservices', 'agile', 'scrum', 'devops', 'terraform', 'hadoop',
    'spark', 'tableau', 'power bi', 'excel', 'photoshop', 'figma',
]

SECTION_HEADERS = {
    'skills': ['skills', 'technical skills', 'core competencies', 'technologies'],
    'experience': ['experience', 'work experience', 'employment', 'professional experience'],
    'projects': ['projects', 'personal projects', 'academic projects', 'key projects'],
    'education': ['education', 'academic background', 'qualifications'],
    'certifications': ['certifications', 'certificates', 'achievements', 'courses'],
}


def parse_resume_text(text):
    """NLP-based extraction of structured data from resume text."""
    text_lower = text.lower()
    result = {
        'skills': [],
        'experience': [],
        'projects': [],
        'education': [],
        'certifications': [],
    }

    # Extract known tech skills by scanning
    found_skills = set()
    for skill in KNOWN_TECH_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill.title())
    result['skills'] = list(found_skills)

    # Split text into lines for section parsing
    lines = text.split('\n')
    current_section = None
    section_content = {k: [] for k in SECTION_HEADERS}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        line_lower = stripped.lower()
        matched_section = None
        for section, headers in SECTION_HEADERS.items():
            if any(line_lower == h or line_lower.startswith(h) for h in headers):
                matched_section = section
                break
        if matched_section:
            current_section = matched_section
        elif current_section:
            section_content[current_section].append(stripped)

    result['experience'] = section_content['experience'][:10]
    result['projects'] = section_content['projects'][:10]
    result['education'] = section_content['education'][:5]
    result['certifications'] = section_content['certifications'][:10]

    return result


# ── Routes ────────────────────────────────────────────────────

@resume_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    """Upload and parse resume (PDF or DOCX)."""
    user_id = get_jwt_identity()

    if 'resume' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400

    file = request.files['resume']
    if not file.filename:
        return jsonify({'message': 'Empty filename'}), 400
    if not allowed_file(file.filename):
        return jsonify({'message': 'Only PDF and DOCX files are allowed'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower()

    # Save file
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    import uuid
    unique_name = f"{user_id}_{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(upload_dir, unique_name)
    file.save(save_path)
    file_size = os.path.getsize(save_path)

    # Create DB record
    resume = Resume(
        user_id=user_id,
        file_name=filename,
        file_path=save_path,
        file_size=file_size,
        file_type=ext,
        parse_status='processing',
    )
    db.session.add(resume)
    db.session.commit()

    # Parse resume
    try:
        if ext == 'pdf':
            text = extract_text_from_pdf(save_path)
        else:
            text = extract_text_from_docx(save_path)

        parsed = parse_resume_text(text)

        resume.parsed_text = text[:10000]  # Limit stored text
        resume.extracted_skills = parsed['skills']
        resume.extracted_experience = parsed['experience']
        resume.extracted_projects = parsed['projects']
        resume.extracted_education = parsed['education']
        resume.extracted_certifications = parsed['certifications']
        resume.parse_status = 'completed'
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Resume parse error: {e}')
        resume.parse_status = 'failed'
        db.session.commit()
        return jsonify({'message': 'Resume uploaded but parsing failed', 'resume': resume.to_dict()}), 207

    return jsonify({
        'message': 'Resume uploaded and parsed successfully',
        'resume': resume.to_dict(),
    }), 201


@resume_bp.route('/list', methods=['GET'])
@jwt_required()
def list_resumes():
    """List all resumes for the current user."""
    user_id = get_jwt_identity()
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).all()
    return jsonify({'resumes': [r.to_dict() for r in resumes]}), 200


@resume_bp.route('/<int:resume_id>', methods=['GET'])
@jwt_required()
def get_resume(resume_id):
    """Get a specific resume."""
    user_id = get_jwt_identity()
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return jsonify({'message': 'Resume not found'}), 404
    return jsonify({'resume': resume.to_dict()}), 200
