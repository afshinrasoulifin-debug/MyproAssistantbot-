
from __future__ import annotations
"""
utils/geo_consistency.py — Geographic Consistency Engine v1.0-TITAN
═══════════════════════════════════════════════════════════════════
Ensures ALL browser fingerprint vectors are geographically consistent:

 1. Timezone ↔ Proxy IP country/city alignment
 2. Accept-Language header matching locale
 3. Navigator.language / navigator.languages consistency
 4. Intl API fingerprint (date/number/currency formatting)
 5. Keyboard layout matching region
 6. DNS resolver geo-awareness
 7. Date.getTimezoneOffset() consistency
 8. Screen locale indicators (currency symbols, date order)

Author: Arki Engine TITAN
License: Proprietary
"""


import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("arki.geo_consistency")


# ═══════════════════════════════════════════════════════════
# Geographic Profile Database
# ═══════════════════════════════════════════════════════════

class Region(Enum):
    """Major geographic regions."""
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    NORDIC = "nordic"
    ASIA_PACIFIC = "asia_pacific"
    MIDDLE_EAST = "middle_east"
    SOUTH_AMERICA = "south_america"
    AFRICA = "africa"
    OCEANIA = "oceania"


@dataclass
class GeoLocale:
    """Complete locale configuration for a geographic location."""
    country_code: str          # ISO 3166-1 alpha-2: "FI"
    country_name: str          # "Finland"
    region: Region             # NORDIC
    primary_language: str      # "fi"
    languages: List[str] = field(default_factory=list)   # ["fi", "en-US", "en"]
    accept_language: str = ""  # "fi,en-US;q=0.9,en;q=0.8"
    timezone: str = ""         # "Europe/Helsinki"
    timezone_offset: int = 0   # Minutes offset from UTC (negative = west)
    currency: str = ""         # "EUR"
    currency_symbol: str = ""  # "€"
    date_format: str = ""      # "dd.MM.yyyy"
    number_decimal: str = ""   # ","
    number_group: str = ""     # " " or "."
    keyboard_layout: str = ""  # "fi"
    phone_prefix: str = ""     # "+358"
    measurement: str = "metric"  # "metric" or "imperial"
    writing_direction: str = "ltr"  # "ltr" or "rtl"
    dns_servers: List[str] = field(default_factory=list)
    common_search_engines: List[str] = field(default_factory=list)
    popular_websites: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "country_code": self.country_code,
            "country_name": self.country_name,
            "region": self.region.value,
            "primary_language": self.primary_language,
            "languages": self.languages,
            "accept_language": self.accept_language,
            "timezone": self.timezone,
            "timezone_offset": self.timezone_offset,
            "currency": self.currency,
            "date_format": self.date_format,
            "number_decimal": self.number_decimal,
            "number_group": self.number_group,
            "keyboard_layout": self.keyboard_layout,
            "measurement": self.measurement,
            "writing_direction": self.writing_direction,
        }


# ── Complete locale database ──

