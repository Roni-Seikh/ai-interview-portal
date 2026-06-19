# 🎯 AI Resume Interview Mock Portal

A production-ready full-stack AI-powered interview preparation platform for students.  
Practice mock interviews tailored to your resume, get instant AI feedback, track progress, and download detailed PDF reports.

---

## 🚀 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Tailwind CSS, Framer Motion, React Hook Form, Recharts |
| Backend | Python Flask, Flask-JWT-Extended, SQLAlchemy ORM |
| Database | MySQL (phpMyAdmin compatible) |
| AI | Anthropic Claude API (question generation + feedback) |
| PDF | ReportLab |
| Email | Flask-Mail (Gmail SMTP) |
| Auth | JWT + bcrypt + OTP |

---

## 📁 Project Structure

```
ai-interview-portal/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.js
│   │   │   ├── LoginPage.js
│   │   │   ├── RegisterPage.js
│   │   │   ├── ForgotPasswordPage.js
│   │   │   ├── DashboardPage.js
│   │   │   ├── StartInterviewPage.js
│   │   │   ├── InterviewPage.js
│   │   │   ├── ResultsPage.js
│   │   │   ├── HistoryPage.js
│   │   │   ├── ProfilePage.js
│   │   │   └── AdminPage.js
│   │   ├── components/common/
│   │   │   └── Navbar.js
│   │   ├── context/
│   │   │   └── AuthContext.js
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.js
│   │   ├── index.js
│   │   └── index.css
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   └── .env
│
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory
│   │   ├── config.py            # Configuration classes
│   │   ├── models/
│   │   │   └── __init__.py      # All SQLAlchemy models
│   │   ├── routes/
│   │   │   ├── auth.py          # Register, login, OTP
│   │   │   ├── resume.py        # Upload & parse
│   │   │   ├── interview.py     # Setup, questions, submit
│   │   │   ├── results.py       # Results + Q&A review
│   │   │   ├── reports.py       # PDF generation & download
│   │   │   ├── dashboard.py     # Stats & trend
│   │   │   └── admin.py         # Admin panel APIs
│   │   ├── services/
│   │   │   └── ai_service.py    # Claude API integration
│   │   └── utils/
│   │       ├── security.py      # bcrypt, validators
│   │       └── validators.py
│   ├── run.py
│   ├── requirements.txt
│   └── .env.example
│
└── database/
    └── schema.sql               # Complete MySQL schema
```

---

## ⚡ Quick Setup

### 1. Clone & Setup

```bash
git clone <repo>
cd ai-interview-portal
```

### 2. Database Setup (MySQL / phpMyAdmin)

1. Open phpMyAdmin → Create database: `ai_interview_portal`
2. Import `database/schema.sql`

Or via CLI:
```sql
mysql -u root -p < database/schema.sql
```

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your MySQL credentials, Gmail, and Anthropic API key

flask init-db     # Create tables
flask seed-db     # Create default admin user
python run.py     # Start on http://localhost:5000
```

### 4. Frontend Setup

```bash
cd frontend
npm install
# Edit .env if backend URL is different
npm start         # Opens http://localhost:3000
```

---

## 🔐 Environment Variables

### Backend (`backend/.env`)

```env
FLASK_ENV=development
SECRET_KEY=your-super-secret-key
JWT_SECRET_KEY=your-jwt-secret

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=ai_interview_portal

# Gmail SMTP (enable App Passwords in Google Account)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your_app_password

# Claude AI
ANTHROPIC_API_KEY=sk-ant-...

# CORS
CORS_ORIGINS=http://localhost:3000
```

### Frontend (`frontend/.env`)

```env
REACT_APP_API_URL=http://localhost:5000/api
```

---

## 🎮 Features

### Authentication
- Register with email OTP verification
- Login with JWT (access + refresh tokens)
- Remember me (30-day token)
- Forgot password with OTP reset

### Interview Flow
1. Upload resume (PDF/DOCX) → AI parses skills
2. Enter job role, description, experience level
3. Claude generates 15 Technical + 10 HR MCQs
4. **Round 1:** Technical MCQs (20s per question)
5. **Round 2:** HR MCQs (20s per question)
6. Scores calculated, AI feedback generated
7. Download PDF report

### Anti-Cheat System
- ✅ Webcam mandatory (auto-violation if off)
- ✅ Tab switch detection (Browser Visibility API)
- ✅ Right-click blocked
- ✅ Copy/Paste blocked
- ✅ Keyboard shortcuts blocked (F12, Ctrl+Shift+I, etc.)
- ✅ Fullscreen enforced
- ✅ Auto-submit after 3 violations
- ✅ All violations stored in DB

### Results & Analytics
- Technical, HR, Overall scores with grade (A+ to F)
- Skill-wise radar chart
- Topic-wise bar chart
- Full Q&A review with correct answers highlighted
- AI-generated: strengths, weaknesses, technical gaps
- Resume suggestions (skills to add, keywords, projects)
- 4-week learning roadmap

### Admin Panel
- User management (activate/deactivate)
- All interviews table
- Violations log
- Analytics overview

---

## 🔌 API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/verify-email` | Verify OTP |
| POST | `/api/auth/login` | Login → JWT |
| POST | `/api/auth/refresh` | Refresh token |
| POST | `/api/auth/forgot-password` | Send reset OTP |
| POST | `/api/auth/reset-password` | Reset password |
| GET  | `/api/auth/me` | Get current user |
| PUT  | `/api/auth/update-profile` | Update profile |

