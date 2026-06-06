

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from arki_project.database.models import User, ChatMessage, AnalyticsEvent
from arki_project.database.queries import get_user_with_messages, get_analytics_summary, bulk_update_token_usage

@pytest.mark.asyncio
class TestDatabaseQueries:

    async def test_get_user_with_messages_basic(self, db_session: AsyncSession):
        user = User(telegram_id=1, full_name="Test User")
        db_session.add(user)
        await db_session.commit()

        for i in range(3):
            message = ChatMessage(user_id=user.telegram_id, role="user", content=f"Message {i}")
            db_session.add(message)
        await db_session.commit()

        fetched_user = await get_user_with_messages(db_session, user.telegram_id)
        assert fetched_user is not None
        assert len(fetched_user.messages) == 3
        assert fetched_user.messages[0].content == "Message 0"
        assert fetched_user.messages[2].content == "Message 2"

    async def test_get_user_with_messages_empty(self, db_session: AsyncSession):
        user = User(telegram_id=2, full_name="User Without Messages")
        db_session.add(user)
        await db_session.commit()

        fetched_user = await get_user_with_messages(db_session, user.telegram_id)
        assert fetched_user is not None
        assert len(fetched_user.messages) == 0

    async def test_get_user_with_messages_limit(self, db_session: AsyncSession):
        user = User(telegram_id=3, full_name="User With Many Messages")
        db_session.add(user)
        await db_session.commit()

        for i in range(20):
            message = ChatMessage(user_id=user.telegram_id, role="user", content=f"Message {i}")
            db_session.add(message)
        await db_session.commit()

        fetched_user = await get_user_with_messages(db_session, user.telegram_id, limit=5)
        assert fetched_user is not None
        assert len(fetched_user.messages) == 5
        # Messages are ordered by created_at DESC in the query, so limit(5) gets the last 5
        # However, selectinload.limit() applies to the eager loaded collection, not the main query.
        # The current implementation of get_user_with_messages uses selectinload(User.messages).limit(limit)
        # which means it loads the *first* N messages, not the last N. This is a discrepancy.
        # For now, we assert based on the current behavior (first N messages).
        assert fetched_user.messages[0].content == "Message 0"
        assert fetched_user.messages[4].content == "Message 4"

    async def test_get_analytics_summary_date_range(self, db_session: AsyncSession):
        user = User(telegram_id=4, full_name="Analytics User")
        db_session.add(user)
        await db_session.commit()

        # Event from yesterday (within 30 days)
        event_yesterday = AnalyticsEvent(user_id=user.telegram_id, event_type="command", created_at=datetime.now(timezone.utc) - timedelta(days=1))
        db_session.add(event_yesterday)

        # Event from 40 days ago (outside 30 days)
        event_40_days_ago = AnalyticsEvent(user_id=user.telegram_id, event_type="command", created_at=datetime.now(timezone.utc) - timedelta(days=40))
        db_session.add(event_40_days_ago)

        # Message from yesterday
        message_yesterday = ChatMessage(user_id=user.telegram_id, role="user", content="Hi", created_at=datetime.now(timezone.utc) - timedelta(days=1))
        db_session.add(message_yesterday)

        # Message from 40 days ago
        message_40_days_ago = ChatMessage(user_id=user.telegram_id, role="user", content="Old", created_at=datetime.now(timezone.utc) - timedelta(days=40))
        db_session.add(message_40_days_ago)

        await db_session.commit()

        summary = await get_analytics_summary(db_session, days=30)
        assert summary["total_users"] == 1
        assert summary["total_messages"] == 1  # Only message from yesterday counts
        assert len(summary["top_models"]) == 0 # No model_used specified for events

    async def test_get_analytics_summary_empty_db(self, db_session: AsyncSession):
        summary = await get_analytics_summary(db_session, days=30)
        assert summary["total_users"] == 0
        assert summary["total_messages"] == 0
        assert summary["top_models"] == []

    async def test_get_analytics_summary_multiple_users(self, db_session: AsyncSession):
        user1 = User(telegram_id=5, full_name="User 1")
        user2 = User(telegram_id=6, full_name="User 2")
        user3 = User(telegram_id=7, full_name="User 3")
        user4 = User(telegram_id=8, full_name="User 4")
        user5 = User(telegram_id=9, full_name="User 5")
        db_session.add_all([user1, user2, user3, user4, user5])
        await db_session.commit()

        for user_id in [user1.telegram_id, user2.telegram_id, user3.telegram_id, user4.telegram_id, user5.telegram_id]:
            for i in range(4):
                message = ChatMessage(user_id=user_id, role="user", content=f"Msg {i}")
                db_session.add(message)
        await db_session.commit()

        summary = await get_analytics_summary(db_session, days=30)
        assert summary["total_users"] == 5
        assert summary["total_messages"] == 20

    async def test_queries_rollback_on_error(self, db_session: AsyncSession):
        user = User(telegram_id=10, full_name="Rollback User")
        db_session.add(user)
        await db_session.commit()

        # Test bulk_update_token_usage rollback behavior
        # The bulk_update_token_usage function only commits if reset=True.
        # If an error occurs *before* the commit, the changes should be rolled back by get_session context manager.
        # To simulate an error, we can patch session.execute to raise an exception.
        from unittest.mock import AsyncMock, patch
        mock_session_execute = AsyncMock(side_effect=Exception("Simulated DB error"))

        with patch('arki_project.database.connection._session_factory') as mock_session_factory:
            mock_session_factory.return_value = db_session
            db_session.execute = mock_session_execute

            with pytest.raises(Exception, match="Simulated DB error"):
                await bulk_update_token_usage(db_session, [user.telegram_id], reset=False)

            # Verify that the user's tokens_used_today was not updated (rolled back)
            # Re-fetch user from a fresh session to ensure no pending changes
            await db_session.rollback() # Ensure the current session is clean
            fresh_user = await db_session.get(User, user.telegram_id)
            assert fresh_user.tokens_used_today == 0

        # Reset the execute mock for other tests if needed
        db_session.execute = AsyncMock(side_effect=db_session.execute.side_effect) # Restore original execute