GEO_DATABASE: Dict[str, GeoLocale] = {
    "FI": GeoLocale(
        country_code="FI", country_name="Finland", region=Region.NORDIC,
        primary_language="fi", languages=["fi", "en-US", "en"],
        accept_language="fi,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Helsinki", timezone_offset=-120,
        currency="EUR", currency_symbol="€",
        date_format="d.M.yyyy", number_decimal=",", number_group="\u00a0",
        keyboard_layout="fi", phone_prefix="+358",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.fi", "bing.com"],
        popular_websites=["yle.fi", "hs.fi", "iltalehti.fi", "mtv.fi"],
    ),
    "SE": GeoLocale(
        country_code="SE", country_name="Sweden", region=Region.NORDIC,
        primary_language="sv", languages=["sv", "en-US", "en"],
        accept_language="sv,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Stockholm", timezone_offset=-60,
        currency="SEK", currency_symbol="kr",
        date_format="yyyy-MM-dd", number_decimal=",", number_group="\u00a0",
        keyboard_layout="sv", phone_prefix="+46",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.se", "bing.com"],
        popular_websites=["aftonbladet.se", "expressen.se", "svt.se"],
    ),
    "NO": GeoLocale(
        country_code="NO", country_name="Norway", region=Region.NORDIC,
        primary_language="nb", languages=["nb", "en-US", "en"],
        accept_language="nb,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Oslo", timezone_offset=-60,
        currency="NOK", currency_symbol="kr",
        date_format="dd.MM.yyyy", number_decimal=",", number_group="\u00a0",
        keyboard_layout="no", phone_prefix="+47",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.no", "bing.com"],
        popular_websites=["vg.no", "nrk.no", "dagbladet.no"],
    ),
    "DK": GeoLocale(
        country_code="DK", country_name="Denmark", region=Region.NORDIC,
        primary_language="da", languages=["da", "en-US", "en"],
        accept_language="da,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Copenhagen", timezone_offset=-60,
        currency="DKK", currency_symbol="kr",
        date_format="dd.MM.yyyy", number_decimal=",", number_group=".",
        keyboard_layout="da", phone_prefix="+45",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.dk", "bing.com"],
        popular_websites=["bt.dk", "dr.dk", "jyllands-posten.dk"],
    ),
    "US": GeoLocale(
        country_code="US", country_name="United States", region=Region.NORTH_AMERICA,
        primary_language="en-US", languages=["en-US", "en"],
        accept_language="en-US,en;q=0.9",
        timezone="America/New_York", timezone_offset=300,
        currency="USD", currency_symbol="$",
        date_format="M/d/yyyy", number_decimal=".", number_group=",",
        keyboard_layout="us", phone_prefix="+1", measurement="imperial",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.com", "bing.com"],
        popular_websites=["google.com", "youtube.com", "amazon.com", "reddit.com"],
    ),
    "CA": GeoLocale(
        country_code="CA", country_name="Canada", region=Region.NORTH_AMERICA,
        primary_language="en-CA", languages=["en-CA", "en-US", "en", "fr-CA"],
        accept_language="en-CA,en-US;q=0.9,en;q=0.8,fr-CA;q=0.7",
        timezone="America/Toronto", timezone_offset=300,
        currency="CAD", currency_symbol="$",
        date_format="yyyy-MM-dd", number_decimal=".", number_group=",",
        keyboard_layout="us", phone_prefix="+1",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.ca", "bing.com"],
        popular_websites=["google.ca", "cbc.ca", "yahoo.ca"],
    ),
    "GB": GeoLocale(
        country_code="GB", country_name="United Kingdom", region=Region.EUROPE,
        primary_language="en-GB", languages=["en-GB", "en"],
        accept_language="en-GB,en;q=0.9",
        timezone="Europe/London", timezone_offset=0,
        currency="GBP", currency_symbol="£",
        date_format="dd/MM/yyyy", number_decimal=".", number_group=",",
        keyboard_layout="gb", phone_prefix="+44",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.co.uk", "bing.com"],
        popular_websites=["bbc.co.uk", "theguardian.com", "amazon.co.uk"],
    ),
    "DE": GeoLocale(
        country_code="DE", country_name="Germany", region=Region.EUROPE,
        primary_language="de", languages=["de", "en-US", "en"],
        accept_language="de,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Berlin", timezone_offset=-60,
        currency="EUR", currency_symbol="€",
        date_format="dd.MM.yyyy", number_decimal=",", number_group=".",
        keyboard_layout="de", phone_prefix="+49",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.de", "bing.com"],
        popular_websites=["spiegel.de", "bild.de", "amazon.de", "tagesschau.de"],
    ),
    "FR": GeoLocale(
        country_code="FR", country_name="France", region=Region.EUROPE,
        primary_language="fr", languages=["fr", "en-US", "en"],
        accept_language="fr,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Paris", timezone_offset=-60,
        currency="EUR", currency_symbol="€",
        date_format="dd/MM/yyyy", number_decimal=",", number_group="\u00a0",
        keyboard_layout="fr", phone_prefix="+33",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.fr", "bing.com"],
        popular_websites=["lemonde.fr", "lefigaro.fr", "amazon.fr"],
    ),
    "NL": GeoLocale(
        country_code="NL", country_name="Netherlands", region=Region.EUROPE,
        primary_language="nl", languages=["nl", "en-US", "en"],
        accept_language="nl,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Amsterdam", timezone_offset=-60,
        currency="EUR", currency_symbol="€",
        date_format="dd-MM-yyyy", number_decimal=",", number_group=".",
        keyboard_layout="us-intl", phone_prefix="+31",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.nl", "bing.com"],
        popular_websites=["nu.nl", "tweakers.net", "nos.nl"],
    ),
    "IT": GeoLocale(
        country_code="IT", country_name="Italy", region=Region.EUROPE,
        primary_language="it", languages=["it", "en-US", "en"],
        accept_language="it,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Rome", timezone_offset=-60,
        currency="EUR", currency_symbol="€",
        date_format="dd/MM/yyyy", number_decimal=",", number_group=".",
        keyboard_layout="it", phone_prefix="+39",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.it", "bing.com"],
        popular_websites=["corriere.it", "repubblica.it", "amazon.it"],
    ),
    "ES": GeoLocale(
        country_code="ES", country_name="Spain", region=Region.EUROPE,
        primary_language="es", languages=["es", "en-US", "en"],
        accept_language="es,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Madrid", timezone_offset=-60,
        currency="EUR", currency_symbol="€",
        date_format="dd/MM/yyyy", number_decimal=",", number_group=".",
        keyboard_layout="es", phone_prefix="+34",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.es", "bing.com"],
        popular_websites=["elpais.com", "elmundo.es", "amazon.es"],
    ),
    "AU": GeoLocale(
        country_code="AU", country_name="Australia", region=Region.OCEANIA,
        primary_language="en-AU", languages=["en-AU", "en"],
        accept_language="en-AU,en;q=0.9",
        timezone="Australia/Sydney", timezone_offset=-600,
        currency="AUD", currency_symbol="$",
        date_format="dd/MM/yyyy", number_decimal=".", number_group=",",
        keyboard_layout="us", phone_prefix="+61",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.com.au", "bing.com"],
        popular_websites=["news.com.au", "abc.net.au", "amazon.com.au"],
    ),
    "JP": GeoLocale(
        country_code="JP", country_name="Japan", region=Region.ASIA_PACIFIC,
        primary_language="ja", languages=["ja", "en-US", "en"],
        accept_language="ja,en-US;q=0.9,en;q=0.8",
        timezone="Asia/Tokyo", timezone_offset=-540,
        currency="JPY", currency_symbol="¥",
        date_format="yyyy/MM/dd", number_decimal=".", number_group=",",
        keyboard_layout="jp", phone_prefix="+81",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.co.jp", "yahoo.co.jp"],
        popular_websites=["yahoo.co.jp", "amazon.co.jp", "rakuten.co.jp"],
    ),
    "BR": GeoLocale(
        country_code="BR", country_name="Brazil", region=Region.SOUTH_AMERICA,
        primary_language="pt-BR", languages=["pt-BR", "en-US", "en"],
        accept_language="pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        timezone="America/Sao_Paulo", timezone_offset=180,
        currency="BRL", currency_symbol="R$",
        date_format="dd/MM/yyyy", number_decimal=",", number_group=".",
        keyboard_layout="br", phone_prefix="+55",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.com.br", "bing.com"],
        popular_websites=["uol.com.br", "globo.com", "mercadolivre.com.br"],
    ),
    "IR": GeoLocale(
        country_code="IR", country_name="Iran", region=Region.MIDDLE_EAST,
        primary_language="fa", languages=["fa", "en-US", "en"],
        accept_language="fa,en-US;q=0.9,en;q=0.8",
        timezone="Asia/Tehran", timezone_offset=-210,
        currency="IRR", currency_symbol="﷼",
        date_format="yyyy/MM/dd", number_decimal="/", number_group=",",
        keyboard_layout="fa", phone_prefix="+98",
        writing_direction="rtl",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.com"],
        popular_websites=["digikala.com", "aparat.com", "divar.ir"],
    ),
    "AE": GeoLocale(
        country_code="AE", country_name="United Arab Emirates", region=Region.MIDDLE_EAST,
        primary_language="ar", languages=["ar", "en-US", "en"],
        accept_language="ar,en-US;q=0.9,en;q=0.8",
        timezone="Asia/Dubai", timezone_offset=-240,
        currency="AED", currency_symbol="د.إ",
        date_format="dd/MM/yyyy", number_decimal=".", number_group=",",
        keyboard_layout="ar", phone_prefix="+971",
        writing_direction="rtl",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.ae", "bing.com"],
        popular_websites=["google.ae", "amazon.ae", "noon.com"],
    ),
    "IN": GeoLocale(
        country_code="IN", country_name="India", region=Region.ASIA_PACIFIC,
        primary_language="en-IN", languages=["en-IN", "hi", "en"],
        accept_language="en-IN,en;q=0.9,hi;q=0.8",
        timezone="Asia/Kolkata", timezone_offset=-330,
        currency="INR", currency_symbol="₹",
        date_format="dd/MM/yyyy", number_decimal=".", number_group=",",
        keyboard_layout="us", phone_prefix="+91",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["google.co.in", "bing.com"],
        popular_websites=["flipkart.com", "amazon.in", "times ofindia.indiatimes.com"],
    ),
    "KR": GeoLocale(
        country_code="KR", country_name="South Korea", region=Region.ASIA_PACIFIC,
        primary_language="ko", languages=["ko", "en-US", "en"],
        accept_language="ko,en-US;q=0.9,en;q=0.8",
        timezone="Asia/Seoul", timezone_offset=-540,
        currency="KRW", currency_symbol="₩",
        date_format="yyyy. M. d.", number_decimal=".", number_group=",",
        keyboard_layout="kr", phone_prefix="+82",
        dns_servers=["8.8.8.8", "1.1.1.1"],
        common_search_engines=["naver.com", "google.co.kr"],
        popular_websites=["naver.com", "daum.net", "coupang.com"],
    ),
    "PL": GeoLocale(
        country_code="PL", country_name="Poland", region=Region.EUROPE,
        primary_language="pl", languages=["pl", "en-US", "en"],
        accept_language="pl,en-US;q=0.9,en;q=0.8",
        timezone="Europe/Warsaw", timezone_offset=-60,
        currency="PLN", currency_symbol="zł",
        date_format="dd.MM.yyyy", number_decimal=",", number_group="\u00a0",
        keyboard_layout="pl", phone_prefix="+48",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        common_search_engines=["google.pl", "bing.com"],
        popular_websites=["onet.pl", "wp.pl", "allegro.pl"],
    ),
}

