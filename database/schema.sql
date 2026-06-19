-- ============================================================
-- AI Resume Interview Mock Portal - MySQL Schema (FIXED)
-- Compatible with MySQL strict mode
-- ============================================================

SET SQL_MODE = '';
SET FOREIGN_KEY_CHECKS = 0;

-- Drop tables if re-running
DROP TABLE IF EXISTS user_badges;
DROP TABLE IF EXISTS badges;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS violations;
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS interview_results;
DROP TABLE IF EXISTS interview_answers;
DROP TABLE IF EXISTS interview_questions;
DROP TABLE IF EXISTS interviews;
DROP TABLE IF EXISTS question_bank;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS resumes;
DROP TABLE IF EXISTS otp_tokens;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- TABLE: users
-- ============================================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    profile_picture VARCHAR(500) DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    is_active TINYINT(1) DEFAULT 1,
    is_verified TINYINT(1) DEFAULT 0,
    role ENUM('student', 'admin') DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL DEFAULT NULL,
    INDEX idx_email (email),
    INDEX idx_role (role)
);

-- ============================================================
-- TABLE: otp_tokens
-- ============================================================
CREATE TABLE otp_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(10) NOT NULL,
    token_type ENUM('email_verify', 'password_reset') NOT NULL,
    expires_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_used TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_token (user_id, token)
);

-- ============================================================
-- TABLE: resumes
-- ============================================================
CREATE TABLE resumes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT DEFAULT 0,
    file_type ENUM('pdf', 'docx') NOT NULL,
    parsed_text LONGTEXT DEFAULT NULL,
    extracted_skills JSON DEFAULT NULL,
    extracted_experience JSON DEFAULT NULL,
    extracted_projects JSON DEFAULT NULL,
    extracted_education JSON DEFAULT NULL,
    extracted_certifications JSON DEFAULT NULL,
    parse_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);

-- ============================================================
-- TABLE: skills
-- ============================================================
CREATE TABLE skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) NOT NULL UNIQUE,
    category ENUM('technical', 'soft', 'domain', 'tool') DEFAULT 'technical',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category)
);

-- ============================================================
-- TABLE: question_bank
-- ============================================================
CREATE TABLE question_bank (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT NOT NULL,
    option_a VARCHAR(500) NOT NULL,
    option_b VARCHAR(500) NOT NULL,
    option_c VARCHAR(500) NOT NULL,
    option_d VARCHAR(500) NOT NULL,
    correct_answer ENUM('A', 'B', 'C', 'D') NOT NULL,
    explanation TEXT DEFAULT NULL,
    question_type ENUM('technical', 'hr', 'behavioral') NOT NULL,
    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    skill_tags JSON DEFAULT NULL,
    job_roles JSON DEFAULT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_by INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_type (question_type),
    INDEX idx_difficulty (difficulty)
);

-- ============================================================
-- TABLE: interviews
-- ============================================================
CREATE TABLE interviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    resume_id INT NOT NULL,
    job_role VARCHAR(200) NOT NULL,
    job_description TEXT NOT NULL,
    experience_level ENUM('fresher', 'internship', '1year', '2years', '3years', '5plus') NOT NULL,
    status ENUM('setup', 'technical_round', 'hr_round', 'completed', 'abandoned') DEFAULT 'setup',
    technical_start_time TIMESTAMP NULL DEFAULT NULL,
    technical_end_time TIMESTAMP NULL DEFAULT NULL,
    hr_start_time TIMESTAMP NULL DEFAULT NULL,
    hr_end_time TIMESTAMP NULL DEFAULT NULL,
    total_duration_seconds INT DEFAULT 0,
    technical_score DECIMAL(5,2) DEFAULT 0.00,
    hr_score DECIMAL(5,2) DEFAULT 0.00,
    overall_score DECIMAL(5,2) DEFAULT 0.00,
    violation_count INT DEFAULT 0,
    auto_submitted TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);

-- ============================================================
-- TABLE: interview_questions
-- ============================================================
CREATE TABLE interview_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL,
    question_bank_id INT DEFAULT NULL,
    question_text TEXT NOT NULL,
    option_a VARCHAR(500) NOT NULL,
    option_b VARCHAR(500) NOT NULL,
    option_c VARCHAR(500) NOT NULL,
    option_d VARCHAR(500) NOT NULL,
    correct_answer ENUM('A', 'B', 'C', 'D') NOT NULL,
    question_type ENUM('technical', 'hr') NOT NULL,
    round_number TINYINT NOT NULL DEFAULT 1,
    question_order INT NOT NULL,
    time_limit_seconds INT DEFAULT 20,
    skill_tag VARCHAR(100) DEFAULT NULL,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
    FOREIGN KEY (question_bank_id) REFERENCES question_bank(id) ON DELETE SET NULL,
    INDEX idx_interview_id (interview_id),
    INDEX idx_type (question_type)
);

