
"""v29.0: Add missing indexes for frequently-queried columns.

Revision ID: v29_add_indexes
Revises: 499fad11a5b9
Create Date: 2026-05-28

Indexes added:
  - users.is_banned — admin dashboard filters
  - reminders.sent — scheduler queries unsent reminders
  - analytics_events.success — error rate dashboard
  - customers.status — CRM status filtering
  - web_monitors.is_active — monitor scheduler
  - auto_replies.is_active — auto-reply activation filter
"""
from alembic import op


revision = 'v29_add_indexes'
down_revision = '499fad11a5b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_users_is_banned', 'users', ['is_banned'])
    op.create_index('ix_reminders_sent', 'reminders', ['sent'])
    op.create_index('ix_analytics_events_success', 'analytics_events', ['success'])
    op.create_index('ix_customers_status', 'customers', ['status'])
    op.create_index('ix_web_monitors_is_active', 'web_monitors', ['is_active'])
    op.create_index('ix_auto_replies_is_active', 'auto_replies', ['is_active'])


def downgrade():
    op.drop_index('ix_auto_replies_is_active', 'auto_replies')
    op.drop_index('ix_web_monitors_is_active', 'web_monitors')
    op.drop_index('ix_customers_status', 'customers')
    op.drop_index('ix_analytics_events_success', 'analytics_events')
    op.drop_index('ix_reminders_sent', 'reminders')
    op.drop_index('ix_users_is_banned', 'users')


