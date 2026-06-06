
from __future__ import annotations
#!/usr/bin/env python3
"""
scripts/migrate_to_postgresql.py — SQLite → PostgreSQL Migration Tool
═══════════════════════════════════════════════════════════════════════
Real, production-grade data migration. NOT a toy.

Usage:
    python scripts/migrate_to_postgresql.py \
        --sqlite data/arki.db \
        --postgres postgresql://user:pass@host:5432/arki

What it does:
    1. Reads all tables from SQLite
    2. Creates schema in PostgreSQL (via SQLAlchemy models)
    3. Migrates data in batches (configurable batch size)
    4. Verifies row counts match
    5. Reports migration results

Requirements:
    pip install psycopg2-binary sqlalchemy aiosqlite
"""

import argparse
import logging
import os
import sys
import time
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, MetaData, Table, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_tables(engine: sa.Engine) -> List[str]:
    """Get all table names from a database."""
    inspector = inspect(engine)
    return inspector.get_table_names()


def count_rows(engine: sa.Engine, table_name: str) -> int:
    """Count rows in a table."""
    with engine.connect() as conn:
        result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
        return result.scalar()


def migrate_table(
    src_engine: sa.Engine,
    dst_engine: sa.Engine,
    table_name: str,
    batch_size: int = 1000,
) -> int:
    """Migrate a single table from source to destination."""
    src_meta = MetaData()
    src_table = Table(table_name, src_meta, autoload_with=src_engine)

    # Read column names
    columns = [col.name for col in src_table.columns]

    # Read all rows from source
    total = 0
    offset = 0

    while True:
        with src_engine.connect() as src_conn:
            query = sa.select(src_table).offset(offset).limit(batch_size)
            rows = src_conn.execute(query).fetchall()

        if not rows:
            break

        # Insert into destination
        with dst_engine.begin() as dst_conn:
            # Build insert dicts
            insert_data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                insert_data.append(row_dict)

            # Reflect destination table
            dst_meta = MetaData()
            dst_table = Table(table_name, dst_meta, autoload_with=dst_engine)

            try:
                dst_conn.execute(dst_table.insert(), insert_data)
            except Exception as e:
                logger.error("Error inserting batch at offset %d: %s", offset, e)
                # Try one-by-one for this batch
                success = 0
                for row_dict in insert_data:
                    try:
                        dst_conn.execute(dst_table.insert().values(**row_dict))
                        success += 1
                    except Exception as row_e:
                        logger.warning("Skipped row: %s", row_e)
                total += success
                offset += batch_size
                continue

        total += len(rows)
        offset += batch_size

        if total % 5000 == 0:
            logger.info("  ... %s: %d rows migrated", table_name, total)

    return total


def reset_sequences(engine: sa.Engine, table_name: str):
    """Reset PostgreSQL auto-increment sequences after data import."""
    with engine.begin() as conn:
        try:
            # Find the sequence name
            result = conn.execute(text(f"""
                SELECT pg_get_serial_sequence('"{table_name}"', 'id')
            """))
            seq_name = result.scalar()
            if seq_name:
                conn.execute(text(f"""
                    SELECT setval('{seq_name}', COALESCE(
                        (SELECT MAX(id) FROM "{table_name}"), 0
                    ) + 1, false)
                """))
                logger.info("  Sequence reset for %s", table_name)
        except Exception:
            pass  # Table may not have an id column or sequence


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite → PostgreSQL")
    parser.add_argument("--sqlite", required=True, help="SQLite database path")
    parser.add_argument("--postgres", required=True, help="PostgreSQL connection URL")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size")
    parser.add_argument("--drop-existing", action="store_true",
                        help="Drop existing PostgreSQL tables first")
    args = parser.parse_args()

    # Validate SQLite path
    if not os.path.exists(args.sqlite):
        logger.error("SQLite database not found: %s", args.sqlite)
        sys.exit(1)

    sqlite_url = f"sqlite:///{args.sqlite}"
    pg_url = args.postgres
    if not pg_url.startswith("postgresql"):
        logger.error("PostgreSQL URL must start with 'postgresql://'")
        sys.exit(1)

    logger.info("═══ SQLite → PostgreSQL Migration ═══")
    logger.info("Source: %s", args.sqlite)
    logger.info("Target: %s", pg_url.split("@")[-1] if "@" in pg_url else pg_url)
    logger.info("Batch size: %d", args.batch_size)

    # Connect to both databases
    src_engine = create_engine(sqlite_url)
    dst_engine = create_engine(pg_url)

    # Create schema in PostgreSQL from models
    logger.info("\n── Creating PostgreSQL schema from models ──")
    from database.models import Base
    if args.drop_existing:
        logger.warning("Dropping existing tables...")
        Base.metadata.drop_all(dst_engine)
    Base.metadata.create_all(dst_engine)
    logger.info("Schema created.")

    # Get tables to migrate
    src_tables = get_tables(src_engine)
    dst_tables = get_tables(dst_engine)
    
    # Only migrate tables that exist in both
    tables_to_migrate = [t for t in src_tables if t in dst_tables and t != "alembic_version"]
    logger.info("\n── Migrating %d tables ──", len(tables_to_migrate))

    start_time = time.time()
    results: Dict[str, Dict[str, Any]] = {}

    for table_name in tables_to_migrate:
        src_count = count_rows(src_engine, table_name)
        if src_count == 0:
            logger.info("  %-30s  (empty, skipped)", table_name)
            results[table_name] = {"src": 0, "dst": 0, "status": "skipped"}
            continue

        logger.info("  %-30s  %d rows ...", table_name, src_count)
        migrated = migrate_table(src_engine, dst_engine, table_name, args.batch_size)
        dst_count = count_rows(dst_engine, table_name)

        # Reset sequences
        reset_sequences(dst_engine, table_name)

        status = "✅" if dst_count >= src_count else "⚠️ MISMATCH"
        results[table_name] = {"src": src_count, "dst": dst_count, "status": status}
        logger.info("  %-30s  %s (src=%d, dst=%d)", table_name, status, src_count, dst_count)

    elapsed = time.time() - start_time

    # Summary
    logger.info("\n═══ Migration Summary ═══")
    logger.info("%-30s  %8s  %8s  %s", "Table", "Source", "Target", "Status")
    logger.info("─" * 60)
    total_src = 0
    total_dst = 0
    for table_name, info in results.items():
        logger.info("%-30s  %8d  %8d  %s",
                     table_name, info["src"], info["dst"], info["status"])
        total_src += info["src"]
        total_dst += info["dst"]
    logger.info("─" * 60)
    logger.info("%-30s  %8d  %8d", "TOTAL", total_src, total_dst)
    logger.info("\nTime: %.1f seconds", elapsed)

    if total_src == total_dst:
        logger.info("✅ Migration complete — all rows transferred successfully!")
    else:
        logger.warning("⚠️ Row count mismatch! Source=%d, Target=%d", total_src, total_dst)
        sys.exit(1)


if __name__ == "__main__":
    main()


