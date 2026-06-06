
from __future__ import annotations
"""
tg_bot/utils/ai_output_validator.py — AI Output Validation v9.4
Validate and parse structured AI responses.
"""
import json
import logging
import re
from typing import Dict, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class AIOutputValidator:
    """Validate and extract structured data from AI responses."""

    @staticmethod
    def extract_json(text: str) -> Optional[Dict]:
        """Extract JSON from AI response (handles markdown code blocks)."""
        # Try direct parse
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            logger.debug("Suppressed: %s", _exc)

        # Try extracting from code blocks
        patterns = [
            r'```json\s*\n?(.*?)\n?```',
            r'```\s*\n?(.*?)\n?```',
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1) if '```' in pattern else match.group(0))
                except (json.JSONDecodeError, IndexError):
                    continue
        return None

    @staticmethod
    def validate_response(text: str, required_fields: list = None,
                         max_length: int = 0, min_length: int = 0) -> Dict:
        """Validate AI text response."""
        issues = []

        if not text or not text.strip():
            return {"valid": False, "issues": ["Empty response"]}

        if max_length and len(text) > max_length:
            issues.append(f"Too long: {len(text)} > {max_length}")

        if min_length and len(text) < min_length:
            issues.append(f"Too short: {len(text)} < {min_length}")

        if required_fields:
            data = AIOutputValidator.extract_json(text)
            if data:
                for field in required_fields:
                    if field not in data:
                        issues.append(f"Missing field: {field}")

        return {"valid": len(issues) == 0, "issues": issues, "length": len(text)}

    @staticmethod
    def sanitize_response(text: str) -> str:
        """Clean up AI response for safe display."""
        if not text:
            return ""
        # Remove potential prompt leakage
        leakage_patterns = [
            r'\[INST\].*?\[/INST\]',
            r'<\|system\|>.*?<\|end\|>',
            r'<s>.*?</s>',
        ]
        for pattern in leakage_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL)
        return text.strip()


def get_output_validator() -> AIOutputValidator:
    return AIOutputValidator()


