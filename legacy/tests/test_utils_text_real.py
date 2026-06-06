


from arki_project.utils.text import split_for_telegram, escape_markdown, truncate_text

class TestUtilsText:

    def test_split_for_telegram_basic(self):
        """D18: متن طولانی‌تر از limit، assert به چند chunk تقسیم شود."""
        long_text = "This is a very long text that needs to be split into multiple chunks for Telegram. " * 50
        chunks = split_for_telegram(long_text, limit=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100

        # Test with text shorter than limit
        short_text = "This is a short text."
        chunks = split_for_telegram(short_text, limit=100)
        assert len(chunks) == 1
        assert chunks[0] == short_text

        # Test with text that splits exactly at limit
        exact_text = "a" * 100
        chunks = split_for_telegram(exact_text, limit=100)
        assert len(chunks) == 1
        assert chunks[0] == exact_text

    def test_split_for_telegram_paragraph_preservation(self):
        """D18: متن با پاراگراف، assert پاراگراف‌ها حفظ شوند."""
        text_with_paragraphs = (
            "Paragraph one.\n\n" +
            "Paragraph two is a bit longer and should ideally stay together.\n\n" +
            "Paragraph three, also important." * 5
        )
        chunks = split_for_telegram(text_with_paragraphs, limit=100)
        # The exact number of chunks depends on the content and limit, but paragraphs should be preserved as much as possible.
        # We expect at least 3 chunks here, as the third paragraph alone is long.
        assert len(chunks) >= 3
        assert "Paragraph one." in chunks[0]
        assert "Paragraph two is a bit longer and should ideally stay together." in chunks[1]
        assert any("Paragraph three, also important." in chunk for chunk in chunks)

    def test_escape_markdown(self):
        """D19: متن با کاراکترهای خاص Markdown، assert به درستی escape شوند."""
        text = "*bold* _italic_ `code` [link](url)"
        escaped_text = escape_markdown(text)
        assert escaped_text == "\\*bold\\* \\_italic\\_ \\`code\\` [link](url)"

        text_with_backticks = "`code block`"
        escaped_text_with_backticks = escape_markdown(text_with_backticks)
        assert escaped_text_with_backticks == "\\`code block\\`"

        text_with_brackets = "[text]"
        escaped_text_with_brackets = escape_markdown(text_with_brackets)
        assert escaped_text_with_brackets == "[text]" # Brackets are not escaped by escape_markdown

    def test_truncate_text(self):
        """D20: متن طولانی، assert به درستی truncate شود."""
        long_text = "This is a very long sentence that needs to be truncated at a certain length."

        # Truncate with default max_len (200) - should not truncate
        truncated = truncate_text(long_text)
        assert truncated == long_text

        # Truncate to a shorter length, should end with ellipsis
        truncated = truncate_text(long_text, max_len=30)
        assert truncated == "This is a very long sentence…"
        assert len(truncated) <= 30

        # Truncate exactly at a word boundary
        truncated = truncate_text(long_text, max_len=19)
        assert truncated == "This is a very…"

        # Test with custom suffix
        truncated = truncate_text(long_text, max_len=25, suffix="...")
        assert truncated == "This is a very long..."

        # Test with text shorter than max_len
        short_text = "Short text."
        truncated = truncate_text(short_text, max_len=50)
        assert truncated == short_text


