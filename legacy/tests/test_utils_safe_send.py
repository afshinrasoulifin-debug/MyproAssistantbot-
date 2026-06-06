

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import Message, CallbackQuery
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply, safe_answer_callback, send_long_text

@pytest.mark.asyncio
class TestUtilsSafeSend:

    @pytest.fixture
    def mock_message(self):
        msg = AsyncMock(spec=Message)
        msg.chat.id = 12345
        msg.message_id = 1
        msg.text = "original text"
        msg.answer = AsyncMock(return_value=MagicMock(message_id=2))
        msg.edit_text = AsyncMock()
        msg.delete = AsyncMock()
        return msg

    @pytest.fixture
    def mock_callback_query(self, mock_message):
        cb_query = AsyncMock(spec=CallbackQuery)
        cb_query.message = mock_message
        cb_query.answer = AsyncMock()
        return cb_query

    async def test_safe_delete_success(self, mock_message):
        """D13: safe_delete با Message، assert delete() فراخوانده شود."""
        await safe_delete(mock_message)
        mock_message.delete.assert_called_once()

    async def test_safe_delete_none_message(self):
        """D13: safe_delete با None، assert هیچ خطایی رخ ندهد."""
        await safe_delete(None)
        # No assertion needed, just ensure no exception is raised

    async def test_safe_delete_handles_exception(self, mock_message):
        """D13: safe_delete با خطا، assert خطا log شود و raise نشود."""
        mock_message.delete.side_effect = Exception("Telegram API error")
        with patch("arki_project.utils.safe_send.logger") as mock_logger:
            await safe_delete(mock_message)
            mock_logger.debug.assert_called_once()
            assert "safe_delete failed" in mock_logger.debug.call_args[0][0]

    async def test_safe_edit_text_success(self, mock_message):
        """D14: safe_edit_text با Message، assert edit_text() فراخوانده شود."""
        new_text = "edited text"
        await safe_edit_text(mock_message, new_text)
        mock_message.edit_text.assert_called_once_with(text=new_text, parse_mode="Markdown")

    async def test_safe_edit_text_callback_query(self, mock_callback_query):
        """D14: safe_edit_text با CallbackQuery، assert edit_text() روی message فراخوانده شود."""
        new_text = "edited text from callback"
        await safe_edit_text(mock_callback_query, new_text)
        mock_callback_query.message.edit_text.assert_called_once_with(text=new_text, parse_mode="Markdown")

    async def test_safe_edit_text_markdown_fallback(self, mock_message):
        """D14: safe_edit_text با Markdown error، assert retry بدون parse_mode."""
        new_text = "*invalid markdown [link](*)"
        mock_message.edit_text.side_effect = [
            Exception("Can't parse entities"), # First call fails with markdown error
            None # Second call succeeds without parse_mode
        ]
        await safe_edit_text(mock_message, new_text, parse_mode="Markdown")
        assert mock_message.edit_text.call_count == 2
        mock_message.edit_text.call_args_list[0].assert_called_with(text=new_text, parse_mode="Markdown")
        mock_message.edit_text.call_args_list[1].assert_called_with(text=new_text)

    async def test_safe_edit_text_message_not_modified(self, mock_message):
        """D14: safe_edit_text با "message is not modified"، assert هیچ خطایی رخ ندهد."""
        mock_message.edit_text.side_effect = Exception("message is not modified")
        with patch("arki_project.utils.safe_send.logger") as mock_logger:
            await safe_edit_text(mock_message, "same text")
            mock_message.edit_text.assert_called_once()
            mock_logger.warning.assert_not_called()

    async def test_safe_reply_success(self, mock_message):
        """D15: safe_reply با Message، assert answer() فراخوانده شود و Message برگردد."""
        with patch("arki_project.utils.safe_send.get_outbound_queue") as mock_get_outbound_queue:
            mock_get_outbound_queue.return_value = MagicMock()
            response = await safe_reply(mock_message, "reply text")
            mock_message.answer.assert_called_once_with(text="reply text", parse_mode="Markdown")
            assert response is not None

    async def test_safe_reply_flood_wait_retry(self, mock_message):
        """D15: safe_reply با FloodWait، assert retry با backoff."""
        mock_message.answer.side_effect = [
            Exception("Flood control exceeded. Retry after 1"),
            MagicMock(message_id=3) # Second attempt succeeds
        ]
        with (
            patch("arki_project.utils.safe_send.asyncio.sleep") as mock_sleep,
            patch("arki_project.utils.safe_send.get_outbound_queue") as mock_get_outbound_queue
        ):
            mock_get_outbound_queue.return_value = MagicMock()
            response = await safe_reply(mock_message, "flood test", max_retries=1)
            assert mock_message.answer.call_count == 2
            mock_sleep.assert_called_once_with(2 ** (0 + 1)) # 2 seconds for first retry
            assert response is not None

    async def test_safe_reply_markdown_fallback(self, mock_message):
        """D15: safe_reply با Markdown error، assert retry بدون parse_mode."""
        mock_message.answer.side_effect = [
            Exception("Can't parse entities"), # First call fails with markdown error
            MagicMock(message_id=3) # Second call succeeds without parse_mode
        ]
        with patch("arki_project.utils.safe_send.get_outbound_queue") as mock_get_outbound_queue:
            mock_get_outbound_queue.return_value = MagicMock()
            response = await safe_reply(mock_message, "*invalid markdown [link](*)", parse_mode="Markdown")
            assert mock_message.answer.call_count == 2
            mock_message.answer.call_args_list[0].assert_called_with(text="*invalid markdown [link](*)", parse_mode="Markdown")
            mock_message.answer.call_args_list[1].assert_called_with(text="*invalid markdown [link](*)")
            assert response is not None

    async def test_safe_answer_callback_success(self, mock_callback_query):
        """D16: safe_answer_callback با CallbackQuery، assert answer() فراخوانده شود."""
        await safe_answer_callback(mock_callback_query, "alert text", show_alert=True)
        mock_callback_query.answer.assert_called_once_with(text="alert text", show_alert=True)

    async def test_send_long_text_splits_message(self, mock_message):
        """D17: send_long_text با متن طولانی، assert به چند پیام تقسیم شود."""
        long_text = "a" * 5000 # Longer than chunk_limit=4080
        with (
            patch("arki_project.utils.safe_send.split_for_telegram", return_value=["a"*4000, "a"*1000]) as mock_split,
            patch("arki_project.utils.safe_send.safe_reply", new_callable=AsyncMock) as mock_safe_reply
        ):
            mock_safe_reply.return_value = MagicMock(spec=Message)
            sent_messages = await send_long_text(mock_message, long_text)
            assert mock_split.called_once_with(long_text, limit=4080)
            assert mock_safe_reply.call_count == 2
            assert len(sent_messages) == 2
            # Ensure reply_markup is only on the last chunk
            mock_safe_reply.call_args_list[0].assert_called_with(mock_message, "a"*4000, parse_mode="Markdown", reply_markup=None)
            mock_safe_reply.call_args_list[1].assert_called_with(mock_message, "a"*1000, parse_mode="Markdown", reply_markup=None) # No reply_markup passed in this test