# ── Timezone database for multi-timezone countries ──

US_TIMEZONES: Dict[str, Tuple[str, int]] = {
    "eastern": ("America/New_York", 300),
    "central": ("America/Chicago", 360),
    "mountain": ("America/Denver", 420),
    "pacific": ("America/Los_Angeles", 480),
    "alaska": ("America/Anchorage", 540),
    "hawaii": ("Pacific/Honolulu", 600),
}

CA_TIMEZONES: Dict[str, Tuple[str, int]] = {
    "eastern": ("America/Toronto", 300),
    "central": ("America/Winnipeg", 360),
    "mountain": ("America/Edmonton", 420),
    "pacific": ("America/Vancouver", 480),
    "atlantic": ("America/Halifax", 240),
}

AU_TIMEZONES: Dict[str, Tuple[str, int]] = {
    "eastern": ("Australia/Sydney", -600),
    "central": ("Australia/Adelaide", -570),
    "western": ("Australia/Perth", -480),
}


# ═══════════════════════════════════════════════════════════
# Intl API Fingerprint Generator
# ═══════════════════════════════════════════════════════════

class IntlFingerprint:
    """Generate JavaScript Intl API consistent fingerprints."""

    @staticmethod
    def date_format_script(locale: GeoLocale) -> str:
        """Generate JS that returns locale-consistent date formatting."""
        lang = locale.primary_language
        return f"""
        (() => {{
            const fmt = new Intl.DateTimeFormat('{lang}', {{
                year: 'numeric', month: 'numeric', day: 'numeric'
            }});
            return fmt.format(new Date(2024, 0, 15));
        }})()
        """

    @staticmethod
    def number_format_script(locale: GeoLocale) -> str:
        """Generate JS for locale-consistent number formatting."""
        lang = locale.primary_language
        return f"""
        (() => {{
            const fmt = new Intl.NumberFormat('{lang}');
            return fmt.format(1234567.89);
        }})()
        """

    @staticmethod
    def currency_format_script(locale: GeoLocale) -> str:
        """Generate JS for locale-consistent currency formatting."""
        lang = locale.primary_language
        cur = locale.currency
        return f"""
        (() => {{
            const fmt = new Intl.NumberFormat('{lang}', {{
                style: 'currency', currency: '{cur}'
            }});
            return fmt.format(1234.56);
        }})()
        """

    @staticmethod
    def collator_script(locale: GeoLocale) -> str:
        """Generate JS for locale-consistent string sorting."""
        lang = locale.primary_language
        return f"""
        (() => {{
            const col = new Intl.Collator('{lang}');
            return col.resolvedOptions().locale;
        }})()
        """

    @staticmethod
    def timezone_override_script(locale: GeoLocale) -> str:
        """
        Generate IIFE evasion script that overrides Date.getTimezoneOffset()
        and Intl.DateTimeFormat to return correct timezone.
        """
        tz = locale.timezone
        offset = locale.timezone_offset
        return f"""
        (() => {{
            // Override getTimezoneOffset
            const _origGetTZO = Date.prototype.getTimezoneOffset;
            Object.defineProperty(Date.prototype, 'getTimezoneOffset', {{
                value: function() {{ return {offset}; }},
                writable: false, configurable: true
            }});

            // Override Intl.DateTimeFormat resolvedOptions
            const _OrigDTF = Intl.DateTimeFormat;
            const _origResolvedOptions = _OrigDTF.prototype.resolvedOptions;
            _OrigDTF.prototype.resolvedOptions = function() {{
                const opts = _origResolvedOptions.call(this);
                opts.timeZone = '{tz}';
                return opts;
            }};
        }})();
        """

    @staticmethod
    def get_all_scripts(locale: GeoLocale) -> List[str]:
        """Get all Intl override scripts for a locale."""
        return [
            IntlFingerprint.timezone_override_script(locale),
        ]


