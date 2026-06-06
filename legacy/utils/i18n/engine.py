
"""
Internationalization Engine v29.0.0
Supports multiple languages with fallback.
"""
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path



logger = logging.getLogger(__name__)

LOCALE_DIR = Path(__file__).parent / "locales"


class I18nEngine:
    """Multi-language translation engine."""

    def __init__(self, default_lang: str = "fa") -> None:
        self.default_lang = default_lang
        self._translations: Dict[str, Dict[str, str]] = {}
        self._user_langs: Dict[int, str] = {}
        self._load_all()

    def _load_all(self) -> Any:
        """Load all locale files."""
        if not LOCALE_DIR.exists():
            LOCALE_DIR.mkdir(parents=True, exist_ok=True)
            return

        for locale_file in LOCALE_DIR.glob("*.json"):
            lang = locale_file.stem
            try:
                with open(locale_file, encoding='utf-8') as f:
                    self._translations[lang] = json.load(f)
                logger.info("Loaded locale: %s (%d keys)", 
                           lang, len(self._translations[lang]))
            except Exception as e:
                logger.error("Failed to load locale %s: %s", lang, e)

    def t(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        """
        Translate a key.

        Usage:
            _t("welcome_message", name="Ali")
            _t("error.not_found", lang="en")
        """
        lang = lang or self.default_lang

        # Try requested language
        text = self._translations.get(lang, {}).get(key)

        # Fallback to default
        if text is None and lang != self.default_lang:
            text = self._translations.get(self.default_lang, {}).get(key)

        # Fallback to key itself
        if text is None:
            return key

        # Format with kwargs
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, IndexError):
            return text

    def set_user_lang(self, user_id: int, lang: str) -> None:
        """Set preferred language for a user."""
        self._user_langs[user_id] = lang

    def get_user_lang(self, user_id: int) -> str:
        """Get user's preferred language."""
        return self._user_langs.get(user_id, self.default_lang)

    def t_user(self, key: str, user_id: int, **kwargs) -> str:
        """Translate using user's preferred language."""
        lang = self.get_user_lang(user_id)
        return self.t(key, lang=lang, **kwargs)

    @property
    def available_languages(self) -> list:
        return list(self._translations.keys())

    @property
    def stats(self) -> dict:
        return {
            "languages": len(self._translations),
            "total_keys": sum(len(v) for v in self._translations.values()),
            "users_with_pref": len(self._user_langs),
        }


# Singleton
_engine: Optional[I18nEngine] = None

def get_i18n() -> I18nEngine:
    global _engine
    if _engine is None:
        _engine = I18nEngine()
    return _engine

def _t(key: str, **kwargs) -> str:
    """Quick translate helper."""
    return get_i18n().t(key, **kwargs)


