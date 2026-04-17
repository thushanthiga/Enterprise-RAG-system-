#!/usr/bin/env python3
"""
register_schema.py — Validate schema YAML files and optionally test DB connectivity.

Usage:
    python scripts/register_schema.py [--test]
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def validate_schemas():
    """Check all YAML schema files for correctness."""
    errors = []
    yaml_files = list(SCHEMA_DIR.glob("*.yaml"))

    if not yaml_files:
        print("WARNING: No schema YAML files found in schemas/")
        return

    for yf in yaml_files:
        print(f"Checking: {yf.name}")
        try:
            with open(yf) as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                errors.append(f"  {yf.name}: root is not a dict")
                continue

            tables = data.get("tables", {})
            if not tables:
                errors.append(f"  {yf.name}: no 'tables' key found")
                continue

            for table_name, table_info in tables.items():
                if not isinstance(table_info, dict):
                    errors.append(f"  {yf.name}: table '{table_name}' is not a dict")
                    continue

                columns = table_info.get("columns", {})
                if not columns:
                    errors.append(f"  {yf.name}: table '{table_name}' has no columns")
                    continue

                desc = table_info.get("description", "")
                if not desc:
                    print(f"  HINT: table '{table_name}' has no description — add one for better LLM results")

                for col_name, col_info in columns.items():
                    if isinstance(col_info, dict):
                        if "type" not in col_info:
                            print(f"  HINT: {table_name}.{col_name} has no 'type' — consider adding")
                    # Allow simple string values too

                print(f"  ✓ {table_name}: {len(columns)} columns")

        except yaml.YAMLError as e:
            errors.append(f"  {yf.name}: YAML parse error: {e}")

    if errors:
        print("\n❌ Errors found:")
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print(f"\n✓ All {len(yaml_files)} schema file(s) valid")


def test_connectivity():
    """Test database connections (requires async, simplified sync check)."""
    from config import DB_URLS
    from sqlalchemy import create_engine, text

    for source, url in DB_URLS.items():
        if not url:
            print(f"  {source}: no URL configured — SKIPPED")
            continue

        # Convert async URL to sync for testing
        sync_url = url.replace("+asyncpg", "").replace("+aiosqlite", "")
        try:
            engine = create_engine(sync_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"  ✓ {source}: connected OK")
        except Exception as e:
            print(f"  ✗ {source}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate schema YAML files")
    parser.add_argument("--test", action="store_true", help="Also test DB connectivity")
    args = parser.parse_args()

    validate_schemas()

    if args.test:
        print("\nTesting database connectivity...")
        test_connectivity()
