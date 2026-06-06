
"""Tests for sessions/browser_profile.py — Full Browser Profile Persistence."""

import pytest
import time
import os
import tempfile
import shutil

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sessions.browser_profile import (
    IndexedDBRecord, IndexedDBDatabase, ServiceWorkerRegistration,
    CacheEntry, PermissionState, DomainProfile, BrowserProfile,
    ProfileCapturer, ProfileRestorer, ProfileManager,
    profile_manager,
)


# ═══════════════════════════════════════════════════════════
# IndexedDB Models Tests
# ═══════════════════════════════════════════════════════════

class TestIndexedDBRecord:
    def test_create(self):
        r = IndexedDBRecord(store_name="users", key="1", value={"name": "test"})
        assert r.store_name == "users"

    def test_to_dict(self):
        r = IndexedDBRecord(store_name="users", key=1, value="hello")
        d = r.to_dict()
        assert d["store"] == "users"
        assert d["key"] == 1
        assert d["value"] == "hello"

    def test_from_dict(self):
        d = {"store": "cache", "key": "k1", "value": [1, 2, 3]}
        r = IndexedDBRecord.from_dict(d)
        assert r.store_name == "cache"
        assert r.value == [1, 2, 3]


class TestIndexedDBDatabase:
    def test_create_empty(self):
        db = IndexedDBDatabase(name="test_db")
        assert db.name == "test_db"
        assert db.version == 1

    def test_to_dict(self):
        db = IndexedDBDatabase(
            name="mydb", version=3,
            stores={"users": [IndexedDBRecord("users", "1", {"name": "alice"})]}
        )
        d = db.to_dict()
        assert d["name"] == "mydb"
        assert d["version"] == 3
        assert len(d["stores"]["users"]) == 1

    def test_from_dict(self):
        d = {
            "name": "testdb", "version": 2,
            "stores": {
                "items": [{"store": "items", "key": 1, "value": "test"}]
            }
        }
        db = IndexedDBDatabase.from_dict(d)
        assert db.name == "testdb"
        assert db.version == 2
        assert len(db.stores["items"]) == 1

    def test_roundtrip(self):
        db = IndexedDBDatabase(
            name="rt_db", version=5,
            stores={"s1": [IndexedDBRecord("s1", "k", "v")]}
        )
        d = db.to_dict()
        db2 = IndexedDBDatabase.from_dict(d)
        assert db2.name == db.name
        assert db2.version == db.version


# ═══════════════════════════════════════════════════════════
# ServiceWorker Tests
# ═══════════════════════════════════════════════════════════

class TestServiceWorkerRegistration:
    def test_create(self):
        sw = ServiceWorkerRegistration(scope="/app/", script_url="/sw.js")
        assert sw.state == "activated"

    def test_to_dict(self):
        sw = ServiceWorkerRegistration("/", "/sw.js", "installing")
        d = sw.to_dict()
        assert d["scope"] == "/"
        assert d["state"] == "installing"

    def test_from_dict(self):
        d = {"scope": "/app/", "script_url": "/sw.js", "state": "activated"}
        sw = ServiceWorkerRegistration.from_dict(d)
        assert sw.scope == "/app/"


# ═══════════════════════════════════════════════════════════
# CacheEntry Tests
# ═══════════════════════════════════════════════════════════

class TestCacheEntry:
    def test_create(self):
        ce = CacheEntry(cache_name="v1", request_url="https://example.com/api")
        assert ce.response_status == 200

    def test_to_dict(self):
        ce = CacheEntry("v1", "https://x.com", 304, {"etag": "abc"})
        d = ce.to_dict()
        assert d["cache"] == "v1"
        assert d["status"] == 304

    def test_from_dict(self):
        d = {"cache": "static", "url": "https://x.com/img.png", "status": 200}
        ce = CacheEntry.from_dict(d)
        assert ce.cache_name == "static"
        assert ce.request_url == "https://x.com/img.png"


# ═══════════════════════════════════════════════════════════
# PermissionState Tests
# ═══════════════════════════════════════════════════════════

