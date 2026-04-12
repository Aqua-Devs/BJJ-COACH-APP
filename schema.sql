-- BJJ Coach App - PostgreSQL Schema
-- Run this in Supabase SQL Editor

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Gyms table
CREATE TABLE IF NOT EXISTS gyms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    location VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    belt VARCHAR(50) NOT NULL,
    since_date DATE NOT NULL,
    stripes INTEGER DEFAULT 0,
    competition_date DATE,
    competition_prep_active BOOLEAN DEFAULT FALSE,
    current_weight DECIMAL(5,2),
    gym_id INTEGER REFERENCES gyms(id)
);

-- Curriculum table
CREATE TABLE IF NOT EXISTS curriculum (
    id SERIAL PRIMARY KEY,
    gym_id INTEGER NOT NULL REFERENCES gyms(id) ON DELETE CASCADE,
    technique_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    belt_level VARCHAR(50),
    description TEXT,
    date_from DATE,
    date_to DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    gym_id INTEGER REFERENCES gyms(id),
    date DATE NOT NULL,
    techniques TEXT,
    note_goed TEXT,
    note_focus TEXT,
    note_algemeen TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Technique suggestions
CREATE TABLE IF NOT EXISTS technique_suggestions (
    id SERIAL PRIMARY KEY,
    technique VARCHAR(255) UNIQUE NOT NULL
);

-- Technique mastery
CREATE TABLE IF NOT EXISTS technique_mastery (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    technique VARCHAR(255) NOT NULL,
    level VARCHAR(50) DEFAULT 'introduced',
    mastery_percentage INTEGER DEFAULT 0,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, technique)
);

-- Sparring sessions
CREATE TABLE IF NOT EXISTS sparring_sessions (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    opponent_name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    outcome VARCHAR(50),
    notes TEXT,
    what_worked TEXT,
    what_didnt TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Injuries
CREATE TABLE IF NOT EXISTS injuries (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    injury_type VARCHAR(255) NOT NULL,
    affected_area VARCHAR(255) NOT NULL,
    restricted_techniques TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    notes TEXT,
    active BOOLEAN DEFAULT TRUE
);

-- Belt promotions
CREATE TABLE IF NOT EXISTS belt_promotions (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    from_belt VARCHAR(50) NOT NULL,
    to_belt VARCHAR(50) NOT NULL,
    promotion_date DATE NOT NULL,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_students_gym ON students(gym_id);
CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_curriculum_gym ON curriculum(gym_id);
CREATE INDEX IF NOT EXISTS idx_sparring_student ON sparring_sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_mastery_student ON technique_mastery(student_id);
