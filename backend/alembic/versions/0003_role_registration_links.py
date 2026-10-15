"""Add role-scoped signup links and persist the granted role in OTP challenges."""
from alembic import op
import sqlalchemy as sa

revision = '0003_role_registration_links'
down_revision = '0002_student_registration_otp'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'registration_links',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('campus_id', sa.String(36), sa.ForeignKey('campuses.id'), nullable=False),
        sa.Column('role', sa.String(40), nullable=False),
        sa.Column('created_by_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_registration_links_token_hash', 'registration_links', ['token_hash'], unique=True)
    op.create_index('ix_registration_links_campus_id', 'registration_links', ['campus_id'])
    op.create_index('ix_registration_links_expires_at', 'registration_links', ['expires_at'])
    op.add_column('student_registrations', sa.Column('role', sa.String(40), nullable=False, server_default='STUDENT'))
    op.add_column('student_registrations', sa.Column('registration_link_id', sa.String(36), sa.ForeignKey('registration_links.id')))


def downgrade():
    op.drop_column('student_registrations', 'registration_link_id')
    op.drop_column('student_registrations', 'role')
    op.drop_index('ix_registration_links_expires_at', table_name='registration_links')
    op.drop_index('ix_registration_links_campus_id', table_name='registration_links')
    op.drop_index('ix_registration_links_token_hash', table_name='registration_links')
    op.drop_table('registration_links')