class TestPermissionState:
    def test_default_prompt(self):
        p = PermissionState(name="notifications")
        assert p.state == "prompt"

    def test_granted(self):
        p = PermissionState(name="geolocation", state="granted")
        assert p.state == "granted"

    def test_roundtrip(self):
        p = PermissionState("camera", "denied")
        d = p.to_dict()
        p2 = PermissionState.from_dict(d)
        assert p2.name == "camera"
        assert p2.state == "denied"


# ═══════════════════════════════════════════════════════════
# DomainProfile Tests
# ═══════════════════════════════════════════════════════════

class TestDomainProfile:
    def test_create_empty(self):
        dp = DomainProfile(domain="example.com")
        assert dp.domain == "example.com"
        assert len(dp.local_storage) == 0

    def test_with_data(self):
        dp = DomainProfile(
            domain="google.com",
            local_storage={"theme": "dark", "lang": "en"},
            session_storage={"token": "abc"},
            indexed_dbs=[IndexedDBDatabase(name="cache_db")],
            service_workers=[ServiceWorkerRegistration("/", "/sw.js")],
            permissions=[PermissionState("notifications", "granted")],
        )
        assert len(dp.local_storage) == 2
        assert len(dp.indexed_dbs) == 1
        assert dp.permissions[0].state == "granted"

    def test_to_dict(self):
        dp = DomainProfile(domain="x.com", local_storage={"a": "b"})
        d = dp.to_dict()
        assert d["domain"] == "x.com"
        assert d["local_storage"]["a"] == "b"

    def test_roundtrip(self):
        dp = DomainProfile(
            domain="test.com",
            local_storage={"k": "v"},
            indexed_dbs=[IndexedDBDatabase("db1", stores={"s": [IndexedDBRecord("s", 1, 2)]})],
            cache_entries=[CacheEntry("c1", "https://test.com/api")],
        )
        d = dp.to_dict()
        dp2 = DomainProfile.from_dict(d)
        assert dp2.domain == "test.com"
        assert len(dp2.indexed_dbs) == 1
        assert dp2.indexed_dbs[0].stores["s"][0].value == 2


# ═══════════════════════════════════════════════════════════
# BrowserProfile Tests
# ═══════════════════════════════════════════════════════════

class TestBrowserProfile:
    def test_create_default(self):
        bp = BrowserProfile(profile_id="abc123")
        assert bp.profile_id == "abc123"
        assert bp.timezone == "Europe/Helsinki"
        assert bp.language == "en-US"

    def test_age_hours(self):
        bp = BrowserProfile(profile_id="x", created_at=time.time() - 7200)
        assert abs(bp.age_hours - 2.0) < 0.1

    def test_domains_visited(self):
        bp = BrowserProfile(
            profile_id="x",
            domain_profiles={
                "a.com": DomainProfile(domain="a.com"),
                "b.com": DomainProfile(domain="b.com"),
            }
        )
        assert bp.domains_visited == 2

    def test_touch(self):
        bp = BrowserProfile(profile_id="x", last_used=0)
        bp.touch()
        assert bp.last_used > 0

    def test_to_dict(self):
        bp = BrowserProfile(
            profile_id="test123",
            name="test_profile",
            user_agent="Mozilla/5.0",
            cookies=[{"name": "s", "value": "v", "domain": ".test.com"}],
            canvas_noise_seed=42,
        )
        d = bp.to_dict()
        assert d["profile_id"] == "test123"
        assert d["canvas_noise_seed"] == 42
        assert len(d["cookies"]) == 1

    def test_roundtrip(self):
        bp = BrowserProfile(
            profile_id="rt_test",
            name="roundtrip",
            user_agent="Test/1.0",
            platform="Win32",
            languages=["en-US", "fi"],
            screen_width=2560,
            domain_profiles={
                "x.com": DomainProfile(
                    domain="x.com",
                    local_storage={"auth": "token123"},
                )
            },
            visit_patterns={"x.com": 5},
        )
        d = bp.to_dict()
        bp2 = BrowserProfile.from_dict(d)
        assert bp2.profile_id == "rt_test"
        assert bp2.screen_width == 2560
        assert bp2.domain_profiles["x.com"].local_storage["auth"] == "token123"
        assert bp2.visit_patterns["x.com"] == 5


# ═══════════════════════════════════════════════════════════
# ProfileCapturer Tests (unit — no Playwright)
# ═══════════════════════════════════════════════════════════

