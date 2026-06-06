
"""
utils/multi_format_content_factory.py — REAL CONTENT FACTORY (TITAN)
====================================================================
Uses GPT-4 to generate high-quality, brand-aligned marketing content.
"""

import logging
from typing import Any, Dict, Optional
from enum import Enum
from openai import OpenAI

logger = logging.getLogger(__name__)

class ContentFormat(Enum):
    ARTICLE = "article"
    NEWSLETTER = "newsletter"
    VIDEO_SCRIPT = "video_script"
    SOCIAL_THREAD = "social_thread"

class MultiFormatContentFactory:
    """
    Advanced content generation engine using REAL AI.
    """

    def __init__(self, ai_client: Optional[OpenAI] = None):
        self._ai = ai_client or OpenAI()
        self._brand_voice = "Nordic, Minimalist, Artisan, Sustainable Luxury"

    async def generate_content(
        self, 
        format_type: ContentFormat, 
        topic: str, 
        target_audience: str = "B2B Designers"
    ) -> Dict[str, Any]:
        """
        Generates real content using GPT-4.
        """
        logger.info(f"✍️ Content Factory: Manufacturing {format_type.value} via GPT-4...")
        
        prompt = f"""
        Topic: {topic}
        Format: {format_type.value}
        Audience: {target_audience}
        Brand Voice: {self._brand_voice}
        
        Generate professional content including Title and Body. 
        If it's a video script, include Scene descriptions.
        Format: JSON.
        """
        
        try:
            response = self._ai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "system", "content": "You are a Senior Copywriter for Arki, a luxury Nordic design brand."},
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"❌ Content Factory AI Error: {e}")
            return {"title": f"The Art of {topic}", "body": "Content generation failed, using fallback."}


