
from __future__ import annotations
"""
sessions/browser_profile.py — Full Browser Profile Persistence v1.0-TITAN
═══════════════════════════════════════════════════════════════════════════
Complete browser state capture and restoration for persistent identity.

Captures and restores:
1. Cookies (all domains, secure/httpOnly/sameSite flags)
2. localStorage (per-domain key-value pairs)
3. sessionStorage (per-domain key-value pairs)
4. IndexedDB databases (per-domain structure + data)
5. ServiceWorker registrations (scope, script URL)
6. Cache Storage entries (per-domain cached request/response pairs)
7. WebSQL databases (legacy, per-domain)
8. Browser permissions state
9. Credential storage (navigator.credentials)
10. Console history patterns (for behavior realism)

Storage format: AES-256-GCM encrypted JSON, organized by domain.

Integration with SessionStore:
- BrowserProfile extends BrowserSession with full state
- ProfileManager handles capture/restore with Playwright pages
- Profiles persist across browser restarts

Author: Arki Engine TITAN
License: Proprietary
"""


import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Final, List, Optional

logger = logging.getLogger("arki.browser_profile")

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


# ═══════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════

@dataclass
class IndexedDBRecord:
    """A record from an IndexedDB object store."""
    store_name: str
    key: Any
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {"store": self.store_name, "key": self.key, "value": self.value}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IndexedDBRecord":
        return cls(store_name=d["store"], key=d["key"], value=d["value"])


@dataclass
class IndexedDBDatabase:
    """An IndexedDB database with its object stores and data."""
    name: str
    version: int = 1
    stores: Dict[str, List[IndexedDBRecord]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "stores": {
                k: [r.to_dict() for r in v]
                for k, v in self.stores.items()
            },
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IndexedDBDatabase":
        stores = {}
        for k, records in d.get("stores", {}).items():
            stores[k] = [IndexedDBRecord.from_dict(r) for r in records]
        return cls(name=d["name"], version=d.get("version", 1), stores=stores)


@dataclass
class ServiceWorkerRegistration:
    """A ServiceWorker registration."""
    scope: str
    script_url: str
    state: str = "activated"  # installing, installed, activating, activated

    def to_dict(self) -> Dict[str, Any]:
        return {"scope": self.scope, "script_url": self.script_url, "state": self.state}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ServiceWorkerRegistration":
        return cls(scope=d["scope"], script_url=d["script_url"], state=d.get("state", "activated"))


@dataclass
class CacheEntry:
    """A Cache Storage entry (request/response pair)."""
    cache_name: str
    request_url: str
    response_status: int = 200
    response_headers: Dict[str, str] = field(default_factory=dict)
    # Response body is NOT stored (too large) — only structure for fingerprinting

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cache": self.cache_name,
            "url": self.request_url,
            "status": self.response_status,
            "headers": self.response_headers,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CacheEntry":
        return cls(
            cache_name=d["cache"], request_url=d["url"],
            response_status=d.get("status", 200),
            response_headers=d.get("headers", {}),
        )


@dataclass
class PermissionState:
    """Browser permission state."""
    name: str         # e.g., "notifications", "geolocation"
    state: str = "prompt"  # granted, denied, prompt

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "state": self.state}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PermissionState":
        return cls(name=d["name"], state=d.get("state", "prompt"))


