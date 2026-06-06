
from __future__ import annotations
from arki_project.exceptions import StorageError
"""
tg_bot/utils/data_store.py
──────────────────────────
Persistent data store with write-through cache.

Replaces ALL in-memory dicts that were lost on restart:
  _products, _queues, _sales, _brands, _shop_profiles, _catalogs

Usage:
    from arki_project.utils.data_store import store

    # Read (sync — from cache)
    brand = store.brands.get(chat_id, {})

    # Write (async — persists to DB)
    await store.set_brand(chat_id, {"name": "Arki", ...})
"""


import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy import select 

from arki_project.database.connection import get_session
# v17.3: crypto.py is deprecated — using it for legacy compat only
# TODO v18.0: migrate to utils/payload_encryption.py
from arki_project.utils.crypto import encrypt_dict, decrypt_dict  # noqa: F401
from arki_project.database.models import KVStore

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class DataStore:
    """
    Write-through cache backed by the ``kv_store`` DB table.

    All reads are from the in-memory cache (instant).
    All writes go to both cache AND DB (persistent).
    Call ``await store.load_all()`` once at startup.
    """

    STORE_NAMES = (
        "products", "queues", "sales", "brands",
        "shop_profiles", "catalogs",
    )

    def __init__(self) -> None:
        # Public caches — handlers access these directly.
        self.products: dict[int, dict[int, dict[str, Any]]] = {}
        self.queues: dict[int, list[dict[str, Any]]] = {}
        self.sales: dict[int, list[dict[str, Any]]] = {}
        self.brands: dict[int, dict[str, Any]] = {}
        self.shop_profiles: dict[int, dict[str, dict[str, Any]]] = {}
        self.catalogs: dict[int, list[dict[str, Any]]] = {}
        self._loaded = False

    # ── Startup ──

    async def load_all(self) -> None:
        """Load all stored data from DB into cache. Call once at startup."""
        if self._loaded:
            return

        async with get_session() as session:
            result = await session.execute(select(KVStore))
            rows = result.scalars().all()

        for row in rows:
            try:
                data = json.loads(row.data)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Corrupt KVStore row: %s/%s", row.store_name, row.chat_id)
                continue

            cache = getattr(self, row.store_name, None)
            if cache is None:
                continue

            # Convert string keys back to int where needed
            if row.store_name == "products":
                # products: chat_id → {pid(int) → product_dict}
                cache[row.chat_id] = {int(k): v for k, v in data.items()}
            else:
                cache[row.chat_id] = data

        self._loaded = True

        total = sum(len(getattr(self, n)) for n in self.STORE_NAMES)
        logger.info("DataStore loaded: %d entries across %d stores", total, len(self.STORE_NAMES))

    # ── Generic persist ──

    async def _persist(self, store_name: str, chat_id: int, data: Any) -> None:
        """Save one cache entry to DB using merge (works with any DB backend)."""
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        async with get_session() as session:
            result = await session.execute(
                select(KVStore).where(
                    KVStore.store_name == store_name,
                    KVStore.chat_id == chat_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.data = json_str
            else:
                session.add(KVStore(
                    store_name=store_name,
                    chat_id=chat_id,
                    data=json_str,
                ))
            await session.flush()

    # ── Products ──

    async def set_product(
        self, chat_id: int, pid: int, product: dict[str, Any],
    ) -> None:
        self.products.setdefault(chat_id, {})[pid] = product
        await self._persist("products", chat_id, self.products[chat_id])

    async def delete_product(self, chat_id: int, pid: int) -> bool:
        prods = self.products.get(chat_id, {})
        if pid in prods:
            del prods[pid]
            await self._persist("products", chat_id, prods)
            return True
        return False

    def get_products(self, chat_id: int) -> dict[int, dict[str, Any]]:
        return self.products.get(chat_id, {})


    # ── Queues ──

    async def add_to_queue(
        self, chat_id: int, item: dict[str, Any],
    ) -> None:
        self.queues.setdefault(chat_id, []).append(item)
        await self._persist("queues", chat_id, self.queues[chat_id])

    async def clear_queue(self, chat_id: int) -> None:
        self.queues[chat_id] = []
        await self._persist("queues", chat_id, [])

    async def set_queue(self, chat_id: int, queue: list[dict]) -> None:
        self.queues[chat_id] = queue
        await self._persist("queues", chat_id, queue)

    def get_queue(self, chat_id: int) -> list[dict[str, Any]]:
        return self.queues.get(chat_id, [])

    # ── Sales ──

    async def add_sale(
        self, chat_id: int, sale: dict[str, Any],
    ) -> None:
        sales_list = self.sales.setdefault(chat_id, [])
        sales_list.append(sale)
        # Keep only last 500 sales in memory/DB to prevent blob growth
        if len(sales_list) > 500:
            self.sales[chat_id] = sales_list[-500:]
        await self._persist("sales", chat_id, self.sales[chat_id])

    def get_sales(self, chat_id: int) -> list[dict[str, Any]]:
        return self.sales.get(chat_id, [])

    # ── Brands ──

    async def set_brand(self, chat_id: int, brand: dict[str, Any]) -> None:
        self.brands[chat_id] = brand
        await self._persist("brands", chat_id, brand)

    def get_brand(self, chat_id: int) -> dict[str, Any]:
        return self.brands.get(chat_id, {})

    # ── Shop Profiles ──

    async def set_shop_profile(
        self, chat_id: int, platform_key: str, profile: dict[str, Any],
    ) -> None:
        # Encrypt sensitive credential fields before storing
        encrypted_profile = profile.copy()
        sensitive_keys = {"api_key", "api_secret", "access_token", "password", "token", "secret"}
        cred_data = {k: v for k, v in profile.items() if k in sensitive_keys and v}
        if cred_data:
            encrypted_profile["_encrypted"] = encrypt_dict(cred_data)
            for k in cred_data:
                encrypted_profile[k] = "***"
        self.shop_profiles.setdefault(chat_id, {})[platform_key] = encrypted_profile
        await self._persist("shop_profiles", chat_id, self.shop_profiles[chat_id])

    def get_shop_profiles(self, chat_id: int) -> dict[str, dict[str, Any]]:
        raw = self.shop_profiles.get(chat_id, {})
        result: dict[str, dict[str, Any]] = {}
        for plat, prof in raw.items():
            p = prof.copy()
            if "_encrypted" in p:
                try:
                    secrets = decrypt_dict(p.pop("_encrypted"))
                    p.update(secrets)
                except StorageError as _exc:
                    logger.debug("Decryption failed for platform: %s", _exc)
            result[plat] = p
        return result

    # ── Catalogs ──

    async def set_catalog(self, chat_id: int, catalog: list[dict]) -> None:
        self.catalogs[chat_id] = catalog
        await self._persist("catalogs", chat_id, catalog)

    def get_catalog(self, chat_id: int) -> list[dict]:
        return self.catalogs.get(chat_id, [])

    # ── Generic Per-Chat KV ──

    async def set_kv(self, chat_id: int, key: str, value: Any) -> None:
        """Store arbitrary JSON-serializable data under a custom key."""
        store_name = f"custom_{key}"
        # Cache in a dynamic attribute
        cache_attr = f"_custom_{key}"
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, {})
        getattr(self, cache_attr)[chat_id] = value
        await self._persist(store_name, chat_id, value)

    def get_kv(self, chat_id: int, key: str, default: Any = None) -> Any:
        """Read arbitrary data from cache. Returns default if not found."""
        cache_attr = f"_custom_{key}"
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr).get(chat_id, default)
        return default

    async def load_kv(self, key: str) -> None:
        """Load a custom KV namespace from DB into cache."""
        store_name = f"custom_{key}"
        cache_attr = f"_custom_{key}"
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, {})
        async with get_session() as session:
            result = await session.execute(
                select(KVStore).where(KVStore.store_name == store_name)
            )
            for row in result.scalars().all():
                try:
                    getattr(self, cache_attr)[row.chat_id] = json.loads(row.data)
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Suppressed: %s", _exc)


# Module-level singleton — import this everywhere.
store = DataStore()