# ═══════════════════════════════════════════════════════════
# Geographic Consistency Validator
# ═══════════════════════════════════════════════════════════

@dataclass
class ConsistencyIssue:
    """A detected inconsistency in geographic fingerprint."""
    field: str
    expected: str
    actual: str
    severity: str = "warning"  # "warning", "critical"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class ConsistencyReport:
    """Result of geographic consistency validation."""
    country_code: str = ""
    locale_name: str = ""
    issues: List[ConsistencyIssue] = field(default_factory=list)
    score: int = 100  # 0-100
    checked_fields: int = 0

    @property
    def is_consistent(self) -> bool:
        return len(self.issues) == 0

    @property
    def critical_issues(self) -> List[ConsistencyIssue]:
        return [i for i in self.issues if i.severity == "critical"]

    def summary(self) -> str:
        lines = [f"Geo Consistency: {self.score}/100 ({self.country_code})"]
        for issue in self.issues:
            marker = "🔴" if issue.severity == "critical" else "🟡"
            lines.append(f"  {marker} {issue.field}: expected '{issue.expected}', got '{issue.actual}'")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "country_code": self.country_code,
            "score": self.score,
            "is_consistent": self.is_consistent,
            "checked_fields": self.checked_fields,
            "issues": [i.to_dict() for i in self.issues],
        }


