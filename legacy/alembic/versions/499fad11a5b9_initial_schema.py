
"""Initial schema — auto-generated from models.py

Revision ID: 499fad11a5b9
Revises:
Create Date: 2025-03-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '499fad11a5b9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables to match database/models.py exactly."""

    op.create_table('analytics_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(32), nullable=False),
        sa.Column('command', sa.String(64), nullable=False),
        sa.Column('model_used', sa.String(64), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False),
        sa.Column('tokens_out', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('audit_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('action', sa.String(50), index=True, nullable=False),
        sa.Column('resource', sa.String(200), nullable=False),
        sa.Column('details', sa.Text(), nullable=False),
        sa.Column('ip_address', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table('auto_replies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('trigger', sa.String(256), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('match_mode', sa.String(16), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('use_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(64), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('customers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('email', sa.String(256), nullable=False),
        sa.Column('phone', sa.String(32), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('tags', sa.String(256), nullable=False),
        sa.Column('source', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('total_orders', sa.Integer(), nullable=False),
        sa.Column('total_spent', sa.BigInteger(), nullable=False),
        sa.Column('last_order_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('finance_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(8), nullable=False),
        sa.Column('category', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('plan', sa.String(20), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table('knowledge_entities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('entity_name', sa.String(256), nullable=False),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('properties_json', sa.Text(), nullable=False),
        sa.Column('relations_json', sa.Text(), nullable=False),
        sa.Column('mention_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('kv_store',
        sa.Column('store_name', sa.String(64), primary_key=True),
        sa.Column('chat_id', sa.BigInteger(), primary_key=True),
        sa.Column('data', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('pipeline_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('request_id', sa.String(32), nullable=False),
        sa.Column('category', sa.String(32), nullable=False),
        sa.Column('complexity', sa.Integer(), nullable=False),
        sa.Column('reasoning_strategy', sa.String(32), nullable=False),
        sa.Column('modules_used', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('referral_codes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(20), unique=True, index=True, nullable=False),
        sa.Column('referrer_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('referred_id', sa.BigInteger(), nullable=True),
        sa.Column('reward_given', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table('reminders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('remind_at', sa.DateTime(timezone=True), index=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('sent', sa.Boolean(), nullable=False),
        sa.Column('is_recurring', sa.Boolean(), nullable=False),
        sa.Column('recurrence_rule', sa.String(64), nullable=True),
    )

    op.create_table('scheduled_tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('schedule', sa.String(64), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_run', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run', sa.DateTime(timezone=True), index=True, nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('semantic_memory',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('namespace', sa.String(64), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('memory_type', sa.String(32), nullable=False),
        sa.Column('importance', sa.Float(), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table('subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), unique=True, index=True, nullable=False),
        sa.Column('plan', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_trial', sa.Boolean(), nullable=False),
        sa.Column('auto_renew', sa.Boolean(), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('stripe_customer_id', sa.String(100), nullable=True),
    )

    op.create_table('telemetry_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('metric_name', sa.String(128), index=True, nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('tags_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('token_usage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('handler', sa.String(50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table('user_configs',
        sa.Column('telegram_id', sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column('model', sa.String(64), nullable=False),
        sa.Column('persona', sa.String(32), nullable=False),
        sa.Column('autotune', sa.Boolean(), nullable=False),
        sa.Column('voice', sa.String(32), nullable=False),
        sa.Column('language', sa.String(8), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
    )

    op.create_table('user_notes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', sa.String(256), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('users',
        sa.Column('telegram_id', sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column('username', sa.String(64), nullable=True),
        sa.Column('full_name', sa.String(256), nullable=False),
        sa.Column('language', sa.String(8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_banned', sa.Boolean(), nullable=False),
        sa.Column('is_premium', sa.Boolean(), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False),
        sa.Column('total_tokens_used', sa.BigInteger(), nullable=False),
        sa.Column('referral_code', sa.String(32), unique=True, nullable=True),
        sa.Column('referred_by', sa.BigInteger(), nullable=True),
    )

    op.create_table('web_monitors',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('label', sa.String(256), nullable=False),
        sa.Column('css_selector', sa.String(256), nullable=False),
        sa.Column('last_hash', sa.String(64), nullable=False),
        sa.Column('last_size', sa.Integer(), nullable=False),
        sa.Column('last_checked', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_changed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_count', sa.Integer(), nullable=False),
        sa.Column('change_count', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('check_interval_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('workflow_executions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), index=True, nullable=False),
        sa.Column('workflow_name', sa.String(128), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('steps_total', sa.Integer(), nullable=False),
        sa.Column('steps_completed', sa.Integer(), nullable=False),
        sa.Column('result_json', sa.Text(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── Indexes ──
    op.create_index('ix_audit_entries_user_id', 'audit_entries', ['user_id'])
    op.create_index('ix_audit_entries_action', 'audit_entries', ['action'])
    op.create_index('ix_auto_replies_user_id', 'auto_replies', ['user_id'])
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    op.create_index('ix_customers_owner_id', 'customers', ['owner_id'])
    op.create_index('ix_finance_records_user_id', 'finance_records', ['user_id'])
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('ix_knowledge_entities_user_id', 'knowledge_entities', ['user_id'])
    op.create_index('ix_referral_codes_code', 'referral_codes', ['code'])
    op.create_index('ix_referral_codes_referrer_id', 'referral_codes', ['referrer_id'])
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'])
    op.create_index('ix_reminders_remind_at', 'reminders', ['remind_at'])
    op.create_index('ix_scheduled_tasks_user_id', 'scheduled_tasks', ['user_id'])
    op.create_index('ix_scheduled_tasks_next_run', 'scheduled_tasks', ['next_run'])
    op.create_index('ix_semantic_memory_user_id', 'semantic_memory', ['user_id'])
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_telemetry_metrics_metric_name', 'telemetry_metrics', ['metric_name'])
    op.create_index('ix_token_usage_user_id', 'token_usage', ['user_id'])
    op.create_index('ix_user_notes_user_id', 'user_notes', ['user_id'])
    op.create_index('ix_web_monitors_user_id', 'web_monitors', ['user_id'])
    op.create_index('ix_workflow_executions_user_id', 'workflow_executions', ['user_id'])


def downgrade() -> None:
    op.drop_table('workflow_executions')
    op.drop_table('web_monitors')
    op.drop_table('users')
    op.drop_table('user_notes')
    op.drop_table('user_configs')
    op.drop_table('token_usage')
    op.drop_table('telemetry_metrics')
    op.drop_table('subscriptions')
    op.drop_table('semantic_memory')
    op.drop_table('scheduled_tasks')
    op.drop_table('reminders')
    op.drop_table('referral_codes')
    op.drop_table('pipeline_logs')
    op.drop_table('kv_store')
    op.drop_table('knowledge_entities')
    op.drop_table('invoices')
    op.drop_table('finance_records')
    op.drop_table('customers')
    op.drop_table('chat_messages')
    op.drop_table('auto_replies')
    op.drop_table('audit_entries')
    op.drop_table('analytics_events')


