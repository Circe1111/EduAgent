-- =============================================================================
-- EduAgent 2.0 数据库迁移脚本
-- 注意：由于系统启动时自动调用 Base.metadata.create_all，
-- 新表会被 SQLAlchemy 自动创建。此脚本用于新增字段和索引等 ALTER 操作。
-- =============================================================================

-- 1. 用户表扩展
ALTER TABLE users 
  ADD COLUMN IF NOT EXISTS daily_goal INT DEFAULT 30,
  ADD COLUMN IF NOT EXISTS total_xp INT DEFAULT 0;

-- 2. 学习记录表（专注计时用）
CREATE TABLE IF NOT EXISTS study_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    node_id INT,
    duration_seconds INT NOT NULL,
    study_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, study_date)
);

-- 3. 测验历史表（错题本用）
CREATE TABLE IF NOT EXISTS quiz_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    node_id INT NOT NULL,
    question TEXT,
    user_answer CHAR(1),
    correct_answer CHAR(1),
    is_correct BOOLEAN,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. 用户收藏表
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    question TEXT,
    answer TEXT,
    node_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. 用户徽章表
CREATE TABLE IF NOT EXISTS user_badges (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    badge_code VARCHAR(50) NOT NULL,
    badge_name VARCHAR(50),
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_badge (user_id, badge_code)
);
