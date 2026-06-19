"""
Reports Routes - PDF with full feedback included
"""
from flask import Blueprint, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Interview, InterviewResult, Feedback, Report, User, Resume
import os, traceback

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/generate/<int:interview_id>', methods=['POST'])
@jwt_required()
def generate_report(interview_id):
    user_id   = get_jwt_identity()
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()
    if not interview:
        return jsonify({'message': 'Interview not found'}), 404
    if interview.status != 'completed':
        return jsonify({'message': 'Interview not completed yet'}), 400

    user     = User.query.get(user_id)
    result   = InterviewResult.query.filter_by(interview_id=interview_id).first()
    feedback = Feedback.query.filter_by(interview_id=interview_id).first()

    reports_dir = current_app.config['REPORTS_FOLDER']
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"report_{interview_id}_{user_id}.pdf")

    try:
        _generate_pdf(pdf_path, user, interview, result, feedback)
    except Exception:
        current_app.logger.error(f'PDF error: {traceback.format_exc()}')
        return jsonify({'message': 'Report generation failed'}), 500

    file_size = os.path.getsize(pdf_path)
    report = Report.query.filter_by(interview_id=interview_id).first()
    if not report:
        report = Report(interview_id=interview_id, user_id=user_id)
        db.session.add(report)
    report.report_path = pdf_path
    report.report_size = file_size
    db.session.commit()

    return jsonify({'message': 'Report generated', 'report_id': report.id}), 201


@reports_bp.route('/download/<int:interview_id>', methods=['GET'])
@jwt_required()
def download_report(interview_id):
    user_id = get_jwt_identity()
    report  = Report.query.filter_by(interview_id=interview_id, user_id=user_id).first()
    if not report or not os.path.exists(report.report_path):
        return jsonify({'message': 'Report not found. Generate it first.'}), 404
    report.download_count += 1
    db.session.commit()
    return send_file(report.report_path, mimetype='application/pdf',
                     as_attachment=True, download_name=f'interview_report_{interview_id}.pdf')


@reports_bp.route('/list', methods=['GET'])
@jwt_required()
def list_reports():
    user_id = get_jwt_identity()
    reports = Report.query.filter_by(user_id=user_id).order_by(Report.generated_at.desc()).all()
    return jsonify({'reports': [
        {'id': r.id, 'interview_id': r.interview_id,
         'generated_at': r.generated_at.isoformat(),
         'download_count': r.download_count, 'report_size': r.report_size}
        for r in reports
    ]}), 200


# ── PDF Generator ─────────────────────────────────────────────

