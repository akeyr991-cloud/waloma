"""Add notifications, audit logs and offline sync inbox."""
from alembic import op
import sqlalchemy as sa

revision = '0003_notifications_audit_sync'
down_revision = '0002_operations'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(180), nullable=False), sa.Column('message', sa.Text(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True)), sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_table('audit_logs', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(100), nullable=False), sa.Column('entity_type', sa.String(80), nullable=False),
        sa.Column('entity_id', sa.String(36)), sa.Column('details', sa.Text()), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id']); op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_table('sync_operations', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_operation_id', sa.String(80), nullable=False), sa.Column('operation_type', sa.String(80), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False), sa.Column('status', sa.String(20), nullable=False, server_default='accepted'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'client_operation_id', name='uq_sync_user_client_operation'))
    op.create_index('ix_sync_operations_user_id', 'sync_operations', ['user_id'])

def downgrade():
    op.drop_index('ix_sync_operations_user_id', table_name='sync_operations'); op.drop_table('sync_operations')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs'); op.drop_index('ix_audit_logs_actor_id', table_name='audit_logs'); op.drop_table('audit_logs')
    op.drop_index('ix_notifications_user_id', table_name='notifications'); op.drop_table('notifications')