class TestProfileCapturer:
    def test_url_to_domain(self):
        assert ProfileCapturer._url_to_domain("https://example.com/path") == "example.com"

    def test_url_to_domain_with_port(self):
        assert ProfileCapturer._url_to_domain("https://example.com:8080/path") == "example.com:8080"

    def test_url_to_domain_empty(self):
        assert ProfileCapturer._url_to_domain("") == ""

    def test_origin_to_domain(self):
        assert ProfileCapturer._origin_to_domain("https://example.com") == "example.com"


# ═══════════════════════════════════════════════════════════
# ProfileRestorer Tests (unit — no Playwright)
# ═══════════════════════════════════════════════════════════

class TestProfileRestorer:
    def test_filter_valid_cookies_removes_expired(self):
        cookies = [
            {"name": "active", "value": "v", "domain": ".test.com", "expires": time.time() + 3600},
            {"name": "expired", "value": "v", "domain": ".test.com", "expires": time.time() - 100},
        ]
        valid = ProfileRestorer._filter_valid_cookies(cookies)
        assert len(valid) == 1
        assert valid[0]["name"] == "active"

    def test_filter_valid_cookies_keeps_session(self):
        cookies = [
            {"name": "session", "value": "v", "domain": ".test.com", "expires": -1},
        ]
        valid = ProfileRestorer._filter_valid_cookies(cookies)
        assert len(valid) == 1

    def test_filter_valid_cookies_skips_no_domain(self):
        cookies = [
            {"name": "bad", "value": "v"},
        ]
        valid = ProfileRestorer._filter_valid_cookies(cookies)
        assert len(valid) == 0


# ═══════════════════════════════════════════════════════════
# ProfileManager Tests
# ═══════════════════════════════════════════════════════════

class TestProfileManager:
    @pytest.fixture
    def tmp_dir(self):
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_create_profile(self, tmp_dir):
        pm = ProfileManager(profiles_dir=tmp_dir)
        p = await pm.create_profile(name="test_p", user_agent="UA/1.0")
        assert p.name == "test_p"
        assert p.user_agent == "UA/1.0"
        assert p.canvas_noise_seed > 0

    @pytest.mark.asyncio
    async def test_list_profiles(self, tmp_dir):
        pm = ProfileManager(profiles_dir=tmp_dir)
        await pm.create_profile(name="p1")
        await pm.create_profile(name="p2")
        lst = pm.list_profiles()
        assert len(lst) == 2

    @pytest.mark.asyncio
    async def test_get_profile(self, tmp_dir):
        pm = ProfileManager(profiles_dir=tmp_dir)
        p = await pm.create_profile(name="findme")
        found = pm.get_profile(p.profile_id)
        assert found is not None
        assert found.name == "findme"

    @pytest.mark.asyncio
    async def test_delete_profile(self, tmp_dir):
        pm = ProfileManager(profiles_dir=tmp_dir)
        p = await pm.create_profile(name="delete_me")
        assert await pm.delete_profile(p.profile_id)
        assert pm.get_profile(p.profile_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, tmp_dir):
        pm = ProfileManager(profiles_dir=tmp_dir)
        assert not await pm.delete_profile("nonexistent")

    @pytest.mark.asyncio
    async def test_persist_and_reload(self, tmp_dir):
        pm = ProfileManager(profiles_dir=tmp_dir)
        p = await pm.create_profile(name="persist_test", user_agent="UA/2.0")
        pid = p.profile_id

        # Create new manager pointing to same dir
        pm2 = ProfileManager(profiles_dir=tmp_dir)
        count = await pm2.load_all()
        assert count == 1
        loaded = pm2.get_profile(pid)
        assert loaded is not None
        assert loaded.name == "persist_test"
        assert loaded.user_agent == "UA/2.0"

    @pytest.mark.asyncio
    async def test_stats(self, tmp_dir):
        pm = ProfileManager(profiles_dir=tmp_dir)
        await pm.create_profile(name="s1")
        stats = pm.get_stats()
        assert stats["total_profiles"] == 1
        assert stats["version"] == "1.0.0-TITAN"

    def test_singleton_exists(self):
        assert profile_manager is not None