class GeoConsistencyValidator:
    """Validate that a browser fingerprint is geographically consistent."""

    @staticmethod
    def validate(
        country_code: str,
        timezone: str = "",
        languages: Optional[List[str]] = None,
        accept_language: str = "",
        timezone_offset: Optional[int] = None,
        currency: str = "",
        keyboard_layout: str = "",
    ) -> ConsistencyReport:
        """
        Validate that provided browser settings match the expected
        geographic profile for the given country.
        """
        locale = GEO_DATABASE.get(country_code.upper())
        if not locale:
            return ConsistencyReport(
                country_code=country_code, score=50,
                issues=[ConsistencyIssue(
                    "country", "known", country_code,
                    "warning", "Country not in database",
                )]
            )

        report = ConsistencyReport(
            country_code=country_code,
            locale_name=locale.country_name,
        )
        issues: List[ConsistencyIssue] = []
        checks = 0

        # 1. Timezone check
        if timezone:
            checks += 1
            if timezone != locale.timezone:
                # Check multi-timezone countries
                tz_ok = False
                if country_code == "US":
                    tz_ok = any(tz == timezone for tz, _ in US_TIMEZONES.values())
                elif country_code == "CA":
                    tz_ok = any(tz == timezone for tz, _ in CA_TIMEZONES.values())
                elif country_code == "AU":
                    tz_ok = any(tz == timezone for tz, _ in AU_TIMEZONES.values())

                if not tz_ok:
                    issues.append(ConsistencyIssue(
                        "timezone", locale.timezone, timezone,
                        "critical", "Timezone doesn't match country",
                    ))

        # 2. Language check
        if languages:
            checks += 1
            primary = languages[0] if languages else ""
            # The primary language should match or be close to locale
            expected_primary = locale.languages[0] if locale.languages else ""
            if primary and expected_primary:
                # Allow en-US for English-speaking countries, etc.
                primary_base = primary.split("-")[0]
                expected_base = expected_primary.split("-")[0]
                if primary_base != expected_base:
                    issues.append(ConsistencyIssue(
                        "primary_language", expected_primary, primary,
                        "critical",
                        "Primary language doesn't match country",
                    ))

        # 3. Accept-Language header check
        if accept_language:
            checks += 1
            expected_base = locale.primary_language.split("-")[0]
            if expected_base not in accept_language.lower():
                issues.append(ConsistencyIssue(
                    "accept_language", f"contains '{expected_base}'",
                    accept_language, "critical",
                    "Accept-Language missing expected locale",
                ))

        # 4. Timezone offset check
        if timezone_offset is not None:
            checks += 1
            if timezone_offset != locale.timezone_offset:
                # Multi-timezone check
                offsets_ok = False
                if country_code == "US":
                    offsets_ok = any(
                        off == timezone_offset for _, off in US_TIMEZONES.values()
                    )
                elif country_code == "CA":
                    offsets_ok = any(
                        off == timezone_offset for _, off in CA_TIMEZONES.values()
                    )
                elif country_code == "AU":
                    offsets_ok = any(
                        off == timezone_offset for _, off in AU_TIMEZONES.values()
                    )

                if not offsets_ok:
                    issues.append(ConsistencyIssue(
                        "timezone_offset", str(locale.timezone_offset),
                        str(timezone_offset), "warning",
                        "Timezone offset doesn't match",
                    ))

        # 5. Currency check
        if currency:
            checks += 1
            if currency != locale.currency:
                issues.append(ConsistencyIssue(
                    "currency", locale.currency, currency,
                    "warning", "Currency doesn't match country",
                ))

        # 6. Keyboard layout check
        if keyboard_layout:
            checks += 1
            if keyboard_layout != locale.keyboard_layout:
                issues.append(ConsistencyIssue(
                    "keyboard_layout", locale.keyboard_layout,
                    keyboard_layout, "warning",
                    "Keyboard layout doesn't match country",
                ))

        # Calculate score
        if checks > 0:
            critical_count = sum(1 for i in issues if i.severity == "critical")
            warning_count = sum(1 for i in issues if i.severity == "warning")
            score = max(0, 100 - (critical_count * 25) - (warning_count * 10))
        else:
            score = 100

        report.issues = issues
        report.score = score
        report.checked_fields = checks
        return report


