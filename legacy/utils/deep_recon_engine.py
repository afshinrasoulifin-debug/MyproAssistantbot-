
"""
utils/deep_recon_engine.py — REAL DEEP RECON (OMEGA)
===================================================
Uses web analysis logic to extract signals from prospect websites.
"""

import logging
import aiohttp
import re
from typing import Any, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class DeepReconEngine:
    """
    Analyzes prospect websites for real business signals.
    """

    def __init__(self):
        self._headers = {"User-Agent": "Arki-Recon-Bot/1.0 (Nordic Minimalist Research)"}
        self._tech_patterns = {
            "Shopify": r"cdn\.shopify\.com|myshopify\.com",
            "WordPress": r"wp-content|wp-includes",
            "Wix": r"wix\.com|wixsite\.com",
            "Google Analytics": r"google-analytics\.com|gtag",
            "Facebook Pixel": r"fbevents\.js",
            "HubSpot": r"hubspot\.com"
        }

    async def deep_recon(self, url: str) -> Dict[str, Any]:
        """
        Actually attempts to fetch and analyze the target URL.
        """
        if not url.startswith("http"):
            url = f"https://{url}"
            
        logger.info(f"🔎 Deep Recon: Analyzing {url}...")
        
        recon_data = {
            "url": url,
            "tech_stack": [],
            "growth_signals": [],
            "social_links": [],
            "business_type": "Unknown",
            "metadata": {}
        }
        
        try:
            async with aiohttp.ClientSession(headers=self._headers) as session:
                async with session.get(url, timeout=15, allow_redirects=True) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 1. Tech Stack Detection
                        for tech, pattern in self._tech_patterns.items():
                            if re.search(pattern, html, re.I):
                                recon_data["tech_stack"].append(tech)
                        
                        # 2. Social Links Extraction
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if any(p in href for p in ["instagram.com", "linkedin.com", "pinterest.com", "facebook.com"]):
                                if href not in recon_data["social_links"]:
                                    recon_data["social_links"].append(href)
                        
                        # 3. Growth & Business Signals
                        text_content = soup.get_text().lower()
                        if any(k in text_content for k in ["careers", "hiring", "open positions", "join us"]):
                            recon_data["growth_signals"].append("Active Hiring")
                        if any(k in text_content for k in ["showroom", "visit us", "our store"]):
                            recon_data["business_type"] = "Physical Retail/Showroom"
                        elif any(k in text_content for k in ["b2b", "wholesale", "trade program"]):
                            recon_data["business_type"] = "B2B/Wholesale"
                        
                        # 4. Metadata
                        recon_data["metadata"]["title"] = soup.title.string if soup.title else "No Title"
                        meta_desc = soup.find("meta", attrs={"name": "description"})
                        recon_data["metadata"]["description"] = meta_desc["content"] if meta_desc else "No Description"
                        
                    else:
                        logger.warning(f"⚠️ Recon: Site returned status {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ Recon Error for {url}: {e}")
            
        return recon_data