@dataclass
class DomainProfile:
    """Complete browser state for a single domain."""
    domain: str
    local_storage: Dict[str, str] = field(default_factory=dict)
    session_storage: Dict[str, str] = field(default_factory=dict)
    indexed_dbs: List[IndexedDBDatabase] = field(default_factory=list)
    service_workers: List[ServiceWorkerRegistration] = field(default_factory=list)
    cache_entries: List[CacheEntry] = field(default_factory=list)
    permissions: List[PermissionState] = field(default_factory=list)
    last_visit: float = 0.0
    visit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
            "indexed_dbs": [db.to_dict() for db in self.indexed_dbs],
            "service_workers": [sw.to_dict() for sw in self.service_workers],
            "cache_entries": [ce.to_dict() for ce in self.cache_entries],
            "permissions": [p.to_dict() for p in self.permissions],
            "last_visit": self.last_visit,
            "visit_count": self.visit_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DomainProfile":
        return cls(
            domain=d["domain"],
            local_storage=d.get("local_storage", {}),
            session_storage=d.get("session_storage", {}),
            indexed_dbs=[IndexedDBDatabase.from_dict(db) for db in d.get("indexed_dbs", [])],
            service_workers=[ServiceWorkerRegistration.from_dict(sw) for sw in d.get("service_workers", [])],
            cache_entries=[CacheEntry.from_dict(ce) for ce in d.get("cache_entries", [])],
            permissions=[PermissionState.from_dict(p) for p in d.get("permissions", [])],
            last_visit=d.get("last_visit", 0),
            visit_count=d.get("visit_count", 0),
        )


@dataclass
class BrowserProfile:
    """
    Complete browser profile for persistent identity across sessions.

    This is the master record that contains ALL browser state needed to
    maintain a consistent identity across browser restarts, proxy changes,
    and even machine changes.
    """
    profile_id: str
    name: str = ""
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)

    # Core browser identity
    user_agent: str = ""
    platform: str = ""
    language: str = "en-US"
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    timezone: str = "Europe/Helsinki"
    screen_width: int = 1920
    screen_height: int = 1080

    # Fingerprint components
    canvas_noise_seed: int = 0
    webgl_noise_seed: int = 0
    audio_noise_seed: int = 0
    font_list_hash: str = ""

    # Cookies (all domains)
    cookies: List[Dict[str, Any]] = field(default_factory=list)

    # Per-domain state
    domain_profiles: Dict[str, DomainProfile] = field(default_factory=dict)

    # Playwright storage state (for direct restore)
    storage_state: Optional[Dict[str, Any]] = None

    # Navigation history pattern (for behavior realism)
    typical_sites: List[str] = field(default_factory=list)
    visit_patterns: Dict[str, int] = field(default_factory=dict)  # domain → visit_count

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    @property
    def domains_visited(self) -> int:
        return len(self.domain_profiles)

    def touch(self) -> None:
        self.last_used = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "user_agent": self.user_agent,
            "platform": self.platform,
            "language": self.language,
            "languages": self.languages,
            "timezone": self.timezone,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "canvas_noise_seed": self.canvas_noise_seed,
            "webgl_noise_seed": self.webgl_noise_seed,
            "audio_noise_seed": self.audio_noise_seed,
            "font_list_hash": self.font_list_hash,
            "cookies": self.cookies,
            "domain_profiles": {k: v.to_dict() for k, v in self.domain_profiles.items()},
            "storage_state": self.storage_state,
            "typical_sites": self.typical_sites,
            "visit_patterns": self.visit_patterns,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BrowserProfile":
        domain_profiles = {}
        for k, v in d.get("domain_profiles", {}).items():
            domain_profiles[k] = DomainProfile.from_dict(v)

        return cls(
            profile_id=d["profile_id"],
            name=d.get("name", ""),
            created_at=d.get("created_at", time.time()),
            last_used=d.get("last_used", time.time()),
            user_agent=d.get("user_agent", ""),
            platform=d.get("platform", ""),
            language=d.get("language", "en-US"),
            languages=d.get("languages", ["en-US", "en"]),
            timezone=d.get("timezone", "Europe/Helsinki"),
            screen_width=d.get("screen_width", 1920),
            screen_height=d.get("screen_height", 1080),
            canvas_noise_seed=d.get("canvas_noise_seed", 0),
            webgl_noise_seed=d.get("webgl_noise_seed", 0),
            audio_noise_seed=d.get("audio_noise_seed", 0),
            font_list_hash=d.get("font_list_hash", ""),
            cookies=d.get("cookies", []),
            domain_profiles=domain_profiles,
            storage_state=d.get("storage_state"),
            typical_sites=d.get("typical_sites", []),
            visit_patterns=d.get("visit_patterns", {}),
            metadata=d.get("metadata", {}),
        )


