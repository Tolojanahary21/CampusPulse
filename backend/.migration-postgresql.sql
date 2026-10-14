BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

CREATE TABLE auth_rate_limits (
    key VARCHAR(64) NOT NULL, 
    count INTEGER NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (key)
);

CREATE INDEX ix_auth_rate_limits_expires_at ON auth_rate_limits (expires_at);

CREATE TABLE campuses (
    name VARCHAR(200) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    slug VARCHAR(200) NOT NULL, 
    description TEXT, 
    email VARCHAR(255), 
    phone VARCHAR(30), 
    address TEXT, 
    city VARCHAR(100), 
    country VARCHAR(100) NOT NULL, 
    logo_url TEXT, 
    website_url TEXT, 
    status VARCHAR(20) NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code), 
    UNIQUE (slug)
);

CREATE TABLE mail_outbox (
    id VARCHAR(36) NOT NULL, 
    recipient VARCHAR(255) NOT NULL, 
    subject VARCHAR(255) NOT NULL, 
    text_body TEXT NOT NULL, 
    html_body TEXT, 
    status VARCHAR(20) NOT NULL, 
    attempts INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    sent_at TIMESTAMP WITH TIME ZONE, 
    last_error VARCHAR(100), 
    PRIMARY KEY (id)
);

CREATE INDEX ix_mail_outbox_expires_at ON mail_outbox (expires_at);

CREATE INDEX ix_mail_outbox_next_attempt_at ON mail_outbox (next_attempt_at);

CREATE INDEX ix_mail_outbox_status ON mail_outbox (status);

