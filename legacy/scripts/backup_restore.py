
#!/usr/bin/env python3
"""
scripts/backup_restore.py — Database Backup & Restore v27.0
═══════════════════════════════════════════════════════════
Usage:
  python scripts/backup_restore.py backup          # Create backup
  python scripts/backup_restore.py restore <file>   # Restore from backup
  python scripts/backup_restore.py list             # List backups
  python scripts/backup_restore.py cleanup [days]   # Remove old backups
"""
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "backups"))
DB_PATH = Path(os.getenv("DATABASE_PATH", "data/arki.db"))


def create_backup() -> str:
    """Create a timestamped database backup."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"arki_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_name

    # Copy with metadata preservation
    shutil.copy2(str(DB_PATH), str(backup_path))

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"✅ Backup created: {backup_path} ({size_mb:.1f} MB)")

    # Also create a compressed version
    import gzip
    gz_path = backup_path.with_suffix(".db.gz")
    with open(backup_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    gz_size_mb = gz_path.stat().st_size / (1024 * 1024)
    print(f"✅ Compressed: {gz_path} ({gz_size_mb:.1f} MB)")

    return str(backup_path)


def restore_backup(backup_file: str) -> bool:
    """Restore database from a backup file."""
    backup_path = Path(backup_file)

    if not backup_path.exists():
        # Try in backup dir
        backup_path = BACKUP_DIR / backup_file
        if not backup_path.exists():
            print(f"❌ Backup not found: {backup_file}")
            return False

    # Handle gzipped backups
    if str(backup_path).endswith(".gz"):
        import gzip
        import tempfile
        with gzip.open(backup_path, "rb") as f_in:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f_out:
                shutil.copyfileobj(f_in, f_out)
                temp_path = f_out.name
        backup_path = Path(temp_path)

    # Safety: backup current DB before restore
    if DB_PATH.exists():
        safety_backup = DB_PATH.with_suffix(f".db.pre_restore_{int(time.time())}")
        shutil.copy2(str(DB_PATH), str(safety_backup))
        print(f"⚠️ Current DB backed up to: {safety_backup}")

    # Restore
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(backup_path), str(DB_PATH))
    size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"✅ Restored from: {backup_path} ({size_mb:.1f} MB)")
    return True


def list_backups() -> None:
    """List all available backups."""
    if not BACKUP_DIR.exists():
        print("No backups directory found.")
        return

    backups = sorted(BACKUP_DIR.glob("arki_*.db*"), reverse=True)
    if not backups:
        print("No backups found.")
        return

    print(f"\n{'#':>3} {'File':<40} {'Size':>10} {'Date':<20}")
    print("─" * 75)
    for i, bp in enumerate(backups, 1):
        size_mb = bp.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(bp.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i:>3} {bp.name:<40} {size_mb:>8.1f}MB {mtime:<20}")
    print(f"\nTotal: {len(backups)} backups")


def cleanup_backups(days: int = 7) -> None:
    """Remove backups older than N days."""
    if not BACKUP_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    for bp in BACKUP_DIR.glob("arki_*.db*"):
        mtime = datetime.fromtimestamp(bp.stat().st_mtime)
        if mtime < cutoff:
            bp.unlink()
            removed += 1
            print(f"🗑️ Removed: {bp.name}")

    print(f"✅ Cleanup done: {removed} old backups removed (>{days} days)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "backup":
        create_backup()
    elif cmd == "restore":
        if len(sys.argv) < 3:
            print("Usage: backup_restore.py restore <backup_file>")
            sys.exit(1)
        restore_backup(sys.argv[2])
    elif cmd == "list":
        list_backups()
    elif cmd == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        cleanup_backups(days)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