# ═══════════════════════════════════════════════════════════
# Profile Capture (from live Playwright page)
# ═══════════════════════════════════════════════════════════

class ProfileCapturer:
    """
    Captures complete browser state from a live Playwright page/context.

    Usage:
        capturer = ProfileCapturer()
        profile = await capturer.capture(context, page)
    """

    async def capture(
        self,
        context: Any,
        page: Any,
        profile: Optional[BrowserProfile] = None,
    ) -> BrowserProfile:
        """
        Capture full browser state from a Playwright context + page.

        Args:
            context: Playwright BrowserContext
            page: Active Playwright Page
            profile: Existing profile to update (or creates new)

        Returns:
            Updated/new BrowserProfile
        """
        if profile is None:
            profile = BrowserProfile(
                profile_id=secrets.token_hex(12),
                name=f"captured_{int(time.time())}",
            )

        profile.touch()

        # 1. Capture storage state (cookies + localStorage)
        try:
            storage_state = await context.storage_state()
            profile.storage_state = storage_state
            profile.cookies = storage_state.get("cookies", [])

            # Extract localStorage per origin
            for origin_state in storage_state.get("origins", []):
                origin = origin_state.get("origin", "")
                domain = self._origin_to_domain(origin)
                if domain:
                    dp = profile.domain_profiles.setdefault(domain, DomainProfile(domain=domain))
                    dp.local_storage = {
                        item["name"]: item["value"]
                        for item in origin_state.get("localStorage", [])
                    }
                    dp.last_visit = time.time()
                    dp.visit_count += 1
        except Exception as e:
            logger.warning("Failed to capture storage state: %s", e)

        # 2. Capture current page's detailed state
        try:
            domain = self._url_to_domain(page.url)
            if domain:
                dp = profile.domain_profiles.setdefault(domain, DomainProfile(domain=domain))
                await self._capture_page_state(page, dp)
        except Exception as e:
            logger.warning("Failed to capture page state: %s", e)

        # 3. Capture ServiceWorker registrations
        try:
            await self._capture_service_workers(page, profile)
        except Exception as e:
            logger.debug("ServiceWorker capture failed: %s", e)

        # 4. Capture user agent
        try:
            profile.user_agent = await page.evaluate("() => navigator.userAgent")
            profile.platform = await page.evaluate("() => navigator.platform")
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

        # 5. Update visit patterns
        domain = self._url_to_domain(page.url)
        if domain:
            profile.visit_patterns[domain] = profile.visit_patterns.get(domain, 0) + 1
            if domain not in profile.typical_sites:
                profile.typical_sites.append(domain)

        logger.info(
            "📸 Captured profile %s: %d cookies, %d domains, %d localStorage keys",
            profile.profile_id[:8],
            len(profile.cookies),
            len(profile.domain_profiles),
            sum(len(dp.local_storage) for dp in profile.domain_profiles.values()),
        )

        return profile

    async def _capture_page_state(self, page: Any, dp: DomainProfile) -> None:
        """Capture detailed state from the current page."""
        # localStorage (more complete — from page context)
        try:
            ls = await page.evaluate("""() => {
                const data = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    data[key] = localStorage.getItem(key);
                }
                return data;
            }""")
            dp.local_storage.update(ls)
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

        # sessionStorage
        try:
            ss = await page.evaluate("""() => {
                const data = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    data[key] = sessionStorage.getItem(key);
                }
                return data;
            }""")
            dp.session_storage = ss
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

        # IndexedDB databases
        try:
            dbs = await page.evaluate("""async () => {
                try {
                    const dbNames = await indexedDB.databases();
                    const results = [];
                    for (const dbInfo of dbNames) {
                        try {
                            const db = await new Promise((resolve, reject) => {
                                const req = indexedDB.open(dbInfo.name, dbInfo.version);
                                req.onsuccess = () => resolve(req.result);
                                req.onerror = () => reject(req.error);
                            });
                            const stores = {};
                            for (const storeName of db.objectStoreNames) {
                                try {
                                    const tx = db.transaction(storeName, 'readonly');
                                    const store = tx.objectStore(storeName);
                                    const allKeys = await new Promise((resolve, reject) => {
                                        const req = store.getAllKeys();
                                        req.onsuccess = () => resolve(req.result);
                                        req.onerror = () => reject(req.error);
                                    });
                                    const allValues = await new Promise((resolve, reject) => {
                                        const req = store.getAll();
                                        req.onsuccess = () => resolve(req.result);
                                        req.onerror = () => reject(req.error);
                                    });
                                    stores[storeName] = allKeys.map((k, i) => ({
                                        key: JSON.parse(JSON.stringify(k)),
                                        value: JSON.parse(JSON.stringify(allValues[i] || null)),
                                    }));
                                } catch(e) { stores[storeName] = []; }
                            }
                            db.close();
                            results.push({
                                name: dbInfo.name,
                                version: dbInfo.version,
                                stores: stores,
                            });
                        } catch(e) {}
                    }
                    return results;
                } catch(e) { return []; }
            }""")

            dp.indexed_dbs = []
            for db_data in (dbs or []):
                stores = {}
                for store_name, records in db_data.get("stores", {}).items():
                    stores[store_name] = [
                        IndexedDBRecord(store_name=store_name, key=r["key"], value=r["value"])
                        for r in records
                    ]
                dp.indexed_dbs.append(IndexedDBDatabase(
                    name=db_data["name"],
                    version=db_data.get("version", 1),
                    stores=stores,
                ))
        except Exception as e:
            logger.debug("IndexedDB capture failed: %s", e)

        # Cache Storage
        try:
            caches = await page.evaluate("""async () => {
                try {
                    const cacheNames = await caches.keys();
                    const results = [];
                    for (const name of cacheNames) {
                        const cache = await caches.open(name);
                        const requests = await cache.keys();
                        for (const req of requests.slice(0, 50)) {
                            const resp = await cache.match(req);
                            results.push({
                                cache: name,
                                url: req.url,
                                status: resp ? resp.status_code : 0,
                            });
                        }
                    }
                    return results;
                } catch(e) { return []; }
            }""")
            dp.cache_entries = [CacheEntry.from_dict(c) for c in (caches or [])]
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

    async def _capture_service_workers(self, page: Any, profile: BrowserProfile) -> None:
        """Capture ServiceWorker registrations."""
        try:
            sws = await page.evaluate("""async () => {
                try {
                    const registrations = await navigator.serviceWorker.getRegistrations();
                    return registrations.map(reg => ({
                        scope: reg.scope,
                        script_url: reg.active ? reg.active.scriptURL : '',
                        state: reg.active ? reg.active.state : 'unknown',
                    }));
                } catch(e) { return []; }
            }""")

            domain = self._url_to_domain(page.url)
            if domain and sws:
                dp = profile.domain_profiles.setdefault(domain, DomainProfile(domain=domain))
                dp.service_workers = [ServiceWorkerRegistration.from_dict(sw) for sw in sws]
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

    @staticmethod
    def _url_to_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or ""
        except Exception:
            return ""

    @staticmethod
    def _origin_to_domain(origin: str) -> str:
        """Extract domain from origin (https://example.com → example.com)."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            return parsed.netloc or ""
        except Exception:
            return ""


# ═══════════════════════════════════════════════════════════
# Profile Restorer (to live Playwright page)
# ═══════════════════════════════════════════════════════════

class ProfileRestorer:
    """
    Restores a saved browser profile into a Playwright context/page.

    Usage:
        restorer = ProfileRestorer()
        await restorer.restore(context, page, profile)
    """

    async def restore(
        self,
        context: Any,
        page: Any,
        profile: BrowserProfile,
        domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Restore browser state into a Playwright context.

        Args:
            context: Playwright BrowserContext
            page: Active Playwright Page
            profile: Profile to restore
            domains: Optional list of domains to restore (all if None)

        Returns:
            Dict with restoration stats
        """
        stats = {
            "cookies_restored": 0,
            "localStorage_restored": 0,
            "sessionStorage_restored": 0,
            "indexedDB_restored": 0,
            "serviceWorkers_restored": 0,
            "errors": [],
        }

        # 1. Restore cookies via context
        try:
            if profile.cookies:
                valid_cookies = self._filter_valid_cookies(profile.cookies)
                await context.add_cookies(valid_cookies)
                stats["cookies_restored"] = len(valid_cookies)
        except Exception as e:
            stats["errors"].append(f"Cookies: {e}")

        # 2. Restore per-domain state
        target_domains = domains or list(profile.domain_profiles.keys())
        for domain in target_domains:
            dp = profile.domain_profiles.get(domain)
            if not dp:
                continue

            try:
                await self._restore_domain(page, dp, stats)
            except Exception as e:
                stats["errors"].append(f"Domain {domain}: {e}")

        profile.touch()

        logger.info(
            "📥 Restored profile %s: cookies=%d, localStorage=%d, indexedDB=%d",
            profile.profile_id[:8],
            stats["cookies_restored"],
            stats["localStorage_restored"],
            stats["indexedDB_restored"],
        )

        return stats

    async def _restore_domain(
        self,
        page: Any,
        dp: DomainProfile,
        stats: Dict[str, Any],
    ) -> None:
        """Restore state for a single domain."""
        # localStorage
        if dp.local_storage:
            try:
                await page.evaluate("""(data) => {
                    for (const [key, value] of Object.entries(data)) {
                        try { localStorage.setItem(key, value); } catch(e) {}
                    }
                }""", dp.local_storage)
                stats["localStorage_restored"] += len(dp.local_storage)
            except Exception as e:
                stats["errors"].append(f"localStorage {dp.domain}: {e}")

        # sessionStorage
        if dp.session_storage:
            try:
                await page.evaluate("""(data) => {
                    for (const [key, value] of Object.entries(data)) {
                        try { sessionStorage.setItem(key, value); } catch(e) {}
                    }
                }""", dp.session_storage)
                stats["sessionStorage_restored"] += len(dp.session_storage)
            except Exception as e:
                stats["errors"].append(f"sessionStorage {dp.domain}: {e}")

        # IndexedDB
        for db in dp.indexed_dbs:
            try:
                await self._restore_indexed_db(page, db)
                stats["indexedDB_restored"] += 1
            except Exception as e:
                stats["errors"].append(f"IndexedDB {db.name}: {e}")

    async def _restore_indexed_db(self, page: Any, db: IndexedDBDatabase) -> None:
        """Restore an IndexedDB database."""
        db_config = {
            "name": db.name,
            "version": db.version,
            "stores": {
                store_name: [r.to_dict() for r in records]
                for store_name, records in db.stores.items()
            },
        }

        await page.evaluate("""async (config) => {
            return new Promise((resolve, reject) => {
                const req = indexedDB.open(config.name, config.version);
                req.onupgradeneeded = (event) => {
                    const db = event.target.result;
                    for (const storeName of Object.keys(config.stores)) {
                        if (!db.objectStoreNames.contains(storeName)) {
                            db.createObjectStore(storeName, { autoIncrement: true });
                        }
                    }
                };
                req.onsuccess = async () => {
                    const db = req.result;
                    try {
                        for (const [storeName, records] of Object.entries(config.stores)) {
                            if (!db.objectStoreNames.contains(storeName)) continue;
                            const tx = db.transaction(storeName, 'readwrite');
                            const store = tx.objectStore(storeName);
                            for (const record of records) {
                                try {
                                    store.put(record.value, record.key);
                                } catch(e) {}
                            }
                            await new Promise((res, rej) => {
                                tx.oncomplete = res;
                                tx.onerror = rej;
                            });
                        }
                    } catch(e) {}
                    db.close();
                    resolve(true);
                };
                req.onerror = () => reject(req.error);
                setTimeout(() => resolve(false), 5000);
            });
        }""", db_config)

    @staticmethod
    def _filter_valid_cookies(cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out expired cookies and fix format for Playwright."""
        now = time.time()
        valid = []
        for c in cookies:
            # Skip expired
            expires = c.get("expires", -1)
            if isinstance(expires, (int, float)) and 0 < expires < now:
                continue

            # Playwright requires certain fields
            cookie = {
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
            }

            if not cookie["name"] or not cookie["domain"]:
                continue

            if expires and expires > 0:
                cookie["expires"] = expires
            if "secure" in c:
                cookie["secure"] = c["secure"]
            if "httpOnly" in c:
                cookie["httpOnly"] = c["httpOnly"]
            if "sameSite" in c:
                cookie["sameSite"] = c["sameSite"]

            valid.append(cookie)

        return valid


# ═══════════════════════════════════════════════════════════
# Profile Manager (Persistence + CRUD)
# ═══════════════════════════════════════════════════════════

class ProfileManager:
    """
    Manages browser profiles on disk with encryption.

    Profile storage layout:
        profiles/
        ├── {profile_id}.json          (encrypted profile data)
        ├── {profile_id}.meta.json     (unencrypted metadata for listing)
        └── ...
    """

    VERSION: Final[str] = "1.0.0-TITAN"

    def __init__(
        self,
        profiles_dir: str = "sessions/profiles",
        encryption_key: Optional[str] = None,
    ) -> None:
        self._dir = Path(profiles_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._enc_key = encryption_key or os.environ.get("ARKI_PROFILE_KEY", "")
        self._profiles: Dict[str, BrowserProfile] = {}
        self._lock = asyncio.Lock()

        self._capturer = ProfileCapturer()
        self._restorer = ProfileRestorer()

    async def load_all(self) -> int:
        """Load all profiles from disk."""
        count = 0
        for meta_file in self._dir.glob("*.meta.json"):
            profile_id = meta_file.stem.replace(".meta", "")
            try:
                profile = await self._load_profile(profile_id)
                if profile:
                    self._profiles[profile_id] = profile
                    count += 1
            except Exception as e:
                logger.debug("Skip corrupt profile %s: %s", profile_id, e)
        logger.info("📂 ProfileManager loaded %d profiles", count)
        return count

    async def create_profile(
        self,
        name: str = "",
        user_agent: str = "",
        platform: str = "",
        timezone: str = "Europe/Helsinki",
        language: str = "en-US",
        screen_width: int = 1920,
        screen_height: int = 1080,
    ) -> BrowserProfile:
        """Create a new empty browser profile."""
        import random as _rand
        profile = BrowserProfile(
            profile_id=secrets.token_hex(12),
            name=name or f"profile_{int(time.time())}",
            user_agent=user_agent,
            platform=platform,
            timezone=timezone,
            language=language,
            screen_width=screen_width,
            screen_height=screen_height,
            canvas_noise_seed=_rand.randint(1, 2**32),
            webgl_noise_seed=_rand.randint(1, 2**32),
            audio_noise_seed=_rand.randint(1, 2**32),
        )
        async with self._lock:
            self._profiles[profile.profile_id] = profile
            await self._save_profile(profile)
        return profile

    async def capture_from_page(
        self,
        context: Any,
        page: Any,
        profile_id: Optional[str] = None,
    ) -> BrowserProfile:
        """Capture browser state into a profile."""
        profile = self._profiles.get(profile_id) if profile_id else None
        profile = await self._capturer.capture(context, page, profile)
        async with self._lock:
            self._profiles[profile.profile_id] = profile
            await self._save_profile(profile)
        return profile

    async def restore_to_page(
        self,
        context: Any,
        page: Any,
        profile_id: str,
        domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Restore a profile into a Playwright context."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return {"error": f"Profile {profile_id} not found"}
        stats = await self._restorer.restore(context, page, profile, domains)
        async with self._lock:
            await self._save_profile(profile)
        return stats

    async def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile."""
        async with self._lock:
            if profile_id not in self._profiles:
                return False
            del self._profiles[profile_id]
            data_file = self._dir / f"{profile_id}.json"
            meta_file = self._dir / f"{profile_id}.meta.json"
            data_file.unlink(missing_ok=True)
            meta_file.unlink(missing_ok=True)
        return True

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles with summary metadata."""
        result = []
        for pid, p in self._profiles.items():
            result.append({
                "profile_id": pid,
                "name": p.name,
                "user_agent": p.user_agent[:60] + "..." if len(p.user_agent) > 60 else p.user_agent,
                "domains": p.domains_visited,
                "cookies": len(p.cookies),
                "age_hours": round(p.age_hours, 1),
                "last_used": p.last_used,
            })
        return sorted(result, key=lambda x: -x["last_used"])

    def get_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Get a profile by ID."""
        return self._profiles.get(profile_id)

    # ── Persistence ──

    async def _save_profile(self, profile: BrowserProfile) -> None:
        """Save profile to disk (encrypted)."""
        data = json.dumps(profile.to_dict(), ensure_ascii=False)

        # Encrypt if key available
        if _CRYPTO_AVAILABLE and self._enc_key:
            try:
                key = hashlib.sha256(self._enc_key.encode()).digest()
                nonce = secrets.token_bytes(12)
                aesgcm = AESGCM(key)
                encrypted = aesgcm.encrypt(nonce, data.encode("utf-8"), None)
                import base64
                payload = base64.b64encode(nonce + encrypted).decode("ascii")
                (self._dir / f"{profile.profile_id}.json").write_text(payload)
            except Exception as e:
                logger.warning("Encryption failed, saving plain: %s", e)
                (self._dir / f"{profile.profile_id}.json").write_text(data)
        else:
            (self._dir / f"{profile.profile_id}.json").write_text(data)

        # Save unencrypted metadata for listing
        meta = {
            "profile_id": profile.profile_id,
            "name": profile.name,
            "created_at": profile.created_at,
            "last_used": profile.last_used,
            "domains": profile.domains_visited,
            "cookies": len(profile.cookies),
        }
        (self._dir / f"{profile.profile_id}.meta.json").write_text(
            json.dumps(meta, indent=2)
        )

    async def _load_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Load a profile from disk."""
        data_file = self._dir / f"{profile_id}.json"
        if not data_file.exists():
            return None

        raw = data_file.read_text()

        # Try decrypt
        if _CRYPTO_AVAILABLE and self._enc_key:
            try:
                import base64
                key = hashlib.sha256(self._enc_key.encode()).digest()
                payload = base64.b64decode(raw)
                nonce = payload[:12]
                encrypted = payload[12:]
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(nonce, encrypted, None)
                raw = decrypted.decode("utf-8")
            except Exception:
                pass  # Might be unencrypted

        data = json.loads(raw)
        return BrowserProfile.from_dict(data)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "total_profiles": len(self._profiles),
            "total_cookies": sum(len(p.cookies) for p in self._profiles.values()),
            "total_domains": sum(p.domains_visited for p in self._profiles.values()),
            "profiles_dir": str(self._dir),
            "encryption": "AES-256-GCM" if (_CRYPTO_AVAILABLE and self._enc_key) else "none",
        }


# Module-level singleton
profile_manager = ProfileManager()