### Resume
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/resume/upload` | Upload + parse |
| GET  | `/api/resume/list` | List resumes |
| GET  | `/api/resume/:id` | Get resume |

### Interview
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/interview/setup` | Create interview + generate questions |
| GET  | `/api/interview/:id/questions/:round` | Get questions (technical/hr) |
| POST | `/api/interview/:id/submit-round` | Submit round answers |
| POST | `/api/interview/:id/complete` | Finalize + calculate scores |
| POST | `/api/interview/:id/violation` | Log anti-cheat violation |
| GET  | `/api/interview/history` | Interview history |

### Results & Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/results/:id` | Full results + feedback |
| POST | `/api/reports/generate/:id` | Generate PDF |
| GET  | `/api/reports/download/:id` | Download PDF |
| GET  | `/api/reports/list` | List reports |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/dashboard/stats` | Stats + trend data |

### Admin (admin role required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/admin/users` | List users |
| PUT  | `/api/admin/users/:id/toggle` | Toggle active |
| GET  | `/api/admin/interviews` | All interviews |
| GET  | `/api/admin/violations` | All violations |
| GET  | `/api/admin/analytics` | Platform analytics |
| POST | `/api/admin/questions` | Add to question bank |

---

## 🔒 Security Features

- Passwords hashed with bcrypt (12 rounds)
- JWT with short expiry (1h access, 30d refresh)
- OTP tokens expire in 10–15 minutes
- Rate limiting on auth endpoints
- SQL injection prevention via SQLAlchemy ORM
- XSS protection via React's default escaping
- CORS restricted to frontend origin
- File upload validation (type + size)
- Input sanitization on all API endpoints

---

## 🏗️ Database Schema (Summary)

```
users ─────────────────────────── id, full_name, email, password_hash, role
otp_tokens ─────────────────────── user_id → users
resumes ────────────────────────── user_id → users, extracted_skills (JSON)
interviews ─────────────────────── user_id, resume_id, job_role, status, scores
interview_questions ────────────── interview_id, options A-D, correct_answer
interview_answers ──────────────── interview_id, question_id, selected, is_correct
interview_results ──────────────── interview_id, scores, grade, skill_scores (JSON)
feedback ───────────────────────── interview_id, strengths/weaknesses (JSON)
violations ─────────────────────── interview_id, user_id, violation_type
reports ────────────────────────── interview_id, report_path, download_count
question_bank ──────────────────── admin-managed Q bank
badges / user_badges ───────────── gamification
```

---

## 🚀 Production Deployment

### Backend (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:5000 "run:app"
```

### Frontend (Build)
```bash
npm run build
# Serve dist/ with Nginx or Vercel
```

### Nginx config snippet
```nginx
location /api {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
}
location / {
    root /var/www/ai-interview/build;
    try_files $uri /index.html;
}
```

---

## 🎯 Default Admin Credentials

After `flask seed-db`:
- **Email:** `admin@portal.com`
- **Password:** `Admin@1234`

> ⚠️ Change immediately in production!

---

## 🔮 Future Improvements

- [ ] AI voice interview (Web Speech API)
- [ ] Webcam emotion/confidence detection
- [ ] Interview difficulty levels (Easy/Medium/Hard)
- [ ] Leaderboard and gamification badges
- [ ] Email interview reminders
- [ ] Google/GitHub OAuth login
- [ ] Multi-language support
- [ ] Interview recording playback
- [ ] Company-specific question packs
- [ ] Resume builder integration

---

## 📄 License

MIT License — Free to use for educational purposes.
