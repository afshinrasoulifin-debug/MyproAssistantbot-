

import pytest
import os
from collections import Counter

from arki_project.utils.titanium.crypto import (
    csprng_int,
    csprng_float,
    csprng_choice,
    csprng_weighted_choice,
    hmac_sign,
    hmac_verify,
    secure_hex,
    secure_request_id
)

class TestUtilsTitaniumCrypto:

    def test_csprng_int_range(self):
        """D21: csprng_int باید عددی در بازه [lo, hi] برگرداند."""
        lo, hi = 10, 20
        for _ in range(100):
            result = csprng_int(lo, hi)
            assert lo <= result <= hi

        # Test edge case where lo == hi
        assert csprng_int(5, 5) == 5

    def test_csprng_int_distribution_basic(self):
        """D21: csprng_int باید توزیع نسبتاً یکنواختی داشته باشد (غیرقطعی)."""
        lo, hi = 0, 9
        num_samples = 1000
        results = [csprng_int(lo, hi) for _ in range(num_samples)]
        counts = Counter(results)

        # Check that all numbers in range appear at least once (probabilistically)
        for i in range(lo, hi + 1):
            assert counts[i] > 0

        # Check for reasonable distribution (not too skewed, within 3 standard deviations)
        expected_avg = num_samples / (hi - lo + 1)
        for count in counts.values():
            assert abs(count - expected_avg) < expected_avg * 0.5 # Allow for 50% deviation for non-deterministic test

    def test_csprng_float_range(self):
        """D22: csprng_float باید عددی در بازه [0.0, 1.0) برگرداند."""
        for _ in range(100):
            result = csprng_float()
            assert 0.0 <= result < 1.0

    def test_csprng_choice_selection(self):
        """D23: csprng_choice باید یکی از آیتم‌های موجود در sequence را انتخاب کند."""
        sequence = ["apple", "banana", "cherry"]
        for _ in range(100):
            result = csprng_choice(sequence)
            assert result in sequence

        with pytest.raises(IndexError):
            csprng_choice([])

    def test_csprng_weighted_choice_distribution(self):
        """D24: csprng_weighted_choice باید وزن‌ها را در انتخاب رعایت کند."""
        items = ["A", "B", "C"]
        weights = [0.6, 0.3, 0.1]
        num_samples = 10000
        results = [csprng_weighted_choice(items, weights) for _ in range(num_samples)]
        counts = Counter(results)

        total_weight = sum(weights)
        for i, item in enumerate(items):
            expected_count = (weights[i] / total_weight) * num_samples
            # Allow for a reasonable deviation (e.g., 5% of total samples)
            assert abs(counts[item] - expected_count) < num_samples * 0.05

        with pytest.raises(ValueError):
            csprng_weighted_choice(["A"], [1, 2]) # Mismatched lengths

        with pytest.raises(IndexError):
            csprng_weighted_choice([], []) # Empty sequence

    def test_hmac_sign_verify_roundtrip(self):
        """D25: hmac_sign و hmac_verify باید به درستی کار کنند."""
        key = os.urandom(32)
        data = b"some secret data"

        signature = hmac_sign(key, data)
        assert isinstance(signature, str)
        assert len(signature) == 64 # SHA256 produces 64 hex chars

        # Verify with correct key and data
        assert hmac_verify(key, data, signature) is True

        # Verify with incorrect key
        wrong_key = os.urandom(32)
        assert hmac_verify(wrong_key, data, signature) is False

        # Verify with incorrect data
        wrong_data = b"other data"
        assert hmac_verify(key, wrong_data, signature) is False

        # Verify with incorrect signature format
        assert hmac_verify(key, data, "invalid_signature") is False

    def test_secure_hex(self):
        """D26: secure_hex باید یک رشته هگز امن تولید کند."""
        hex_str = secure_hex(n_bytes=16)
        assert isinstance(hex_str, str)
        assert len(hex_str) == 32 # 16 bytes = 32 hex characters
        assert all(c in "0123456789abcdef" for c in hex_str)

    def test_secure_request_id(self):
        """D27: secure_request_id باید یک ID درخواست امن و منحصر به فرد تولید کند."""
        req_id1 = secure_request_id()
        req_id2 = secure_request_id()
        assert isinstance(req_id1, str)
        assert len(req_id1) == 24 # 12 bytes = 24 hex characters
        assert req_id1 != req_id2



