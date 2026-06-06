
"""
utils/hyper_personalization_engine.py — REAL HYPER-PERSONALIZATION (OMEGA)
==========================================================================
Uses GPT-4 to craft unique email hooks based on deep recon data.
"""

import logging
from typing import Any, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class HyperPersonalizationEngine:
    """
    Crafts hyper-personalized outreach content using REAL AI.
    """

    def __init__(self, ai_client: Optional[OpenAI] = None):
        self._ai = ai_client or OpenAI()

    async def craft_personalized_email(
        self, 
        prospect: Dict[str, Any], 
        recon_report: Dict[str, Any], 
        base_content: str,
        language: str = "en"
    ) -> str:
        """
        Uses GPT-4 to create a high-conversion email hook.
        """
        logger.info(f"🎯 Personalizer: Crafting hook for {prospect.get('business_name')}...")
        
        prompt = f"""
        Prospect: {prospect.get('business_name')}
        Recon Data: {recon_report}
        Base Offer: {base_content}
        Language: {language}
        
        Task: Write a 1-2 sentence hyper-personalized opening hook for an email. 
        Focus on their specific tech stack, growth signals, or website details.
        Be professional, minimalist, and intriguing.
        """
        
        try:
            response = self._ai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "system", "content": "You are a master of B2B psychological outreach."},
                          {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ Personalizer AI Error: {e}")
            return f"I was impressed by {prospect.get('business_name')}'s commitment to design excellence."


