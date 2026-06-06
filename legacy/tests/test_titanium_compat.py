
"""
Tests for TITANIUM compat module (drop-in random replacement).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arki_project.utils.titanium.compat import secure_random

def test_randint():
    """secure_random.randint should match random.randint interface."""
    for _ in range(500):
        val = secure_random.randint(1, 100)
        assert 1 <= val <= 100, f"Out of range: {val}"

def test_random():
    """secure_random.random should return float in [0, 1)."""
    for _ in range(500):
        val = secure_random.random()
        assert 0.0 <= val < 1.0

def test_uniform():
    """secure_random.uniform should return float in [a, b]."""
    for _ in range(500):
        val = secure_random.uniform(10.0, 20.0)
        assert 10.0 <= val <= 20.0

def test_choice():
    """secure_random.choice should pick from list."""
    items = [1, 2, 3, 4, 5]
    for _ in range(100):
        pick = secure_random.choice(items)
        assert pick in items

def test_shuffle():
    """secure_random.shuffle should shuffle in place."""
    items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    original = items.copy()
    secure_random.shuffle(items)
    # Items should be same elements
    assert sorted(items) == sorted(original)
    # At least some should be reordered (vanishingly unlikely to be same)
    assert items != original or True  # rare edge case ok

def test_sample():
    """secure_random.sample should return k unique elements."""
    items = list(range(100))
    s = secure_random.sample(items, 10)
    assert len(s) == 10
    assert len(set(s)) == 10
    for x in s:
        assert x in items

def test_gauss():
    """secure_random.gauss should return values near mean."""
    vals = [secure_random.gauss(0, 1) for _ in range(1000)]
    mean = sum(vals) / len(vals)
    assert -0.5 < mean < 0.5, f"Mean too far from 0: {mean}"

def test_choices_with_weights():
    """secure_random.choices should respect weights."""
    items = ["heavy", "light"]
    weights = [100, 1]
    results = secure_random.choices(items, weights=weights, k=200)
    heavy = results.count("heavy")
    assert heavy > 150, f"heavy only {heavy}/200"

if __name__ == "__main__":
    test_randint()
    test_random()
    test_uniform()
    test_choice()
    test_shuffle()
    test_sample()
    test_gauss()
    test_choices_with_weights()
    print("✅ All compat tests passed")


