
"""
utils/intelligence_bridge.py — Arki Intelligence Bridge v1.0
═════════════════════════════════════════════════════════════
Translates raw intelligence from OMEGA engines into actionable
insights for content generation and campaign optimization.
"""

import logging
from typing import Dict
from arki_project.utils.deep_recon_engine import DeepReconReport

logger = logging.getLogger(__name__)

class IntelligenceBridge:
    """
    Bridges the gap between raw data (Recon) and creative output (Content).
    """

    @staticmethod
    def extract_personalization_hooks(report: DeepReconReport) -> Dict[str, str]:
        """
        Extracts specific 'hooks' from a recon report that can be used
        to prove 'we did our homework' in an outreach email.
        """
        hooks = {}
        
        # 1. Tech Stack Hook
        if report.tech_profile:
            tech = report.tech_profile
            if tech.ecommerce:
                hooks["tech_hook"] = f"I noticed you're using {tech.ecommerce} for your shop — it looks great."
            elif tech.cms == "WordPress":
                hooks["tech_hook"] = "I saw your site is built on WordPress; the design is very clean."

        # 2. Growth Signal Hook
        if report.growth_signals:
            # Pick the strongest signal
            best_signal = max(report.growth_signals, key=lambda x: x.strength)
            if best_signal.signal_type == "hiring":
                hooks["growth_hook"] = f"I saw you're currently expanding the team — exciting times for {report.target}!"
            elif best_signal.signal_type == "new_product":
                hooks["growth_hook"] = f"Congratulations on the new product launch mentioned in your recent news."

        # 3. Social Presence Hook
        if report.social_profiles:
            ig = next((s for s in report.social_profiles if s.platform == "instagram"), None)
            if ig:
                hooks["social_hook"] = "Your Instagram feed really captures the aesthetic we admire at ArkiObjects."

        # 4. Content/Aesthetic Hook
        if report.crawled_pages:
            about_page = next((p for p in report.crawled_pages if p.get("page_type") == "about"), None)
            if about_page and "minimalism" in about_page.get("meta_description", "").lower():
                hooks["aesthetic_hook"] = "Your focus on minimalism aligns perfectly with our Nordic design philosophy."

        return hooks

    @staticmethod
    def calculate_strategic_priority(report: DeepReconReport) -> float:
        """
        Calculates a priority score (0-100) based on business signals.
        """
        score = 50.0  # Base
        
        # Tech stack indicators
        if report.tech_profile:
            if report.tech_profile.ecommerce: score += 15
            if "Google Analytics" in report.tech_profile.analytics: score += 5
            
        # Growth signals
        score += len(report.growth_signals) * 10
        
        # Digital footprint
        score += len(report.social_profiles) * 5
        
        return min(100.0, score)


