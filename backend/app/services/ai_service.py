"""
AI Service - Question Generation & Feedback
Fixed: f-string conflict inside JSON template resolved by building prompt separately
"""
import os, json, re, requests, random, traceback
from flask import current_app
from app import db
from app.models import Feedback

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-haiku-4-5"


def _call_claude(prompt: str, max_tokens: int = 4096) -> str:
    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(CLAUDE_API_URL, headers=headers, json=body, timeout=90)
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Cannot connect to Anthropic API: {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError("Anthropic API timed out after 90 seconds")

    if resp.status_code != 200:
        raise RuntimeError(
            f"Anthropic API error HTTP {resp.status_code}: {resp.text[:400]}"
        )

    data = resp.json()
    if "content" not in data or not data["content"]:
        raise RuntimeError(f"Unexpected API response structure: {str(data)[:300]}")

    return data["content"][0]["text"]


def _parse_json(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    start = cleaned.find('{')
    end   = cleaned.rfind('}')
    if start != -1 and end != -1:
        cleaned = cleaned[start:end+1]
    return json.loads(cleaned)


# ─────────────────────────────────────────────────────────────
# Question Generation
# ─────────────────────────────────────────────────────────────

def generate_interview_questions(
    job_role: str,
    job_description: str,
    experience_level: str,
    skills: list,
    projects: list,
    education: list = None,
    resume_text: str = "",
) -> dict:

    skills_str    = ', '.join(skills[:25]) if skills else 'Not specified'
    projects_str  = '\n'.join(f"- {p}" for p in projects[:6]) if projects else '- No projects listed'
    education_str = ', '.join(str(e) for e in (education or [])[:3]) or 'Not specified'
    resume_snippet = (resume_text or '')[:1200]

    exp_map = {
        'fresher':    'Final year student / 0 years — focus on fundamentals',
        'internship': '0-6 months — basic practical knowledge',
        '1year':      '1 year — some real project exposure',
        '2years':     '2 years — solid hands-on intermediate knowledge',
        '3years':     '3 years — advanced topics',
        '5plus':      '5+ years — architecture and leadership',
    }
    exp_label = exp_map.get(experience_level, experience_level)
    seed = random.randint(10000, 99999)

    # Build JSON template as a plain string (no f-string braces conflict)
    json_template = '''
{
  "technical": [
    {
      "question": "Practical scenario question about the job role and candidate skills?",
      "options": {"A": "option text", "B": "option text", "C": "option text", "D": "option text"},
      "correct": "C",
      "skill_tag": "Specific Technology Name",
      "explanation": "Brief explanation"
    }
  ],
  "hr": [
    {
      "question": "Behavioral/situational question?",
      "options": {"A": "response", "B": "response", "C": "response", "D": "response"},
      "correct": "B",
      "skill_tag": "Communication",
      "explanation": "Why this is best"
    }
  ]
}'''

    prompt = (
        f"You are a senior technical interviewer. Session ID: {seed}\n\n"
        f"CANDIDATE PROFILE:\n"
        f"- Job Role: {job_role}\n"
        f"- Experience Level: {exp_label}\n"
        f"- Skills: {skills_str}\n"
        f"- Education: {education_str}\n"
        f"- Projects:\n{projects_str}\n"
        f"- Resume Excerpt: {resume_snippet}\n\n"
        f"JOB DESCRIPTION:\n{job_description[:800]}\n\n"
        f"TASK: Generate exactly 15 technical MCQ and 10 HR behavioral MCQ questions.\n\n"
        f"RULES:\n"
        f"1. Technical questions MUST use skills the candidate listed: {skills_str}\n"
        f"2. At least 4 questions must reference the candidate's projects\n"
        f"3. Match difficulty to: {exp_label}\n"
        f"4. Ask practical/scenario questions, NOT definitions\n"
        f"5. Each question has 4 options, only ONE correct\n"
        f"6. Vary which option is correct (A/B/C/D equally)\n"
        f"7. skill_tag must be specific (e.g. 'Pandas GroupBy', 'SQL Joins')\n"
        f"8. HR questions must be real workplace behavioral situations\n\n"
        f"Return ONLY valid raw JSON (no markdown, no explanation) in this format:\n"
        + json_template
    )

    try:
        text = _call_claude(prompt, max_tokens=4096)
        data = _parse_json(text)

        technical = [q for q in data.get('technical', [])
                     if all(k in q for k in ['question', 'options', 'correct'])]
        hr        = [q for q in data.get('hr', [])
                     if all(k in q for k in ['question', 'options', 'correct'])]

        current_app.logger.info(
            f"Generated {len(technical)} technical + {len(hr)} HR questions for '{job_role}'"
        )

        if len(technical) < 10:
            technical += _fallback_technical(job_role, skills)[:(15 - len(technical))]
        if len(hr) < 8:
            hr += _fallback_hr(job_role)[:(10 - len(hr))]

        return {'technical': technical[:15], 'hr': hr[:10]}

    except Exception:
        current_app.logger.error(f'Question generation failed:\n{traceback.format_exc()}')
        return {
            'technical': _fallback_technical(job_role, skills),
            'hr':        _fallback_hr(job_role),
        }


# ─────────────────────────────────────────────────────────────
# Feedback Generation  — f-string conflict FIXED
# Build the JSON schema as a plain string, not inside f-string
# ─────────────────────────────────────────────────────────────

def generate_feedback(interview, resume) -> None:
    from app.models import InterviewAnswer, InterviewQuestion

    questions  = InterviewQuestion.query.filter_by(interview_id=interview.id).all()
    answers    = InterviewAnswer.query.filter_by(interview_id=interview.id).all()
    answer_map = {a.question_id: a for a in answers}

    skill_performance = {}
    wrong_qs   = []
    correct_qs = []
    skipped_qs = []

    for q in questions:
        ans = answer_map.get(q.id)
        tag = q.skill_tag or ('HR/Behavioral' if q.question_type == 'hr' else 'General')
        if tag not in skill_performance:
            skill_performance[tag] = {'correct': 0, 'wrong': 0, 'skipped': 0}
        if not ans or ans.selected_answer == 'skipped':
            skill_performance[tag]['skipped'] += 1
            skipped_qs.append(q.question_text[:80])
        elif ans.is_correct:
            skill_performance[tag]['correct'] += 1
            correct_qs.append(tag + ': ' + q.question_text[:60])
        else:
            skill_performance[tag]['wrong'] += 1
            wrong_qs.append(tag + ': ' + q.question_text[:60])

    weak_topics   = [t for t, v in skill_performance.items()
                     if v['wrong'] + v['skipped'] > v['correct']]
    strong_topics = [t for t, v in skill_performance.items()
                     if v['correct'] > v['wrong'] + v['skipped']]

    skills_str   = ', '.join(resume.extracted_skills or []) or 'Not specified'
    projects_str = '; '.join(str(p) for p in (resume.extracted_projects or [])[:4]) or 'None'
    job_role     = interview.job_role
    tech_pct     = float(interview.technical_score)
    hr_pct       = float(interview.hr_score)
    overall_pct  = float(interview.overall_score)
    conf_score   = min(95, max(10, int(overall_pct)))

    # ── Build prompt without f-string inside JSON template ──
    # Use string concatenation so {{ }} are never misinterpreted
    context = (
        "You are an expert career counselor analyzing a mock interview result.\n\n"
        "INTERVIEW RESULTS:\n"
        "- Job Role: " + job_role + "\n"
        "- Experience Level: " + interview.experience_level + "\n"
        "- Technical Score: " + str(round(tech_pct, 1)) + "%\n"
        "- HR Score: " + str(round(hr_pct, 1)) + "%\n"
        "- Overall Score: " + str(round(overall_pct, 1)) + "%\n\n"
        "PERFORMANCE:\n"
        "- Strong Topics: " + (', '.join(strong_topics[:6]) or 'None') + "\n"
        "- Weak Topics: " + (', '.join(weak_topics[:8]) or 'None') + "\n"
        "- Wrong Answers: " + ('; '.join(wrong_qs[:5]) or 'None') + "\n"
        "- Skipped: " + str(len(skipped_qs)) + " questions\n\n"
        "RESUME:\n"
        "- Skills: " + skills_str + "\n"
        "- Projects: " + projects_str + "\n\n"
        "Generate SPECIFIC, ACTIONABLE feedback referencing actual topics from performance.\n\n"
        "Return ONLY valid raw JSON — no markdown fences, no explanation:\n"
    )

    # JSON schema as plain string — no f-string, no {{ }} confusion
    json_schema = (
        '{\n'
        '  "strengths": [\n'
        '    "Specific strength mentioning actual topic they got correct",\n'
        '    "Second strength",\n'
        '    "Third strength"\n'
        '  ],\n'
        '  "weaknesses": [\n'
        '    "Specific weak area with topic name from wrong answers",\n'
        '    "Second weakness"\n'
        '  ],\n'
        '  "technical_gaps": [\n'
        '    "Topic they need to study (from wrong answers)",\n'
        '    "Second gap",\n'
        '    "Third gap"\n'
        '  ],\n'
        '  "focus_areas": [\n'
        '    {"topic": "Topic name", "priority": "High", "reason": "Why important for ' + job_role + '", "current_level": "Needs improvement"},\n'
        '    {"topic": "Topic name", "priority": "Medium", "reason": "Reason", "current_level": "Basic"}\n'
        '  ],\n'
        '  "resume_gaps": [\n'
        '    {"type": "missing_skill", "skill": "Skill missing from resume for ' + job_role + '", "importance": "Why it matters"},\n'
        '    {"type": "missing_skill", "skill": "Another missing skill", "importance": "Why it matters"}\n'
        '  ],\n'
        '  "resume_improvements": [\n'
        '    "Add quantified metrics to project descriptions",\n'
        '    "Include specific technology versions used",\n'
        '    "Add a dedicated Skills section",\n'
        '    "Specific improvement for their profile"\n'
        '  ],\n'
        '  "learning_resources": [\n'
        '    {\n'
        '      "topic": "Topic to learn",\n'
        '      "resources": [\n'
        '        {"name": "Resource name", "url": "https://example.com", "type": "Free"},\n'
        '        {"name": "Another resource", "url": "https://example.com", "type": "Course"}\n'
        '      ],\n'
        '      "estimated_time": "2 weeks"\n'
        '    }\n'
        '  ],\n'
        '  "weekly_study_plan": [\n'
        '    {"week": 1, "focus": "Most critical weak topic", "goals": ["Goal 1", "Goal 2", "Goal 3"], "resources": ["Resource 1", "Resource 2"], "practice": "Practice task for week 1"},\n'
        '    {"week": 2, "focus": "Second weak topic", "goals": ["Goal 1", "Goal 2"], "resources": ["Resource 1"], "practice": "Practice task"},\n'
        '    {"week": 3, "focus": "Third topic", "goals": ["Goal 1", "Goal 2"], "resources": ["Resource 1"], "practice": "Practice task"},\n'
        '    {"week": 4, "focus": "Mock interviews and review", "goals": ["Take 3 mock interviews", "Review all weak topics", "Polish resume"], "resources": ["Pramp.com", "Interviewing.io"], "practice": "Full timed mock interview"}\n'
        '  ],\n'
        '  "interview_tips": [\n'
        '    "Specific tip based on their performance pattern",\n'
        '    "Another actionable tip",\n'
        '    "Third tip"\n'
        '  ],\n'
        '  "communication_analysis": "2-3 sentences about their HR performance at ' + str(round(hr_pct, 1)) + '% and what it means for communication skills",\n'
        '  "overall_summary": "3-4 sentence personalised assessment of what they did well, what needs work, and a specific next step",\n'
        '  "confidence_score": ' + str(conf_score) + '\n'
        '}'
    )

    prompt = context + json_schema

    try:
        current_app.logger.info(f"Calling Claude for feedback on interview {interview.id}...")
        current_app.logger.info(f"Using model: {CLAUDE_MODEL}, API key prefix: {os.getenv('ANTHROPIC_API_KEY','')[:15]}...")
        text = _call_claude(prompt, max_tokens=3000)
        current_app.logger.info(f"Claude response length: {len(text)} chars")

        data = _parse_json(text)
        current_app.logger.info(f"JSON parsed OK, keys: {list(data.keys())}")

        fb = Feedback.query.filter_by(interview_id=interview.id).first()
        if not fb:
            fb = Feedback(interview_id=interview.id)
            db.session.add(fb)

        fb.strengths              = data.get('strengths', [])
        fb.weaknesses             = data.get('weaknesses', [])
        fb.technical_gaps         = data.get('technical_gaps', [])
        fb.communication_analysis = data.get('communication_analysis', '')
        fb.resume_suggestions     = {
            'resume_gaps':         data.get('resume_gaps', []),
            'resume_improvements': data.get('resume_improvements', []),
            'focus_areas':         data.get('focus_areas', []),
        }
        fb.learning_roadmap = {
            'weekly_plan':        data.get('weekly_study_plan', []),
            'learning_resources': data.get('learning_resources', []),
            'interview_tips':     data.get('interview_tips', []),
        }
        fb.overall_summary  = data.get('overall_summary', '')
        fb.confidence_score = float(data.get('confidence_score', 50))
        db.session.commit()
        current_app.logger.info(
            f"Feedback saved for interview {interview.id}. "
            f"summary={bool(fb.overall_summary)}, strengths={len(fb.strengths or [])}"
        )

    except Exception:
        err_msg = traceback.format_exc()
        current_app.logger.error(
            f"Claude feedback FAILED for interview {interview.id}:\n{err_msg}"
        )
        current_app.logger.warning(
            "Falling back to rule-based local feedback generation..."
        )
        # Always generate feedback even if Claude fails
        generate_feedback_local(interview, resume)


# ─────────────────────────────────────────────────────────────
# Role-aware fallback questions
# ─────────────────────────────────────────────────────────────

def _fallback_technical(job_role: str, skills: list) -> list:
    role = job_role.lower()

    if any(k in role for k in ['data', 'analyst', 'science', 'ml', 'ai', 'analytics']):
        pool = [
            {"question": "Which Pandas method removes rows with missing (NaN) values?", "options": {"A": "df.fill()", "B": "df.dropna()", "C": "df.remove_nulls()", "D": "df.clean()"}, "correct": "B", "skill_tag": "Pandas", "explanation": "dropna() removes rows or columns containing NaN."},
            {"question": "What does SQL GROUP BY do?", "options": {"A": "Sorts results ascending", "B": "Filters individual rows", "C": "Groups rows with same value for aggregate functions", "D": "Joins two tables"}, "correct": "C", "skill_tag": "SQL", "explanation": "GROUP BY aggregates rows sharing a value in specified columns."},
            {"question": "In a confusion matrix, what is Precision?", "options": {"A": "TP / (TP + FN)", "B": "TP / (TP + FP)", "C": "TN / (TN + FP)", "D": "FP / (FP + TN)"}, "correct": "B", "skill_tag": "Machine Learning", "explanation": "Precision = True Positives / (True Positives + False Positives)."},
            {"question": "Which chart best shows the distribution of a continuous variable?", "options": {"A": "Pie chart", "B": "Bar chart", "C": "Histogram", "D": "Scatter plot"}, "correct": "C", "skill_tag": "Data Visualization", "explanation": "Histograms show frequency distribution of continuous data."},
            {"question": "What does df.describe() return in Pandas?", "options": {"A": "Column names only", "B": "Data types of each column", "C": "Statistical summary (mean, std, min, max, quartiles)", "D": "First 5 rows"}, "correct": "C", "skill_tag": "Pandas", "explanation": "describe() returns count, mean, std, min, 25%, 50%, 75%, max for numeric columns."},
            {"question": "What is overfitting in machine learning?", "options": {"A": "Model performs well on test data only", "B": "Model memorises training data but fails on unseen data", "C": "Model has too few parameters", "D": "Model trains too slowly"}, "correct": "B", "skill_tag": "Machine Learning", "explanation": "Overfitting: model learns noise in training data and doesn't generalise."},
            {"question": "Which Python library is primarily used for numerical computing?", "options": {"A": "Matplotlib", "B": "Seaborn", "C": "NumPy", "D": "Scikit-learn"}, "correct": "C", "skill_tag": "NumPy", "explanation": "NumPy provides N-dimensional arrays and mathematical functions."},
            {"question": "What does the SQL HAVING clause do?", "options": {"A": "Filters rows before grouping", "B": "Filters groups after GROUP BY", "C": "Sorts grouped results", "D": "Creates a new table"}, "correct": "B", "skill_tag": "SQL", "explanation": "HAVING filters groups created by GROUP BY (like WHERE but for aggregated data)."},
            {"question": "Which scaler maps all features to the range [0, 1]?", "options": {"A": "StandardScaler", "B": "RobustScaler", "C": "MinMaxScaler", "D": "Normalizer"}, "correct": "C", "skill_tag": "Feature Engineering", "explanation": "MinMaxScaler transforms features to [0,1] using (x - min) / (max - min)."},
            {"question": "What is the main purpose of a train-test split?", "options": {"A": "Speed up training", "B": "Evaluate model performance on unseen data to detect overfitting", "C": "Reduce dataset size", "D": "Balance class distribution"}, "correct": "B", "skill_tag": "Machine Learning", "explanation": "Splitting ensures model is tested on data it has never seen during training."},
            {"question": "How do you read a CSV file into a Pandas DataFrame?", "options": {"A": "pd.load_csv('file.csv')", "B": "pd.open('file.csv')", "C": "pd.read_csv('file.csv')", "D": "pd.import_csv('file.csv')"}, "correct": "C", "skill_tag": "Pandas", "explanation": "pd.read_csv() is the standard Pandas function for reading CSV files."},
            {"question": "What is the difference between supervised and unsupervised learning?", "options": {"A": "No difference", "B": "Supervised uses labelled data; unsupervised finds patterns in unlabelled data", "C": "Supervised is always faster", "D": "Unsupervised requires more data"}, "correct": "B", "skill_tag": "Machine Learning", "explanation": "Supervised trains on labelled examples; unsupervised discovers hidden patterns."},
            {"question": "Which SQL join returns only rows that match in BOTH tables?", "options": {"A": "LEFT JOIN", "B": "RIGHT JOIN", "C": "FULL OUTER JOIN", "D": "INNER JOIN"}, "correct": "D", "skill_tag": "SQL", "explanation": "INNER JOIN returns only rows with matches in both tables."},
            {"question": "What is cross-validation used for?", "options": {"A": "Speed up training", "B": "Get reliable model performance estimate using multiple train-test splits", "C": "Increase dataset size", "D": "Select features automatically"}, "correct": "B", "skill_tag": "Machine Learning", "explanation": "Cross-validation averages results over multiple splits for more reliable estimates."},
            {"question": "What does a box plot display?", "options": {"A": "Correlation between variables", "B": "Trend over time", "C": "Median, quartiles and outliers", "D": "Proportion of categories"}, "correct": "C", "skill_tag": "Data Visualization", "explanation": "Box plots show five-number summary: min, Q1, median, Q3, max and outliers."},
        ]
    elif any(k in role for k in ['web', 'frontend', 'backend', 'full', 'react', 'node', 'django', 'flask', 'developer']):
        pool = [
            {"question": "What does React useEffect with empty [] dependency do?", "options": {"A": "Runs on every render", "B": "Runs when any state changes", "C": "Runs once after initial render", "D": "Never runs"}, "correct": "C", "skill_tag": "React Hooks", "explanation": "Empty [] means the effect runs once after mount, like componentDidMount."},
            {"question": "What HTTP status code means 'Not Found'?", "options": {"A": "200", "B": "401", "C": "500", "D": "404"}, "correct": "D", "skill_tag": "HTTP", "explanation": "404 Not Found means the server cannot find the requested resource."},
            {"question": "What does async/await do in JavaScript?", "options": {"A": "Creates parallel threads", "B": "Makes async code look synchronous using Promises", "C": "Prevents all errors", "D": "Speeds up execution"}, "correct": "B", "skill_tag": "JavaScript", "explanation": "async/await is syntactic sugar over Promises for readable async code."},
            {"question": "Which HTTP method partially updates a resource in REST?", "options": {"A": "POST", "B": "PUT", "C": "PATCH", "D": "DELETE"}, "correct": "C", "skill_tag": "REST API", "explanation": "PATCH updates specific fields; PUT replaces the entire resource."},
            {"question": "What is JWT used for?", "options": {"A": "Encrypt passwords", "B": "Store session in database", "C": "Securely transmit user identity as signed token", "D": "Hash user data"}, "correct": "C", "skill_tag": "Authentication", "explanation": "JWT carries user claims and is signed to verify authenticity without server sessions."},
            {"question": "What is the Virtual DOM in React?", "options": {"A": "A browser API", "B": "Lightweight copy of real DOM for efficient updates", "C": "Server-side rendering", "D": "CSS-in-JS library"}, "correct": "B", "skill_tag": "React", "explanation": "React's Virtual DOM is an in-memory representation used to compute minimal real DOM updates."},
            {"question": "What is the difference between == and === in JavaScript?", "options": {"A": "No difference", "B": "=== checks type only", "C": "=== checks both value and type (strict equality)", "D": "== checks type"}, "correct": "C", "skill_tag": "JavaScript", "explanation": "=== is strict equality; == does type coercion before comparison."},
            {"question": "What does SQL JOIN do?", "options": {"A": "Deletes matching rows", "B": "Combines rows from tables based on related column", "C": "Creates a new table", "D": "Filters duplicates"}, "correct": "B", "skill_tag": "SQL", "explanation": "JOIN combines rows from multiple tables based on matching column values."},
            {"question": "What is CORS?", "options": {"A": "Database security feature", "B": "Browser security mechanism controlling cross-origin requests", "C": "Encryption algorithm", "D": "Caching technique"}, "correct": "B", "skill_tag": "Web Security", "explanation": "CORS controls which origins can access resources on your server from a browser."},
            {"question": "What does `git checkout -b feature` do?", "options": {"A": "Deletes branch", "B": "Switches to existing branch", "C": "Creates new branch and switches to it", "D": "Merges branch"}, "correct": "C", "skill_tag": "Git", "explanation": "git checkout -b creates a new branch and immediately switches to it."},
            {"question": "What is the time complexity of hash map lookup?", "options": {"A": "O(n)", "B": "O(log n)", "C": "O(1) average", "D": "O(n²)"}, "correct": "C", "skill_tag": "Data Structures", "explanation": "Hash maps provide O(1) average-case lookup via hash function."},
            {"question": "What does @app.route() do in Flask?", "options": {"A": "Imports a module", "B": "Creates a database table", "C": "Maps a URL to a Python function", "D": "Starts the server"}, "correct": "C", "skill_tag": "Flask", "explanation": "@app.route() registers a URL pattern and maps it to a view function."},
            {"question": "What is localStorage in the browser?", "options": {"A": "Sends data to server", "B": "Stores key-value pairs persistently with no expiry", "C": "Creates a session cookie", "D": "Encrypts data"}, "correct": "B", "skill_tag": "Browser APIs", "explanation": "localStorage persists key-value pairs in the browser with no expiry date."},
            {"question": "What does CSS flex-wrap: wrap do?", "options": {"A": "Makes column layout", "B": "Allows flex items to wrap to next line", "C": "Aligns items center", "D": "Creates a grid"}, "correct": "B", "skill_tag": "CSS", "explanation": "flex-wrap: wrap allows flex items to wrap onto the next line when they overflow."},
            {"question": "What does npm install do?", "options": {"A": "Runs the app", "B": "Creates React app", "C": "Downloads dependencies from package.json", "D": "Updates Node.js"}, "correct": "C", "skill_tag": "Node.js", "explanation": "npm install reads package.json and installs all dependencies into node_modules."},
        ]
    else:
        pool = [
            {"question": "What is the time complexity of binary search?", "options": {"A": "O(n)", "B": "O(log n)", "C": "O(n²)", "D": "O(1)"}, "correct": "B", "skill_tag": "Algorithms", "explanation": "Binary search halves the search space each step."},
            {"question": "What does OOP stand for?", "options": {"A": "Open Object Programming", "B": "Object-Oriented Programming", "C": "Operational Object Process", "D": "Output-Oriented"}, "correct": "B", "skill_tag": "Programming", "explanation": "OOP organises code around objects containing data and methods."},
            {"question": "What is a primary key in a database?", "options": {"A": "First column", "B": "Unique identifier for each row", "C": "Encrypted field", "D": "Foreign reference"}, "correct": "B", "skill_tag": "Database", "explanation": "A primary key uniquely identifies each record in a table."},
            {"question": "What is version control?", "options": {"A": "Track and manage code changes over time", "B": "Upgrading software", "C": "Testing framework", "D": "Deployment tool"}, "correct": "A", "skill_tag": "Git", "explanation": "Version control systems like Git track changes and enable collaboration."},
            {"question": "Which data structure uses LIFO?", "options": {"A": "Queue", "B": "Array", "C": "Stack", "D": "Linked List"}, "correct": "C", "skill_tag": "Data Structures", "explanation": "Stack follows Last In, First Out order."},
            {"question": "What does API stand for?", "options": {"A": "Application Programming Interface", "B": "Automated Program Integration", "C": "Application Process Input", "D": "Advanced Programming Index"}, "correct": "A", "skill_tag": "Web", "explanation": "API allows different software systems to communicate."},
            {"question": "What is recursion?", "options": {"A": "Sorting algorithm", "B": "Function that calls itself", "C": "Database technique", "D": "Type of loop"}, "correct": "B", "skill_tag": "Algorithms", "explanation": "Recursion breaks a problem into smaller sub-problems using self-referential calls."},
            {"question": "Which SQL command retrieves data?", "options": {"A": "INSERT", "B": "UPDATE", "C": "SELECT", "D": "DELETE"}, "correct": "C", "skill_tag": "SQL", "explanation": "SELECT queries and retrieves data from tables."},
            {"question": "What is a compiler?", "options": {"A": "Runs code line by line", "B": "Translates high-level code to machine code", "C": "Debugs programs", "D": "Connects to internet"}, "correct": "B", "skill_tag": "Computer Science", "explanation": "A compiler translates source code into machine-readable binary."},
            {"question": "What is an array?", "options": {"A": "Key-value store", "B": "Collection at contiguous memory locations", "C": "Function type", "D": "Database table"}, "correct": "B", "skill_tag": "Data Structures", "explanation": "Arrays store elements of the same type in contiguous memory."},
            {"question": "What does HTML stand for?", "options": {"A": "Hyper Text Markup Language", "B": "High Text Machine Language", "C": "Hyperlink Text Management", "D": "Home Tool Markup Language"}, "correct": "A", "skill_tag": "Web", "explanation": "HTML is the standard markup language for web pages."},
            {"question": "What is a loop?", "options": {"A": "Stores data", "B": "Repeats code multiple times", "C": "Connects to database", "D": "Defines functions"}, "correct": "B", "skill_tag": "Programming", "explanation": "Loops execute code repeatedly until a condition is met."},
            {"question": "What is a function?", "options": {"A": "Variable type", "B": "Reusable block of code for a specific task", "C": "Database query", "D": "Loop structure"}, "correct": "B", "skill_tag": "Programming", "explanation": "Functions encapsulate logic that can be reused throughout a program."},
            {"question": "What is an algorithm?", "options": {"A": "Programming language", "B": "Step-by-step procedure to solve a problem", "C": "Database system", "D": "Hardware component"}, "correct": "B", "skill_tag": "Computer Science", "explanation": "An algorithm is a finite sequence of instructions to solve a specific problem."},
            {"question": "What is the purpose of an index in a database?", "options": {"A": "Store backups", "B": "Speed up data retrieval", "C": "Encrypt data", "D": "Normalize tables"}, "correct": "B", "skill_tag": "Database", "explanation": "Indexes speed up SELECT queries at the cost of extra storage."},
        ]

    random.shuffle(pool)
    return pool[:15]


def _fallback_hr(job_role: str) -> list:
    pool = [
        {"question": "You're given a task you've never done before. What's your approach?", "options": {"A": "Refuse until fully trained", "B": "Research, break into steps, ask for help when stuck, then deliver", "C": "Do it without preparation", "D": "Ask someone else"}, "correct": "B", "skill_tag": "Problem Solving", "explanation": "Structured approach to unfamiliar work demonstrates professionalism."},
        {"question": "How do you handle receiving critical feedback on your work?", "options": {"A": "Get defensive and explain why", "B": "Ignore it completely", "C": "Listen, reflect, ask questions, and use it to improve", "D": "Agree without actually changing"}, "correct": "C", "skill_tag": "Feedback", "explanation": "Actively using feedback shows professional maturity."},
        {"question": "A teammate is missing deadlines affecting your work. What do you do?", "options": {"A": "Complain to manager immediately", "B": "Do their work silently", "C": "Have a private, respectful conversation to understand their challenges", "D": "Ignore it"}, "correct": "C", "skill_tag": "Teamwork", "explanation": "Direct empathetic communication resolves most team issues."},
        {"question": "Multiple urgent tasks arrive at once. How do you prioritize?", "options": {"A": "Do the easiest first", "B": "Pick randomly", "C": "Assess impact and deadlines, communicate priority to stakeholders", "D": "Work on all simultaneously"}, "correct": "C", "skill_tag": "Time Management", "explanation": "Structured prioritization prevents bottlenecks and missed deadlines."},
        {"question": "You find a critical bug in production just before leaving. What do you do?", "options": {"A": "Leave it for tomorrow", "B": "Fix alone without telling anyone", "C": "Inform team, assess severity, decide action collaboratively", "D": "Blame whoever wrote it"}, "correct": "C", "skill_tag": "Accountability", "explanation": "Transparency and team collaboration in critical situations is essential."},
        {"question": "How do you keep your skills updated?", "options": {"A": "Only when forced by employer", "B": "College education is enough", "C": "Read blogs, build side projects, take courses, follow industry trends", "D": "Copy others' solutions"}, "correct": "C", "skill_tag": "Continuous Learning", "explanation": "Proactive self-learning is critical in technology."},
        {"question": "You disagree with your manager's technical decision. What do you do?", "options": {"A": "Refuse to implement", "B": "Follow silently even if wrong", "C": "Raise concerns professionally with data, then align with final decision", "D": "Escalate to HR"}, "correct": "C", "skill_tag": "Communication", "explanation": "Expressing concerns respectfully while aligning shows maturity."},
        {"question": "A project requirement is vague. How do you proceed?", "options": {"A": "Make assumptions and build", "B": "Wait for perfect specs", "C": "Ask clarifying questions, document understanding, confirm with stakeholders", "D": "Reject the project"}, "correct": "C", "skill_tag": "Communication", "explanation": "Clarifying requirements early prevents costly rework."},
        {"question": "You made a mistake that affected the team's deadline. How do you handle it?", "options": {"A": "Hide it hoping no one notices", "B": "Blame external factors", "C": "Acknowledge immediately, explain impact, propose recovery plan", "D": "Quietly fix without telling anyone"}, "correct": "C", "skill_tag": "Ownership", "explanation": "Taking ownership and proposing solutions demonstrates professionalism."},
        {"question": "Where do you see yourself in 2-3 years?", "options": {"A": "Same role exactly", "B": "Senior technical or leadership role contributing to meaningful projects", "C": "No specific plans", "D": "Completely different field"}, "correct": "B", "skill_tag": "Career Goals", "explanation": "Employers value ambitious candidates with realistic growth goals."},
    ]
    random.shuffle(pool)
    return pool[:10]


# ─────────────────────────────────────────────────────────────
# Rule-based fallback feedback (works without Claude API)
# ─────────────────────────────────────────────────────────────

def generate_feedback_local(interview, resume) -> None:
    """
    Generates feedback using pure logic — no API call needed.
    Called automatically when Claude API fails.
    """
    from app.models import InterviewAnswer, InterviewQuestion

    questions  = InterviewQuestion.query.filter_by(interview_id=interview.id).all()
    answers    = InterviewAnswer.query.filter_by(interview_id=interview.id).all()
    answer_map = {a.question_id: a for a in answers}

    skill_performance = {}
    wrong_tags   = []
    correct_tags = []

    for q in questions:
        ans = answer_map.get(q.id)
        tag = q.skill_tag or ('HR' if q.question_type == 'hr' else 'General')
        if tag not in skill_performance:
            skill_performance[tag] = {'correct': 0, 'wrong': 0, 'skipped': 0}
        if not ans or ans.selected_answer == 'skipped':
            skill_performance[tag]['skipped'] += 1
        elif ans.is_correct:
            skill_performance[tag]['correct'] += 1
            correct_tags.append(tag)
        else:
            skill_performance[tag]['wrong'] += 1
            wrong_tags.append(tag)

    tech_pct    = float(interview.technical_score)
    hr_pct      = float(interview.hr_score)
    overall_pct = float(interview.overall_score)
    job_role    = interview.job_role
    skills      = resume.extracted_skills or []

    weak_topics   = list(dict.fromkeys(wrong_tags))[:6]
    strong_topics = list(dict.fromkeys(correct_tags))[:4]

    # Build strengths
    strengths = []
    if tech_pct >= 60:
        strengths.append(f"Good technical foundation for {job_role} — scored {tech_pct:.0f}% in technical round")
    if hr_pct >= 60:
        strengths.append(f"Strong behavioral and communication skills — scored {hr_pct:.0f}% in HR round")
    if strong_topics:
        strengths.append(f"Demonstrated knowledge in: {', '.join(strong_topics[:3])}")
    if skills:
        strengths.append(f"Relevant skills on resume: {', '.join(skills[:4])}")
    if not strengths:
        strengths = ["Completed the full interview — good persistence", "Showed willingness to attempt all questions"]

    # Build weaknesses
    weaknesses = []
    if tech_pct < 60:
        weaknesses.append(f"Technical score ({tech_pct:.0f}%) needs improvement — focus on core {job_role} concepts")
    if hr_pct < 60:
        weaknesses.append(f"HR/behavioral score ({hr_pct:.0f}%) is low — practise STAR-format answers")
    if weak_topics:
        weaknesses.append(f"Struggled with: {', '.join(weak_topics[:3])}")
    if not weaknesses:
        weaknesses = ["Review edge cases and advanced topics", "Practise under time pressure"]

    # Technical gaps
    tech_gaps = weak_topics[:5] if weak_topics else ["Core concepts", "Problem solving", "Fundamentals"]

    # Focus areas
    focus_areas = []
    for tag in weak_topics[:3]:
        focus_areas.append({
            "topic": tag,
            "priority": "High",
            "reason": f"You got questions wrong in {tag} — critical for {job_role}",
            "current_level": "Needs improvement"
        })
    for tag in strong_topics[:2]:
        focus_areas.append({
            "topic": tag,
            "priority": "Low",
            "reason": f"You did well in {tag} — maintain this knowledge",
            "current_level": "Good"
        })

    # Resume gaps based on job role
    role_lower = job_role.lower()
    resume_gaps = []
    if 'frontend' in role_lower or 'web' in role_lower:
        needed = ['React', 'TypeScript', 'CSS', 'REST APIs', 'Git']
    elif 'data' in role_lower or 'analyst' in role_lower:
        needed = ['Python', 'SQL', 'Pandas', 'Data Visualization', 'Statistics']
    elif 'backend' in role_lower:
        needed = ['Node.js', 'SQL', 'REST APIs', 'Docker', 'System Design']
    elif 'full' in role_lower:
        needed = ['React', 'Node.js', 'SQL', 'REST APIs', 'Docker']
    else:
        needed = ['Git', 'Problem Solving', 'Data Structures', 'Algorithms', 'Communication']

    skills_lower = [s.lower() for s in skills]
    for skill in needed:
        if skill.lower() not in skills_lower:
            resume_gaps.append({
                "type": "missing_skill",
                "skill": skill,
                "importance": f"{skill} is commonly required for {job_role} roles"
            })

    # Resume improvements
    resume_improvements = [
        "Add quantified metrics to projects (e.g. 'improved load time by 40%')",
        "Include specific versions of technologies used (e.g. 'React 18', 'Python 3.11')",
        "Add a dedicated Skills section organized by category",
        "Write a 2-3 line professional summary at the top matching the job role",
    ]

    # Learning resources by role
    if 'frontend' in role_lower or 'web' in role_lower:
        resources = [
            {"topic": "JavaScript & React", "resources": [
                {"name": "freeCodeCamp", "url": "https://www.freecodecamp.org", "type": "Free"},
                {"name": "React Docs", "url": "https://react.dev", "type": "Free"},
            ], "estimated_time": "3 weeks"},
            {"topic": "CSS & Responsive Design", "resources": [
                {"name": "CSS-Tricks", "url": "https://css-tricks.com", "type": "Free"},
                {"name": "Flexbox Froggy", "url": "https://flexboxfroggy.com", "type": "Free"},
            ], "estimated_time": "1 week"},
        ]
    elif 'data' in role_lower or 'analyst' in role_lower:
        resources = [
            {"topic": "Python & Pandas", "resources": [
                {"name": "Kaggle Learn Python", "url": "https://www.kaggle.com/learn/python", "type": "Free"},
                {"name": "Pandas Docs", "url": "https://pandas.pydata.org/docs", "type": "Free"},
            ], "estimated_time": "2 weeks"},
            {"topic": "SQL", "resources": [
                {"name": "SQLZoo", "url": "https://sqlzoo.net", "type": "Free"},
                {"name": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial", "type": "Free"},
            ], "estimated_time": "1 week"},
        ]
    else:
        resources = [
            {"topic": "Data Structures & Algorithms", "resources": [
                {"name": "LeetCode", "url": "https://leetcode.com", "type": "Free/Paid"},
                {"name": "GeeksforGeeks", "url": "https://www.geeksforgeeks.org", "type": "Free"},
            ], "estimated_time": "4 weeks"},
        ]

    # Weekly plan
    study_topics = weak_topics[:3] if weak_topics else ["Core concepts", "Problem solving", "Interview prep"]
    weekly_plan = [
        {
            "week": 1,
            "focus": study_topics[0] if len(study_topics) > 0 else "Core fundamentals",
            "goals": ["Study core concepts", "Complete 10 practice problems", "Review official documentation"],
            "resources": ["YouTube tutorials", "Official docs", "GeeksforGeeks"],
            "practice": "Solve 5 beginner-level problems on LeetCode or similar"
        },
        {
            "week": 2,
            "focus": study_topics[1] if len(study_topics) > 1 else "Hands-on projects",
            "goals": ["Build a small project", "Apply learned concepts", "Document your code"],
            "resources": ["GitHub", "freeCodeCamp", "YouTube"],
            "practice": "Build one complete mini-project using the week's topic"
        },
        {
            "week": 3,
            "focus": study_topics[2] if len(study_topics) > 2 else "Interview patterns",
            "goals": ["Study common interview patterns", "Practice timed questions", "Review weak areas"],
            "resources": ["InterviewBit", "NeetCode", "Pramp.com"],
            "practice": "Take a timed 30-minute quiz on all weak topics"
        },
        {
            "week": 4,
            "focus": "Full mock interviews and resume polish",
            "goals": ["Take 3 full mock interviews", "Update resume with new skills", "Review all weak topics"],
            "resources": ["Pramp.com", "Interviewing.io", "LinkedIn"],
            "practice": "Complete a full timed mock interview and review every mistake"
        }
    ]

    # Interview tips
    interview_tips = [
        "Read each question carefully — don't rush, you have 20 seconds",
        "Eliminate obviously wrong options first to narrow down choices",
        "For HR questions, always choose the most professional and team-oriented response",
        f"Review {', '.join(weak_topics[:2]) if weak_topics else 'core concepts'} before your next attempt",
        "Practice under time pressure — set a 20-second timer when studying",
    ]

    # Communication analysis
    if hr_pct >= 70:
        comm = f"Your HR score of {hr_pct:.0f}% shows strong communication and behavioral awareness. You understand professional workplace dynamics well."
    elif hr_pct >= 50:
        comm = f"Your HR score of {hr_pct:.0f}% is average. Focus on STAR-format answers (Situation, Task, Action, Result) for behavioral questions to improve significantly."
    else:
        comm = f"Your HR score of {hr_pct:.0f}% needs attention. Study common behavioral interview questions and practise structured responses using the STAR method."

    # Overall summary
    if overall_pct >= 70:
        summary = f"Great performance on your {job_role} interview with {overall_pct:.0f}% overall! Your technical knowledge is solid. Focus on the weak areas identified to reach the next level."
    elif overall_pct >= 50:
        summary = f"Decent effort on the {job_role} interview with {overall_pct:.0f}% overall. You have a foundation to build on. Prioritise the technical gaps and practise consistently for 4 weeks."
    else:
        summary = f"Your {job_role} interview scored {overall_pct:.0f}% — there is significant room to grow. Don't be discouraged: follow the 4-week study plan below, focus on the weak topics, and retake the interview. Consistent practice will make a big difference."

    # Save to DB
    fb = Feedback.query.filter_by(interview_id=interview.id).first()
    if not fb:
        fb = Feedback(interview_id=interview.id)
        db.session.add(fb)

    fb.strengths              = strengths
    fb.weaknesses             = weaknesses
    fb.technical_gaps         = tech_gaps
    fb.communication_analysis = comm
    fb.resume_suggestions     = {
        'resume_gaps':         resume_gaps,
        'resume_improvements': resume_improvements,
        'focus_areas':         focus_areas,
    }
    fb.learning_roadmap = {
        'weekly_plan':        weekly_plan,
        'learning_resources': resources,
        'interview_tips':     interview_tips,
    }
    fb.overall_summary  = summary
    fb.confidence_score = float(min(95, max(10, overall_pct)))
    db.session.commit()
