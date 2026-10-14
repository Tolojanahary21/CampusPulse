"""Keep public student signups pending until email OTP verification."""
from alembic import op
import sqlalchemy as sa

revision = '0002_student_registration_otp'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'student_registrations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('campus_id', sa.String(36), sa.ForeignKey('campuses.id'), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resend_available_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('mail_id', sa.String(36), sa.ForeignKey('mail_outbox.id'), nullable=True),
        sa.CheckConstraint('attempts >= 0', name='registration_attempts_positive'),
    )
    op.create_index('ix_student_registrations_email', 'student_registrations', ['email'], unique=True)
    op.create_index('ix_student_registrations_campus_id', 'student_registrations', ['campus_id'])
    op.create_index('ix_student_registrations_expires_at', 'student_registrations', ['expires_at'])


def downgrade():
    op.drop_index('ix_student_registrations_expires_at', table_name='student_registrations')
    op.drop_index('ix_student_registrations_campus_id', table_name='student_registrations')
    op.drop_index('ix_student_registrations_email', table_name='student_registrations')
    op.drop_table('student_registrations')
