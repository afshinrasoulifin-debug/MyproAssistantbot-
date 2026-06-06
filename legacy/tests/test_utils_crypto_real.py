

import pytest
from unittest.mock import patch
import os

from arki_project.utils.crypto import encrypt_dict, decrypt_dict
from arki_project.utils.crypto_engine import hash_data # Assuming hash_data is directly available

@pytest.mark.asyncio
class TestUtilsCrypto:

    @pytest.fixture(autouse=True)
    def mock_encryption_key(self):
        with patch.dict(os.environ, {"ENCRYPTION_KEY": "test-secret-key-for-testing"}):
            # Clear the cached key in crypto.py to ensure our mock is used
            from arki_project.utils import crypto
            crypto._KEY = None
            yield

    async def test_crypto_encrypt_decrypt_roundtrip(self):
        """D8: متن ساده encrypt، سپس decrypt، assert برابری."""
        original_data = {"message": "Hello, World!", "value": 123}
        encrypted_token = encrypt_dict(original_data)
        decrypted_data = decrypt_dict(encrypted_token)
        assert decrypted_data == original_data

    async def test_crypto_different_plaintext_different_cipher(self):
        """D9: دو متن مختلف، assert دو cipher متفاوت."""
        data1 = {"message": "First message"}
        data2 = {"message": "Second message"}

        encrypted_token1 = encrypt_dict(data1)
        encrypted_token2 = encrypt_dict(data2)

        assert encrypted_token1 != encrypted_token2

    async def test_crypto_wrong_key_fails(self):
        """D10: با کلید اشتباه decrypt، assert exception."""
        original_data = {"message": "Secret"}
        encrypted_token = encrypt_dict(original_data)

        with patch.dict(os.environ, {"ENCRYPTION_KEY": "wrong-secret-key"}):
            # Clear the cached key in crypto.py to ensure our mock is used
            from arki_project.utils import crypto
            crypto._KEY = None
            with pytest.raises(Exception): # Expecting a JSONDecodeError or similar from corrupted data
                decrypt_dict(encrypted_token)

    async def test_crypto_engine_hash_consistent(self):
        """D11: یک متن دو بار hash، assert نتایج یکسان."""
        text_to_hash = "This is a test string."
        hash1 = hash_data(text_to_hash)
        hash2 = hash_data(text_to_hash)
        assert hash1 == hash2

    async def test_crypto_engine_hash_unique(self):
        """D12: دو متن مختلف، assert hash متفاوت."""
        text1 = "First unique string."
        text2 = "Second unique string."
        hash1 = hash_data(text1)
        hash2 = hash_data(text2)
        assert hash1 != hash2


