
"""
Media Storage v9.1
Abstraction for file storage (local, S3, or CDN).
"""
import os
import logging
import hashlib
from pathlib import Path
from typing import Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class MediaStorage:
    """
    Unified media storage:
    - Local filesystem (default)
    - S3-compatible (when configured)
    - CDN URL generation
    """

    def __init__(self, base_dir: str = "data/media") -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._s3_client = None
        self._cdn_url = os.environ.get("CDN_URL", "")
        self._s3_bucket = os.environ.get("S3_BUCKET", "")
        self._try_s3()

    def _try_s3(self) -> Any:
        """Try to initialize S3 client."""
        try:
            import boto3
            self._s3_client = boto3.client('s3',
                endpoint_url=os.environ.get("S3_ENDPOINT"),
                aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
                aws_secret_access_key=os.environ.get("S3_SECRET_KEY"),
            )
            logger.info("S3 storage initialized (bucket: %s)", self._s3_bucket)
        except Exception:
            logger.warning("S3 not available, falling back to local storage")

    async def save(self, data: bytes, filename: str, content_type: str = "") -> str:
        """Save file and return path/URL."""
        # Generate unique name
        file_hash = hashlib.md5(data).hexdigest()[:12]
        ext = Path(filename).suffix
        safe_name = f"{file_hash}{ext}"

        # Save locally
        local_path = self._base_dir / safe_name
        local_path.write_bytes(data)

        # Upload to S3 if available
        if self._s3_client and self._s3_bucket:
            try:
                self._s3_client.put_object(
                    Bucket=self._s3_bucket,
                    Key=f"media/{safe_name}",
                    Body=data,
                    ContentType=content_type,
                )
                if self._cdn_url:
                    return f"{self._cdn_url}/media/{safe_name}"
            except Exception as e:
                logger.error("S3 upload failed: %s", e)

        return str(local_path)

    async def get(self, filename: str) -> Optional[bytes]:
        """Read a file."""
        local_path = self._base_dir / filename
        if local_path.exists():
            return local_path.read_bytes()
        return None

    async def delete(self, filename: str) -> Any:
        """Delete a file."""
        local_path = self._base_dir / filename
        if local_path.exists():
            local_path.unlink()

    @property
    def stats(self) -> dict:
        files = list(self._base_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        return {
            "files": len(files),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "backend": "s3" if self._s3_client else "local",
        }


_storage: Optional[MediaStorage] = None

def get_media_storage() -> MediaStorage:
    global _storage
    if _storage is None:
        _storage = MediaStorage()
    return _storage


