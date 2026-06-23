-- Direct INSERT target tables for MyPage / Settings / Fortune / Admin.
-- External source tables such as users, characters, chat messages, reports,
-- memories, and safety events are referenced by id only here.

CREATE TABLE user_settings (
    user_id BIGINT PRIMARY KEY,
    scale_analysis_agreed BOOLEAN NOT NULL DEFAULT FALSE,
    ml_rag_agreed BOOLEAN NOT NULL DEFAULT FALSE,
    secret_chat_default BOOLEAN NOT NULL DEFAULT FALSE,
    notification_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    share_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    language VARCHAR(10) NOT NULL DEFAULT 'ko',
    theme VARCHAR(20) NOT NULL DEFAULT 'light',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE character_affinities (
    affinity_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    character_id BIGINT NOT NULL,
    affinity_level INT NOT NULL DEFAULT 1,
    affinity_score INT NOT NULL DEFAULT 0,
    conversation_count INT NOT NULL DEFAULT 0,
    consecutive_visit_count INT NOT NULL DEFAULT 0,
    next_condition VARCHAR(255),
    is_representative BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_character_affinities_user_character UNIQUE (user_id, character_id),
    CONSTRAINT ck_character_affinities_level CHECK (affinity_level >= 1),
    CONSTRAINT ck_character_affinities_score CHECK (affinity_score >= 0)
);

CREATE INDEX idx_character_affinities_user ON character_affinities (user_id);
CREATE INDEX idx_character_affinities_representative ON character_affinities (user_id, is_representative);

CREATE TABLE my_daily_summaries (
    daily_summary_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    summary_date DATE NOT NULL,
    mood_tone VARCHAR(50),
    mood_color VARCHAR(30),
    visit_count INT NOT NULL DEFAULT 0,
    consecutive_days INT NOT NULL DEFAULT 0,
    conversation_count INT NOT NULL DEFAULT 0,
    report_count INT NOT NULL DEFAULT 0,
    has_saved_record BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_my_daily_summaries_user_date UNIQUE (user_id, summary_date)
);

CREATE INDEX idx_my_daily_summaries_user_date ON my_daily_summaries (user_id, summary_date DESC);

CREATE TABLE user_activities (
    activity_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    activity_date DATE NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    source_table VARCHAR(80),
    source_id BIGINT,
    character_id BIGINT,
    chat_mode VARCHAR(30),
    save_type VARCHAR(30),
    display_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_activities_user_date ON user_activities (user_id, activity_date DESC, created_at DESC);
CREATE INDEX idx_user_activities_type ON user_activities (user_id, activity_type, activity_date DESC);
CREATE INDEX idx_user_activities_source ON user_activities (source_table, source_id);

CREATE TABLE collection_assets (
    collection_asset_id BIGSERIAL PRIMARY KEY,
    asset_code VARCHAR(80) NOT NULL UNIQUE,
    asset_name VARCHAR(100) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    mood_tone VARCHAR(50),
    description TEXT,
    image_url VARCHAR(500),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE minirooms (
    miniroom_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    representative_asset_id BIGINT REFERENCES collection_assets(collection_asset_id),
    applied_items JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_collection_items (
    user_collection_item_id BIGSERIAL PRIMARY KEY,
    miniroom_id BIGINT NOT NULL REFERENCES minirooms(miniroom_id) ON DELETE CASCADE,
    collection_asset_id BIGINT NOT NULL REFERENCES collection_assets(collection_asset_id),
    acquired_date DATE NOT NULL,
    acquire_reason VARCHAR(255),
    is_representative BOOLEAN NOT NULL DEFAULT FALSE,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_collection_items_daily_asset UNIQUE (miniroom_id, collection_asset_id, acquired_date)
);

CREATE INDEX idx_user_collection_items_miniroom_date ON user_collection_items (miniroom_id, acquired_date DESC);

CREATE TABLE fortune_contents (
    fortune_content_id BIGSERIAL PRIMARY KEY,
    fortune_date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    character_greeting TEXT,
    weather_context VARCHAR(80),
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    publish_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fortune_contents_date_category UNIQUE (fortune_date, category)
);

CREATE INDEX idx_fortune_contents_publish ON fortune_contents (fortune_date, is_published);

CREATE TABLE user_fortunes (
    user_fortune_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    fortune_content_id BIGINT NOT NULL REFERENCES fortune_contents(fortune_content_id),
    viewed_date DATE NOT NULL,
    share_card_created BOOLEAN NOT NULL DEFAULT FALSE,
    viewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_fortunes_user_date_category UNIQUE (user_id, viewed_date, fortune_content_id)
);

CREATE INDEX idx_user_fortunes_user_date ON user_fortunes (user_id, viewed_date DESC);

CREATE TABLE analysis_snapshots (
    analysis_snapshot_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    period_type VARCHAR(30) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    baseline_change_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    emotion_situation_matrix JSONB NOT NULL DEFAULT '{}'::jsonb,
    recovery_effect_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    self_understanding TEXT,
    display_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_record_count INT NOT NULL DEFAULT 0,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_analysis_snapshots_user_period UNIQUE (user_id, period_type, period_start, period_end)
);

CREATE INDEX idx_analysis_snapshots_user_generated ON analysis_snapshots (user_id, generated_at DESC);

CREATE TABLE admin_users (
    admin_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE safety_case_reviews (
    safety_case_review_id BIGSERIAL PRIMARY KEY,
    safety_event_id BIGINT NOT NULL,
    user_id BIGINT,
    risk_level VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    anonymized_summary TEXT,
    llm_bypass_applied BOOLEAN NOT NULL DEFAULT FALSE,
    payment_off_applied BOOLEAN NOT NULL DEFAULT FALSE,
    institution_guidance_done BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_by BIGINT REFERENCES admin_users(admin_id),
    detected_at TIMESTAMPTZ NOT NULL,
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX idx_safety_case_reviews_status ON safety_case_reviews (status, risk_level, detected_at DESC);
CREATE INDEX idx_safety_case_reviews_event ON safety_case_reviews (safety_event_id);

CREATE TABLE admin_contents (
    content_id BIGSERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    scheduled_at TIMESTAMPTZ,
    updated_by BIGINT REFERENCES admin_users(admin_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_admin_contents_type_status ON admin_contents (content_type, status);

CREATE TABLE admin_notices (
    notice_id BIGSERIAL PRIMARY KEY,
    notice_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    target_group VARCHAR(80) NOT NULL DEFAULT 'all',
    display_start_at TIMESTAMPTZ,
    display_end_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    created_by BIGINT REFERENCES admin_users(admin_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_admin_notices_display ON admin_notices (status, display_start_at, display_end_at);

CREATE TABLE service_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    metric_date DATE NOT NULL UNIQUE,
    dau INT NOT NULL DEFAULT 0,
    mau INT NOT NULL DEFAULT 0,
    retention_5turn_rate DECIMAL(5, 2),
    report_count INT NOT NULL DEFAULT 0,
    save_rate DECIMAL(5, 2),
    share_rate DECIMAL(5, 2),
    model_drift_score DECIMAL(8, 4),
    safety_recall DECIMAL(5, 2),
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE admin_audit_logs (
    audit_log_id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT REFERENCES admin_users(admin_id),
    action_type VARCHAR(80) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id BIGINT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_admin_audit_logs_admin_created ON admin_audit_logs (admin_id, created_at DESC);
CREATE INDEX idx_admin_audit_logs_target ON admin_audit_logs (target_type, target_id);
