

import json
import hashlib
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone
from arki_project.exceptions import HandlerError

class VictorMemory:
    """
    Strategic Intelligence Hub.
    Contains pre-loaded knowledge of modern attack techniques and CVEs.
    """
    def __init__(self, data_dir: str = "/home/ubuntu/arki_v29_typed/data/victor_intelligence"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.data_dir / "intelligence_base.json"
        self.data = self._load()
        
        # Inject Intelligence if empty
        if not self.data:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._inject_security_intelligence())
                else:
                    asyncio.run(self._inject_security_intelligence())
            except HandlerError:
                pass

    def _load(self) -> Dict[str, Any]:
        if self.storage_file.exists():
            try: return json.loads(self.storage_file.read_text(encoding="utf-8"))
            except: return {}
        return {}

    def _save(self):
        self.storage_file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def _inject_security_intelligence(self):
        intel = [
            {"topic": "CVE-2024-XXXX", "content": "تحلیل آسیب‌پذیری‌های جدید در سرویس‌های وب."},
            {"topic": "MITRE ATT&CK", "content": "چارچوب جامع برای درک تاکتیک‌ها و تکنیک‌های نفوذ."},
            {"topic": "Privilege Escalation", "content": "متدهای ارتقای دسترسی در سیستم‌های لینوکسی مدرن."},
            {"topic": "Anti-Forensics", "content": "تکنیک‌های مخفی‌کاری و حذف ردپا پس از نفوذ."}
        ]
        for item in intel:
            mid = hashlib.sha256(item["topic"].encode()).hexdigest()[:12]
            self.data[mid] = item
        self._save()

    async def store(self, content: str, topic: str) -> str:
        mid = hashlib.sha256(f"{topic}{content}".encode()).hexdigest()[:12]
        self.data[mid] = {"topic": topic, "content": content, "timestamp": datetime.now(timezone.utc).isoformat()}
        self._save()
        return mid

    async def recall(self, query: str) -> List[Dict]:
        results = [m for m in self.data.values() if query.lower() in m["topic"].lower() or query.lower() in m["content"].lower()]
        return results[:5]


