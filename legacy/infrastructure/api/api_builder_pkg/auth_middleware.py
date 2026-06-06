
"""
api_builder_pkg/auth_middleware.py — AuthMiddleware
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AuthMiddleware:
    """Validates API requests and enforces tier-based access control.
    
    Tiers:
      NONE     — No auth needed (public endpoints like /models/list)
      BASIC    — Any valid API key
      PREMIUM  — Premium tier key required
      ENTERPRISE — Enterprise tier with full access
    """
    
    def __init__(self):
        self._api_keys: Dict[str, Dict] = {}  # key_hash → {user_id, tier, created_at}
        self._revoked: Set[str] = set()
    
    def register_key(self, api_key: str, user_id: str, tier: str = "basic") -> str:
        """Register an API key for a user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self._api_keys[key_hash] = {
            "user_id": user_id,
            "tier": tier,
            "created_at": time.time(),
            "last_used": None,
            "request_count": 0,
        }
        return key_hash
    
    def validate(self, api_key: str, required_level: AuthLevel) -> Tuple[bool, Optional[Dict]]:
        """Validate an API key against a required access level.
        
        Returns:
            (valid, user_info) — user_info has user_id, tier if valid.
        """
        if required_level == AuthLevel.NONE:
            return True, {"user_id": "anonymous", "tier": "none"}
        
        if not api_key:
            return False, None
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self._revoked:
            return False, None
        
        info = self._api_keys.get(key_hash)
        if not info:
            return False, None
        
        # Tier hierarchy: enterprise > premium > basic
        tier_levels = {"basic": 1, "premium": 2, "enterprise": 3}
        required_levels = {
            AuthLevel.BASIC: 1,
            AuthLevel.PREMIUM: 2,
            AuthLevel.ENTERPRISE: 3,
        }
        
        user_level = tier_levels.get(info["tier"], 0)
        needed = required_levels.get(required_level, 1)
        
        if user_level < needed:
            return False, None
        
        # Update usage
        info["last_used"] = time.time()
        info["request_count"] += 1
        
        return True, {"user_id": info["user_id"], "tier": info["tier"]}
    
    def revoke_key(self, api_key: str):
        """Revoke an API key."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self._revoked.add(key_hash)
    
    def generate_key(self, user_id: str, tier: str = "basic") -> str:
        """Generate and register a new API key."""
        raw_key = f"ark_{uuid.uuid4().hex}"
        self.register_key(raw_key, user_id, tier)
        return raw_key


# ═══════════════════════════════════════════════════════════════════
# Pipeline Builder — Chain multiple models/endpoints
# ═══════════════════════════════════════════════════════════════════