CREATE TABLE users (
    email VARCHAR(255) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    first_name VARCHAR(100) NOT NULL, 
    last_name VARCHAR(100) NOT NULL, 
    phone VARCHAR(30), 
    avatar_url TEXT, 
    status VARCHAR(20) NOT NULL, 
    email_verified_at TIMESTAMP WITH TIME ZONE, 
    last_login_at TIMESTAMP WITH TIME ZONE, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE academic_years (
    campus_id VARCHAR(36) NOT NULL, 
    name VARCHAR(50) NOT NULL, 
    starts_on DATE NOT NULL, 
    ends_on DATE NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    is_current BOOLEAN NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT year_dates CHECK (starts_on < ends_on), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    UNIQUE (campus_id, name), 
    CONSTRAINT uq_academic_year_campus UNIQUE (id, campus_id)
);

CREATE INDEX ix_academic_years_campus_id ON academic_years (campus_id);

CREATE UNIQUE INDEX uq_current_academic_year ON academic_years (campus_id) WHERE is_current = true;

CREATE TABLE announcements (
    campus_id VARCHAR(36), 
    author_user_id VARCHAR(36) NOT NULL, 
    title VARCHAR(250) NOT NULL, 
    summary VARCHAR(500), 
    content TEXT NOT NULL, 
    announcement_type VARCHAR(30) NOT NULL, 
    scope VARCHAR(20) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    is_pinned BOOLEAN NOT NULL, 
    allow_comments BOOLEAN NOT NULL, 
    published_at TIMESTAMP WITH TIME ZONE, 
    notifications_dispatched_at TIMESTAMP WITH TIME ZONE, 
    starts_at TIMESTAMP WITH TIME ZONE, 
    ends_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(author_user_id) REFERENCES users (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE INDEX ix_announcements_campus_id ON announcements (campus_id);

CREATE INDEX ix_announcements_notifications_dispatched_at ON announcements (notifications_dispatched_at);

CREATE INDEX ix_announcements_status ON announcements (status);

CREATE TABLE audit_logs (
    actor_user_id VARCHAR(36), 
    campus_id VARCHAR(36), 
    action VARCHAR(100) NOT NULL, 
    entity_type VARCHAR(100) NOT NULL, 
    entity_id VARCHAR(36), 
    details JSON NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor_user_id) REFERENCES users (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE INDEX ix_audit_logs_campus_id ON audit_logs (campus_id);

CREATE TABLE campus_memberships (
    user_id VARCHAR(36) NOT NULL, 
    campus_id VARCHAR(36) NOT NULL, 
    membership_type VARCHAR(30) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    ended_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (user_id, campus_id)
);

CREATE INDEX ix_campus_memberships_campus_id ON campus_memberships (campus_id);

CREATE INDEX ix_campus_memberships_user_id ON campus_memberships (user_id);

CREATE TABLE campus_settings (
    campus_id VARCHAR(36) NOT NULL, 
    allow_announcement_comments BOOLEAN NOT NULL, 
    allow_student_posts BOOLEAN NOT NULL, 
    allow_student_comments BOOLEAN NOT NULL, 
    allow_student_reactions BOOLEAN NOT NULL, 
    max_upload_size_mb INTEGER NOT NULL, 
    updated_by_user_id VARCHAR(36), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(updated_by_user_id) REFERENCES users (id), 
    UNIQUE (campus_id)
);

CREATE TABLE community_posts (
    campus_id VARCHAR(36) NOT NULL, 
    author_user_id VARCHAR(36) NOT NULL, 
    title VARCHAR(250), 
    content TEXT NOT NULL, 
    post_type VARCHAR(30) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(author_user_id) REFERENCES users (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE INDEX ix_community_posts_campus_id ON community_posts (campus_id);

CREATE TABLE file_assets (
    campus_id VARCHAR(36), 
    uploaded_by_user_id VARCHAR(36) NOT NULL, 
    storage_key VARCHAR(255) NOT NULL, 
    original_filename VARCHAR(255) NOT NULL, 
    mime_type VARCHAR(150) NOT NULL, 
    extension VARCHAR(20) NOT NULL, 
    size_bytes INTEGER NOT NULL, 
    sha256_hash VARCHAR(64) NOT NULL, 
    storage_provider VARCHAR(30) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(uploaded_by_user_id) REFERENCES users (id), 
    UNIQUE (storage_key)
);

CREATE INDEX ix_file_assets_campus_id ON file_assets (campus_id);

CREATE TABLE notification_preferences (
    user_id VARCHAR(36) NOT NULL, 
    email_announcements BOOLEAN NOT NULL, 
    email_community BOOLEAN NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (user_id)
);

CREATE TABLE notifications (
    user_id VARCHAR(36) NOT NULL, 
    campus_id VARCHAR(36), 
    event_key VARCHAR(150) NOT NULL, 
    notification_type VARCHAR(30) NOT NULL, 
    title VARCHAR(250) NOT NULL, 
    message TEXT NOT NULL, 
    link VARCHAR(500) NOT NULL, 
    read_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (user_id, event_key)
);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE password_reset_tokens (
    user_id VARCHAR(36) NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash);

CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);

CREATE TABLE platform_settings (
    key VARCHAR(100) NOT NULL, 
    value JSON NOT NULL, 
    updated_by_user_id VARCHAR(36), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(updated_by_user_id) REFERENCES users (id), 
    UNIQUE (key)
);

CREATE TABLE programs (
    campus_id VARCHAR(36) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    UNIQUE (campus_id, code)
);

CREATE INDEX ix_programs_campus_id ON programs (campus_id);

CREATE TABLE role_assignments (
    user_id VARCHAR(36) NOT NULL, 
    role VARCHAR(40) NOT NULL, 
    campus_id VARCHAR(36), 
    granted_by_user_id VARCHAR(36), 
    expires_at TIMESTAMP WITH TIME ZONE, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT role_scope CHECK ((role = 'PLATFORM_ADMIN' AND campus_id IS NULL) OR (role IN ('CAMPUS_ADMIN','CONTENT_PUBLISHER','MODERATOR','STUDENT') AND campus_id IS NOT NULL)), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(granted_by_user_id) REFERENCES users (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_role_assignments_campus_id ON role_assignments (campus_id);

CREATE INDEX ix_role_assignments_user_id ON role_assignments (user_id);

CREATE UNIQUE INDEX uq_active_campus_role ON role_assignments (user_id, campus_id, role) WHERE revoked_at IS NULL AND campus_id IS NOT NULL;

CREATE UNIQUE INDEX uq_active_global_role ON role_assignments (user_id, role) WHERE revoked_at IS NULL AND campus_id IS NULL;

CREATE TABLE user_sessions (
    user_id VARCHAR(36) NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    csrf_token VARCHAR(128) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    last_used_at TIMESTAMP WITH TIME ZONE, 
    ip_address VARCHAR(64), 
    user_agent VARCHAR(512), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_user_sessions_token_hash ON user_sessions (token_hash);

CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);

CREATE TABLE announcement_comments (
    announcement_id VARCHAR(36) NOT NULL, 
    author_user_id VARCHAR(36) NOT NULL, 
    content TEXT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(announcement_id) REFERENCES announcements (id), 
    FOREIGN KEY(author_user_id) REFERENCES users (id)
);

CREATE INDEX ix_announcement_comments_announcement_id ON announcement_comments (announcement_id);

CREATE TABLE announcement_program_targets (
    announcement_id VARCHAR(36) NOT NULL, 
    program_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (announcement_id, program_id), 
    FOREIGN KEY(announcement_id) REFERENCES announcements (id), 
    FOREIGN KEY(program_id) REFERENCES programs (id)
);

CREATE TABLE announcement_year_targets (
    announcement_id VARCHAR(36) NOT NULL, 
    academic_year_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (announcement_id, academic_year_id), 
    FOREIGN KEY(academic_year_id) REFERENCES academic_years (id), 
    FOREIGN KEY(announcement_id) REFERENCES announcements (id)
);

CREATE TABLE community_comments (
    post_id VARCHAR(36) NOT NULL, 
    author_user_id VARCHAR(36) NOT NULL, 
    parent_comment_id VARCHAR(36), 
    content TEXT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(author_user_id) REFERENCES users (id), 
    FOREIGN KEY(parent_comment_id) REFERENCES community_comments (id), 
    FOREIGN KEY(post_id) REFERENCES community_posts (id)
);

CREATE INDEX ix_community_comments_post_id ON community_comments (post_id);

CREATE TABLE events (
    campus_id VARCHAR(36), 
    announcement_id VARCHAR(36), 
    created_by_user_id VARCHAR(36) NOT NULL, 
    title VARCHAR(250) NOT NULL, 
    description TEXT NOT NULL, 
    location VARCHAR(250), 
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    registration_url TEXT, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT event_dates CHECK (starts_at < ends_at), 
    FOREIGN KEY(announcement_id) REFERENCES announcements (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(created_by_user_id) REFERENCES users (id), 
    UNIQUE (announcement_id)
);

CREATE INDEX ix_events_campus_id ON events (campus_id);

CREATE TABLE program_levels (
    program_id VARCHAR(36) NOT NULL, 
    code VARCHAR(30) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    level_order INTEGER NOT NULL, 
    description TEXT, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT level_positive_order CHECK (level_order > 0), 
    FOREIGN KEY(program_id) REFERENCES programs (id), 
    UNIQUE (program_id, code)
);

CREATE INDEX ix_program_levels_program_id ON program_levels (program_id);

CREATE TABLE announcement_level_targets (
    announcement_id VARCHAR(36) NOT NULL, 
    program_level_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (announcement_id, program_level_id), 
    FOREIGN KEY(announcement_id) REFERENCES announcements (id), 
    FOREIGN KEY(program_level_id) REFERENCES program_levels (id)
);

CREATE TABLE enrollments (
    user_id VARCHAR(36) NOT NULL, 
    campus_id VARCHAR(36) NOT NULL, 
    program_level_id VARCHAR(36) NOT NULL, 
    academic_year_id VARCHAR(36) NOT NULL, 
    enrollment_number VARCHAR(80) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    enrolled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    notes TEXT, 
    created_by_user_id VARCHAR(36), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_enrollment_year_campus FOREIGN KEY(academic_year_id, campus_id) REFERENCES academic_years (id, campus_id), 
    FOREIGN KEY(academic_year_id) REFERENCES academic_years (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(created_by_user_id) REFERENCES users (id), 
    FOREIGN KEY(program_level_id) REFERENCES program_levels (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (campus_id, enrollment_number), 
    UNIQUE (user_id, program_level_id, academic_year_id)
);

CREATE INDEX ix_enrollments_academic_year_id ON enrollments (academic_year_id);

CREATE INDEX ix_enrollments_campus_id ON enrollments (campus_id);

CREATE INDEX ix_enrollments_program_level_id ON enrollments (program_level_id);

CREATE INDEX ix_enrollments_user_id ON enrollments (user_id);

CREATE TABLE reactions (
    user_id VARCHAR(36) NOT NULL, 
    post_id VARCHAR(36), 
    comment_id VARCHAR(36), 
    reaction_type VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT reaction_single_target CHECK ((post_id IS NULL) <> (comment_id IS NULL)), 
    FOREIGN KEY(comment_id) REFERENCES community_comments (id), 
    FOREIGN KEY(post_id) REFERENCES community_posts (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (user_id, comment_id), 
    UNIQUE (user_id, post_id)
);

CREATE INDEX ix_reactions_comment_id ON reactions (comment_id);

CREATE INDEX ix_reactions_post_id ON reactions (post_id);

CREATE TABLE reports (
    campus_id VARCHAR(36) NOT NULL, 
    reporter_user_id VARCHAR(36) NOT NULL, 
    post_id VARCHAR(36), 
    comment_id VARCHAR(36), 
    reason VARCHAR(50) NOT NULL, 
    description TEXT, 
    status VARCHAR(20) NOT NULL, 
    resolved_by_user_id VARCHAR(36), 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT report_single_target CHECK ((post_id IS NULL) <> (comment_id IS NULL)), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(comment_id) REFERENCES community_comments (id), 
    FOREIGN KEY(post_id) REFERENCES community_posts (id), 
    FOREIGN KEY(reporter_user_id) REFERENCES users (id), 
    FOREIGN KEY(resolved_by_user_id) REFERENCES users (id)
);

CREATE INDEX ix_reports_campus_id ON reports (campus_id);

CREATE TABLE subjects (
    program_level_id VARCHAR(36) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    credits FLOAT, 
    semester INTEGER, 
    status VARCHAR(20) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT credits_positive CHECK (credits IS NULL OR credits >= 0), 
    FOREIGN KEY(program_level_id) REFERENCES program_levels (id), 
    UNIQUE (program_level_id, code)
);

CREATE INDEX ix_subjects_program_level_id ON subjects (program_level_id);

CREATE TABLE documents (
    campus_id VARCHAR(36), 
    file_asset_id VARCHAR(36) NOT NULL, 
    uploaded_by_user_id VARCHAR(36) NOT NULL, 
    subject_id VARCHAR(36), 
    title VARCHAR(250) NOT NULL, 
    description TEXT, 
    category VARCHAR(30) NOT NULL, 
    scope VARCHAR(20) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    published_at TIMESTAMP WITH TIME ZONE, 
    download_count INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(file_asset_id) REFERENCES file_assets (id), 
    FOREIGN KEY(subject_id) REFERENCES subjects (id), 
    FOREIGN KEY(uploaded_by_user_id) REFERENCES users (id)
);

CREATE INDEX ix_documents_campus_id ON documents (campus_id);

CREATE INDEX ix_documents_file_asset_id ON documents (file_asset_id);

CREATE INDEX ix_documents_status ON documents (status);

CREATE TABLE moderation_actions (
    campus_id VARCHAR(36) NOT NULL, 
    moderator_user_id VARCHAR(36) NOT NULL, 
    report_id VARCHAR(36), 
    post_id VARCHAR(36), 
    comment_id VARCHAR(36), 
    action VARCHAR(30) NOT NULL, 
    reason TEXT NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(campus_id) REFERENCES campuses (id), 
    FOREIGN KEY(comment_id) REFERENCES community_comments (id), 
    FOREIGN KEY(moderator_user_id) REFERENCES users (id), 
    FOREIGN KEY(post_id) REFERENCES community_posts (id), 
    FOREIGN KEY(report_id) REFERENCES reports (id)
);

CREATE INDEX ix_moderation_actions_campus_id ON moderation_actions (campus_id);

CREATE TABLE document_level_targets (
    document_id VARCHAR(36) NOT NULL, 
    program_level_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (document_id, program_level_id), 
    FOREIGN KEY(document_id) REFERENCES documents (id), 
    FOREIGN KEY(program_level_id) REFERENCES program_levels (id)
);

CREATE TABLE document_program_targets (
    document_id VARCHAR(36) NOT NULL, 
    program_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (document_id, program_id), 
    FOREIGN KEY(document_id) REFERENCES documents (id), 
    FOREIGN KEY(program_id) REFERENCES programs (id)
);

CREATE TABLE document_year_targets (
    document_id VARCHAR(36) NOT NULL, 
    academic_year_id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (document_id, academic_year_id), 
    FOREIGN KEY(academic_year_id) REFERENCES academic_years (id), 
    FOREIGN KEY(document_id) REFERENCES documents (id)
);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial') RETURNING alembic_version.version_num;

COMMIT;

