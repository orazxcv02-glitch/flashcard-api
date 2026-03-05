-- ============================================
-- Flashcard E-Learning Platform - Database Schema
-- Supabase PostgreSQL
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. Users Table (extends Supabase Auth)
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins can view all users" ON users
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND is_admin = TRUE)
    );

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 2. Courses Table
-- ============================================
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    slug VARCHAR(50) UNIQUE NOT NULL,
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    flashcard_data_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Anyone can view active courses" ON courses
    FOR SELECT USING (is_active = TRUE);

CREATE POLICY "Admins can manage courses" ON courses
    FOR ALL USING (
        EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND is_admin = TRUE)
    );

CREATE TRIGGER update_courses_updated_at
    BEFORE UPDATE ON courses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. User Courses Table (Purchases)
-- ============================================
CREATE TABLE user_courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    hwid VARCHAR(10),
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, course_id)
);

-- Enable RLS
ALTER TABLE user_courses ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own courses" ON user_courses
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "System can insert user_courses" ON user_courses
    FOR INSERT WITH CHECK (TRUE);

CREATE POLICY "Users can update own courses" ON user_courses
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all user_courses" ON user_courses
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND is_admin = TRUE)
    );

-- ============================================
-- 4. HWID Bindings Table
-- ============================================
CREATE TABLE hwid_bindings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    hwid VARCHAR(10) NOT NULL,
    bound_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, course_id)
);

-- Enable RLS
ALTER TABLE hwid_bindings ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own bindings" ON hwid_bindings
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own bindings" ON hwid_bindings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own bindings" ON hwid_bindings
    FOR UPDATE USING (auth.uid() = user_id);

-- ============================================
-- 5. Study Progress Table
-- ============================================
CREATE TABLE study_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    card_id VARCHAR(255) NOT NULL,
    question TEXT,
    answer TEXT,
    study_count INTEGER DEFAULT 0 CHECK (study_count >= 0),
    correct_count INTEGER DEFAULT 0 CHECK (correct_count >= 0),
    last_studied_at TIMESTAMP WITH TIME ZONE,
    next_review_at TIMESTAMP WITH TIME ZONE,
    srs_level INTEGER DEFAULT 0 CHECK (srs_level >= 0),
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, course_id, card_id)
);

-- Enable RLS
ALTER TABLE study_progress ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own progress" ON study_progress
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own progress" ON study_progress
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own progress" ON study_progress
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own progress" ON study_progress
    FOR DELETE USING (auth.uid() = user_id);

-- Index for faster queries
CREATE INDEX idx_study_progress_user_course ON study_progress(user_id, course_id);
CREATE INDEX idx_study_progress_next_review ON study_progress(user_id, next_review_at);

-- ============================================
-- 6. Orders Table
-- ============================================
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'THB',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'cancelled', 'refunded')),
    payment_method VARCHAR(20) CHECK (payment_method IN ('paypal', 'bank_transfer')),
    payment_proof_url TEXT,
    paypal_order_id VARCHAR(50),
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own orders" ON orders
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own orders" ON orders
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admins can view all orders" ON orders
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND is_admin = TRUE)
    );

CREATE POLICY "Admins can update orders" ON orders
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND is_admin = TRUE)
    );

-- Index for faster queries
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- ============================================
-- 7. Sync Logs Table
-- ============================================
CREATE TABLE sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hwid VARCHAR(10),
    sync_type VARCHAR(20) NOT NULL CHECK (sync_type IN ('push', 'pull', 'merge', 'full')),
    records_count INTEGER DEFAULT 0,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    device_info TEXT
);

-- Enable RLS
ALTER TABLE sync_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own sync logs" ON sync_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sync logs" ON sync_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_sync_logs_user_id ON sync_logs(user_id);

-- ============================================
-- Trigger to auto-create user record on auth signup
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, username, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger on auth.users
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- Sample Data (for testing)
-- ============================================

-- Insert sample courses
INSERT INTO courses (name, description, price, slug, image_url, flashcard_data_url) VALUES
('วิชากฎหมาย (สอบ ก.พ. 2568)', 'คอร์สเตรียมสอบกฎหมายสำหรับข้าราชการ ครอบคลุมเนื้อหาทั้งหมดที่ต้องใช้ในสอบ', 999, 'law-exam-2568', 'https://example.com/law.jpg', 'https://cdn.jsdelivr.net/gh/orazxcv02-glitch/flashcard-data@courses/law-exam-2568.json'),
('ภาษาอังกฤษ Grammar พื้นฐาน', 'เรียนรู้หลักไวยากรณ์ภาษาอังกฤษแบบเข้าใจง่าย ด้วย Flashcard ที่ออกแบบมาอย่างดี', 599, 'english-grammar', 'https://example.com/english.jpg', 'https://cdn.jsdelivr.net/gh/orazxcv02-glitch/flashcard-data@courses/english-grammar.json'),
('คณิตศาสตร์ ป.6 เตรียมสอบเข้า ม.1', 'เตรียมความพร้อมสอบเข้ามัธยมศึกษาตอนต้น ด้วยโจทย์และเทคนิคการทำข้อสอบ', 799, 'math-p6-m1', 'https://example.com/math.jpg', 'https://cdn.jsdelivr.net/gh/orazxcv02-glitch/flashcard-data@courses/math-p6-m1.json');

-- ============================================
-- Functions
-- ============================================

-- Function to check course access
CREATE OR REPLACE FUNCTION check_course_access(p_user_id UUID, p_course_id UUID, p_hwid VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM user_courses
    WHERE user_id = p_user_id
      AND course_id = p_course_id
      AND is_active = TRUE
      AND (hwid IS NULL OR hwid = p_hwid);

    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to grant course access after payment
CREATE OR REPLACE FUNCTION grant_course_access(p_order_id UUID)
RETURNS VOID AS $$
DECLARE
    v_order RECORD;
BEGIN
    SELECT * INTO v_order FROM orders WHERE id = p_order_id;

    IF v_order.status = 'paid' THEN
        INSERT INTO user_courses (user_id, course_id, purchased_at)
        VALUES (v_order.user_id, v_order.course_id, NOW())
        ON CONFLICT (user_id, course_id) DO NOTHING;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