def _generate_pdf(pdf_path, user, interview, result, feedback):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    INDIGO    = colors.HexColor('#6366f1')
    DARK      = colors.HexColor('#1e293b')
    EMERALD   = colors.HexColor('#10b981')
    RED       = colors.HexColor('#ef4444')
    YELLOW    = colors.HexColor('#f59e0b')
    LIGHT_BG  = colors.HexColor('#f8fafc')
    INDIGO_BG = colors.HexColor('#eef2ff')

    h1 = ParagraphStyle('H1', parent=styles['Title'], textColor=INDIGO, fontSize=22, spaceAfter=4)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], textColor=DARK, fontSize=13, spaceBefore=14, spaceAfter=6)
    h3 = ParagraphStyle('H3', parent=styles['Heading3'], textColor=INDIGO, fontSize=11, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9.5, spaceAfter=4, leading=14)
    small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#64748b'), spaceAfter=3, leading=13)
    center = ParagraphStyle('Center', parent=body, alignment=TA_CENTER)
    bullet = ParagraphStyle('Bullet', parent=body, leftIndent=12, spaceAfter=3)

    story = []

    # ── Header ──
    story.append(Paragraph("AI Interview Mock Portal", h1))
    story.append(Paragraph("Performance Report", center))
    story.append(HRFlowable(width="100%", thickness=2, color=INDIGO))
    story.append(Spacer(1, 0.4*cm))

    # ── Candidate Info ──
    story.append(Paragraph("Candidate Information", h2))
    info = [
        ["Name", user.full_name,       "Email",      user.email],
        ["Job Role", interview.job_role, "Experience", interview.experience_level],
        ["Date", interview.created_at.strftime('%d %b %Y') if interview.created_at else '—',
         "Status", interview.status.replace('_',' ').title()],
    ]
    t = Table(info, colWidths=[3*cm, 7*cm, 3*cm, 4*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), LIGHT_BG),
        ('FONTNAME', (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0),(2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0),(-1,-1), 9),
        ('GRID', (0,0),(-1,-1), 0.5, colors.lightgrey),
        ('PADDING', (0,0),(-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # ── Score Summary ──
    if result:
        story.append(Paragraph("Performance Summary", h2))
        score_data = [
            ["Round", "Score", "Correct", "Wrong", "Skipped"],
            ["Technical",
             f"{float(result.technical_percentage):.1f}%",
             str(result.technical_correct), str(result.technical_wrong), str(result.technical_skipped)],
            ["HR / Behavioral",
             f"{float(result.hr_percentage):.1f}%",
             str(result.hr_correct), str(result.hr_wrong), str(result.hr_skipped)],
            ["OVERALL",
             f"{float(result.overall_percentage):.1f}%", "", "", f"Grade: {result.grade}"],
        ]
        st = Table(score_data, colWidths=[4.5*cm, 3*cm, 2.5*cm, 2.5*cm, 4.5*cm])
        st.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,0), INDIGO),
            ('TEXTCOLOR', (0,0),(-1,0), colors.white),
            ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,3),(-1,3), INDIGO_BG),
            ('FONTNAME', (0,3),(-1,3), 'Helvetica-Bold'),
            ('GRID', (0,0),(-1,-1), 0.5, colors.lightgrey),
            ('ALIGN', (1,0),(-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0),(-1,-1), 9),
            ('PADDING', (0,0),(-1,-1), 5),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.4*cm))

    # ── AI Feedback ──
    if feedback:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Paragraph("AI-Generated Feedback", h2))

        # Overall Summary
        if feedback.overall_summary:
            story.append(Paragraph("Overall Assessment", h3))
            story.append(Paragraph(feedback.overall_summary, body))
            story.append(Spacer(1, 0.2*cm))

        # Communication
        if feedback.communication_analysis:
            story.append(Paragraph("Communication Analysis", h3))
            story.append(Paragraph(feedback.communication_analysis, body))
            story.append(Spacer(1, 0.2*cm))

        # Strengths
        if feedback.strengths:
            story.append(Paragraph("✓ Strengths", h3))
            for s in feedback.strengths:
                story.append(Paragraph(f"• {s}", bullet))
            story.append(Spacer(1, 0.2*cm))

        # Weaknesses
        if feedback.weaknesses:
            story.append(Paragraph("⚠ Areas for Improvement", h3))
            for w in feedback.weaknesses:
                story.append(Paragraph(f"• {w}", bullet))
            story.append(Spacer(1, 0.2*cm))

        # Technical Gaps
        if feedback.technical_gaps:
            story.append(Paragraph("Technical Gaps to Study", h3))
            for g in feedback.technical_gaps:
                story.append(Paragraph(f"→ {g}", bullet))
            story.append(Spacer(1, 0.2*cm))

        # Resume Suggestions (now stored as dict)
        rs = feedback.resume_suggestions or {}
        if isinstance(rs, dict):
            gaps    = rs.get('resume_gaps', [])
            imprvs  = rs.get('resume_improvements', [])
            focuses = rs.get('focus_areas', [])
        else:
            gaps, imprvs, focuses = [], rs if isinstance(rs, list) else [], []

        if gaps:
            story.append(Paragraph("Missing Skills in Resume", h3))
            for g in gaps:
                if isinstance(g, dict):
                    story.append(Paragraph(f"+ {g.get('skill','')}: {g.get('importance','')}", bullet))
                else:
                    story.append(Paragraph(f"+ {g}", bullet))
            story.append(Spacer(1, 0.2*cm))

        if imprvs:
            story.append(Paragraph("Resume Improvement Suggestions", h3))
            for s in imprvs:
                story.append(Paragraph(f"→ {s}", bullet))
            story.append(Spacer(1, 0.2*cm))

        if focuses:
            story.append(Paragraph("Priority Focus Areas", h3))
            focus_data = [["Topic", "Priority", "Reason"]]
            for f in focuses:
                if isinstance(f, dict):
                    focus_data.append([
                        f.get('topic',''), f.get('priority',''),
                        Paragraph(f.get('reason',''), small)
                    ])
            if len(focus_data) > 1:
                ft = Table(focus_data, colWidths=[4*cm, 2.5*cm, 10.5*cm])
                ft.setStyle(TableStyle([
                    ('BACKGROUND', (0,0),(-1,0), colors.HexColor('#e0e7ff')),
                    ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0),(-1,-1), 8.5),
                    ('GRID', (0,0),(-1,-1), 0.4, colors.lightgrey),
                    ('PADDING', (0,0),(-1,-1), 4),
                    ('VALIGN', (0,0),(-1,-1), 'TOP'),
                ]))
                story.append(ft)
            story.append(Spacer(1, 0.2*cm))

        # Weekly Study Plan
        lr = feedback.learning_roadmap or {}
        weekly = []
        if isinstance(lr, list):
            weekly = lr
        elif isinstance(lr, dict):
            weekly = lr.get('weekly_plan', [])

        if weekly:
            story.append(Paragraph("Recommended Weekly Study Plan", h3))
            for week in weekly:
                if not isinstance(week, dict): continue
                story.append(Paragraph(f"Week {week.get('week','')}: {week.get('focus','')}", 
                    ParagraphStyle('WeekHead', parent=body, fontName='Helvetica-Bold', textColor=INDIGO)))
                for g in (week.get('goals') or []):
                    story.append(Paragraph(f"  ✓ {g}", bullet))
                if week.get('practice'):
                    story.append(Paragraph(f"  Practice: {week['practice']}", small))
            story.append(Spacer(1, 0.2*cm))

        # Interview Tips
        tips = []
        if isinstance(lr, dict):
            tips = lr.get('interview_tips', [])
        if tips:
            story.append(Paragraph("Interview Tips", h3))
            for tip in tips:
                story.append(Paragraph(f"💡 {tip}", bullet))
            story.append(Spacer(1, 0.2*cm))

        # Readiness score
        if feedback.confidence_score:
            story.append(Paragraph(f"Interview Readiness Score: {float(feedback.confidence_score):.0f}%", 
                ParagraphStyle('Ready', parent=body, fontName='Helvetica-Bold', textColor=INDIGO)))
            story.append(Spacer(1, 0.3*cm))

    # ── Violations ──
    from app.models import Violation
    violations = Violation.query.filter_by(interview_id=interview.id).all()
    if violations:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Paragraph("Anti-Cheat Violations Detected", h2))
        v_data = [["#", "Type", "Description", "Time"]]
        for i, v in enumerate(violations, 1):
            v_data.append([
                str(i),
                v.violation_type.replace('_',' ').title(),
                v.description or '—',
                v.occurred_at.strftime('%H:%M:%S') if v.occurred_at else '—',
            ])
        vt = Table(v_data, colWidths=[1*cm, 4*cm, 8.5*cm, 3.5*cm])
        vt.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,0), colors.HexColor('#fee2e2')),
            ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0),(-1,-1), 8.5),
            ('GRID', (0,0),(-1,-1), 0.4, colors.lightgrey),
            ('PADDING', (0,0),(-1,-1), 4),
        ]))
        story.append(vt)

    # ── Footer ──
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph(
        "Generated by AI Interview Mock Portal | Confidential | Powered by Claude AI",
        center
    ))

    doc.build(story)