# ═══════════════════════════════════════════════════════════
# Geographic Consistency Engine
# ═══════════════════════════════════════════════════════════

class GeoConsistencyEngine:
    """
    Main engine that builds geographically consistent browser profiles.

    Usage:
        engine = GeoConsistencyEngine()
        profile = engine.build_profile("FI")
        # profile has timezone, languages, headers, Intl scripts...
    """

    VERSION = "29.0.0"

    def __init__(self) -> None:
        self._profiles_generated = 0
        self._validations_run = 0

    def get_locale(self, country_code: str) -> Optional[GeoLocale]:
        """Get locale data for a country code."""
        return GEO_DATABASE.get(country_code.upper())

    def list_countries(self) -> List[str]:
        """List all supported country codes."""
        return sorted(GEO_DATABASE.keys())

    def list_regions(self) -> Dict[str, List[str]]:
        """Group countries by region."""
        result: Dict[str, List[str]] = {}
        for code, locale in GEO_DATABASE.items():
            region = locale.region.value
            if region not in result:
                result[region] = []
            result[region].append(code)
        return result

    def build_profile(
        self,
        country_code: str,
        timezone_variant: Optional[str] = None,
        add_secondary_language: bool = True,
        randomize_quality: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Build a complete geographically consistent browser profile.

        Args:
            country_code: ISO 3166-1 alpha-2 country code
            timezone_variant: For multi-tz countries (e.g. "pacific" for US)
            add_secondary_language: Whether to add English as fallback
            randomize_quality: 0.0-1.0, adds slight randomization to q-values

        Returns:
            Dict with all browser configuration fields
        """
        locale = GEO_DATABASE.get(country_code.upper())
        if not locale:
            # Fallback to US
            locale = GEO_DATABASE["US"]
            logger.warning("Unknown country '%s', falling back to US", country_code)

        self._profiles_generated += 1

        # Handle timezone variants
        timezone = locale.timezone
        tz_offset = locale.timezone_offset
        if timezone_variant:
            tz_map = {}
            if country_code.upper() == "US":
                tz_map = US_TIMEZONES
            elif country_code.upper() == "CA":
                tz_map = CA_TIMEZONES
            elif country_code.upper() == "AU":
                tz_map = AU_TIMEZONES

            if timezone_variant.lower() in tz_map:
                timezone, tz_offset = tz_map[timezone_variant.lower()]

        # Build Accept-Language with optional randomization
        if randomize_quality > 0:
            accept_lang = self._build_accept_language(locale, randomize_quality)
        else:
            accept_lang = locale.accept_language

        # Build languages array
        languages = list(locale.languages)
        if add_secondary_language and "en" not in [l.split("-")[0] for l in languages]:
            languages.append("en")

        # Generate Intl API override scripts
        intl_scripts = IntlFingerprint.get_all_scripts(locale)

        profile = {
            "country_code": country_code.upper(),
            "country_name": locale.country_name,
            "region": locale.region.value,
            "timezone": timezone,
            "timezone_offset": tz_offset,
            "primary_language": locale.primary_language,
            "languages": languages,
            "accept_language": accept_lang,
            "currency": locale.currency,
            "currency_symbol": locale.currency_symbol,
            "date_format": locale.date_format,
            "number_decimal": locale.number_decimal,
            "number_group": locale.number_group,
            "keyboard_layout": locale.keyboard_layout,
            "measurement": locale.measurement,
            "writing_direction": locale.writing_direction,
            "phone_prefix": locale.phone_prefix,
            "dns_servers": locale.dns_servers,
            "search_engines": locale.common_search_engines,
            "popular_sites": locale.popular_websites,
            "intl_override_scripts": intl_scripts,
            # Playwright-specific settings
            "playwright_locale": locale.primary_language,
            "playwright_timezone_id": timezone,
            "playwright_geolocation": None,  # Can be set by caller
        }

        return profile

    def build_playwright_context_args(
        self,
        country_code: str,
        timezone_variant: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build args suitable for playwright browser.new_context(**args).

        Returns dict with locale, timezone_id, extra_http_headers, etc.
        """
        profile = self.build_profile(country_code, timezone_variant)

        return {
            "locale": profile["primary_language"],
            "timezone_id": profile["timezone"],
            "extra_http_headers": {
                "Accept-Language": profile["accept_language"],
            },
        }

    def validate(
        self,
        country_code: str,
        **kwargs,
    ) -> ConsistencyReport:
        """Validate browser settings against expected geo profile."""
        self._validations_run += 1
        return GeoConsistencyValidator.validate(country_code, **kwargs)

    def select_random_country(
        self,
        region: Optional[Region] = None,
        exclude: Optional[List[str]] = None,
    ) -> str:
        """Select a random country, optionally filtered by region."""
        exclude = exclude or []
        candidates = [
            code for code, locale in GEO_DATABASE.items()
            if code not in exclude and (region is None or locale.region == region)
        ]
        if not candidates:
            return "US"
        return random.choice(candidates)

    def match_country_to_proxy(
        self, proxy_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Given a proxy's country code, build a matching geo profile.
        If proxy_country is unknown, randomly select one.
        """
        if proxy_country and proxy_country.upper() in GEO_DATABASE:
            return self.build_profile(proxy_country.upper())
        else:
            country = self.select_random_country()
            return self.build_profile(country)

    def _build_accept_language(
        self, locale: GeoLocale, randomize: float
    ) -> str:
        """Build Accept-Language with slight q-value randomization."""
        parts = []
        for i, lang in enumerate(locale.languages):
            if i == 0:
                parts.append(lang)
            else:
                base_q = max(0.1, 1.0 - (i * 0.1))
                noise = random.uniform(-randomize * 0.05, randomize * 0.05)
                q = max(0.1, min(0.99, base_q + noise))
                parts.append(f"{lang};q={q:.1f}")
        return ",".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "supported_countries": len(GEO_DATABASE),
            "profiles_generated": self._profiles_generated,
            "validations_run": self._validations_run,
        }


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

geo_engine: GeoConsistencyEngine = GeoConsistencyEngine()