-- ============================================================
-- TABLE: interview_answers
-- ============================================================
CREATE TABLE interview_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL,
    question_id INT NOT NULL,
    selected_answer ENUM('A', 'B', 'C', 'D', 'skipped') DEFAULT 'skipped',
    is_correct TINYINT(1) DEFAULT 0,
    time_taken_seconds INT DEFAULT 0,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES interview_questions(id) ON DELETE CASCADE,
    INDEX idx_interview_id (interview_id)
);

-- ============================================================
-- TABLE: interview_results
-- ============================================================
CREATE TABLE interview_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL UNIQUE,
    technical_total INT DEFAULT 0,
    technical_correct INT DEFAULT 0,
    technical_wrong INT DEFAULT 0,
    technical_skipped INT DEFAULT 0,
    technical_percentage DECIMAL(5,2) DEFAULT 0.00,
    hr_total INT DEFAULT 0,
    hr_correct INT DEFAULT 0,
    hr_wrong INT DEFAULT 0,
    hr_skipped INT DEFAULT 0,
    hr_percentage DECIMAL(5,2) DEFAULT 0.00,
    overall_percentage DECIMAL(5,2) DEFAULT 0.00,
    grade ENUM('A+', 'A', 'B+', 'B', 'C', 'D', 'F') DEFAULT 'F',
    skill_scores JSON DEFAULT NULL,
    time_analysis JSON DEFAULT NULL,
    percentile DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE: feedback
-- ============================================================
CREATE TABLE feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL UNIQUE,
    strengths JSON DEFAULT NULL,
    weaknesses JSON DEFAULT NULL,
    technical_gaps JSON DEFAULT NULL,
    communication_analysis TEXT DEFAULT NULL,
    resume_suggestions JSON DEFAULT NULL,
    learning_roadmap JSON DEFAULT NULL,
    overall_summary TEXT DEFAULT NULL,
    confidence_score DECIMAL(5,2) DEFAULT 0.00,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE: violations
-- ============================================================
CREATE TABLE violations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL,
    user_id INT NOT NULL,
    violation_type ENUM(
        'tab_switch', 'window_minimize', 'camera_off',
        'copy_attempt', 'paste_attempt', 'right_click',
        'keyboard_shortcut', 'fullscreen_exit', 'suspicious_activity'
    ) NOT NULL,
    description VARCHAR(500) DEFAULT NULL,
    screenshot_path VARCHAR(500) DEFAULT NULL,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_interview_id (interview_id)
);

-- ============================================================
-- TABLE: reports
-- ============================================================
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL UNIQUE,
    user_id INT NOT NULL,
    report_path VARCHAR(500) DEFAULT NULL,
    report_size INT DEFAULT 0,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_count INT DEFAULT 0,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE: badges
-- ============================================================
CREATE TABLE badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    badge_name VARCHAR(100) NOT NULL,
    badge_icon VARCHAR(50) NOT NULL,
    description VARCHAR(300) NOT NULL,
    condition_type ENUM('interview_count', 'score_threshold', 'streak', 'improvement') NOT NULL,
    condition_value INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: user_badges
-- ============================================================
CREATE TABLE user_badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    badge_id INT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badges(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_badge (user_id, badge_id)
);

-- ============================================================
-- SEED: Default Admin User
-- password = Admin@1234 (bcrypt hash)
-- ============================================================
INSERT INTO users (full_name, email, password_hash, role, is_active, is_verified)
VALUES (
    'Admin',
    'admin@portal.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/Lewc3vPs9LLHzOC4W',
    'admin',
    1,
    1
);

-- ============================================================
-- SEED: Default Badges
-- ============================================================
INSERT INTO badges (badge_name, badge_icon, description, condition_type, condition_value) VALUES
('First Interview', '🎯', 'Completed your first mock interview', 'interview_count', 1),
('Interview Pro',   '🏆', 'Completed 10 mock interviews',        'interview_count', 10),
('High Scorer',     '⭐', 'Scored above 80% in an interview',    'score_threshold', 80),
('Perfect Score',   '💯', 'Scored 100% in any round',            'score_threshold', 100),
('Consistent',      '📈', 'Improved score 5 times in a row',     'improvement',     5);
