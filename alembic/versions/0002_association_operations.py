"""Add member operations, meetings, contributions and payments."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002_operations'
down_revision = '0001_initial_users'
branch_labels = None
depends_on = None

payment_method = postgresql.ENUM('CASH', 'BANK', 'MOBILE', name='payment_method', create_type=False)

def upgrade():
    bind = op.get_bind()
    payment_method.create(bind, checkfirst=True)
    op.create_table('meetings',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('title', sa.String(180), nullable=False),
        sa.Column('description', sa.Text()), sa.Column('location', sa.String(180)), sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('attendance', sa.Column('id', sa.String(36), primary_key=True), sa.Column('meeting_id', sa.String(36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False), sa.Column('member_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('marked_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('status', sa.String(16), nullable=False), sa.Column('marked_at', sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint('meeting_id','member_id',name='uq_meeting_member_attendance'))
    op.create_index('ix_attendance_meeting_id','attendance',['meeting_id']); op.create_index('ix_attendance_member_id','attendance',['member_id'])
    op.create_table('contributions', sa.Column('id', sa.String(36), primary_key=True), sa.Column('member_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('period', sa.String(7), nullable=False), sa.Column('amount_due', sa.Numeric(12,2), nullable=False), sa.Column('description', sa.String(240)), sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint('member_id','period',name='uq_member_contribution_period'))
    op.create_index('ix_contributions_member_id','contributions',['member_id']); op.create_index('ix_contributions_period','contributions',['period'])
    op.create_table('payments', sa.Column('id', sa.String(36), primary_key=True), sa.Column('contribution_id', sa.String(36), sa.ForeignKey('contributions.id'), nullable=False), sa.Column('amount', sa.Numeric(12,2), nullable=False), sa.Column('method', payment_method, nullable=False), sa.Column('receipt_number', sa.String(40), nullable=False), sa.Column('reference', sa.String(120)), sa.Column('received_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('paid_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_payments_contribution_id','payments',['contribution_id']); op.create_index('ix_payments_receipt_number','payments',['receipt_number'], unique=True)

def downgrade():
    op.drop_index('ix_payments_receipt_number', table_name='payments'); op.drop_index('ix_payments_contribution_id', table_name='payments'); op.drop_table('payments')
    op.drop_index('ix_contributions_period', table_name='contributions'); op.drop_index('ix_contributions_member_id', table_name='contributions'); op.drop_table('contributions')
    op.drop_index('ix_attendance_member_id', table_name='attendance'); op.drop_index('ix_attendance_meeting_id', table_name='attendance'); op.drop_table('attendance'); op.drop_table('meetings')
    payment_method.drop(op.get_bind(), checkfirst=True)
