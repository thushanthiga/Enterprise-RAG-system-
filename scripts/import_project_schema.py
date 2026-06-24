import os
import sys
import argparse
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app import models
from sqlalchemy import select

async def import_schema(project_id: int, schema_file: str):
    schema_path = Path(schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_file}")
        return

    with open(schema_path, "r") as f:
        schema_content = f.read()

    async with SessionLocal() as db:
        result = await db.execute(select(models.Project).where(models.Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            print(f"Error: Project with ID {project_id} not found.")
            return

        print(f"Updating Project: {project.name} (ID: {project_id})")
        
        extra_data = project.extra_data or {}
        extra_data["db_schema"] = schema_content
        project.extra_data = extra_data
        
        # Explicitly flag as modified for JSON types if needed
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(project, "extra_data")
        
        await db.commit()
        print(f"Successfully imported schema into project {project_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import DB schema into project metadata")
    parser.add_argument("--project", type=int, required=True, help="Project ID")
    parser.add_argument("--file", type=str, required=True, help="Path to schema markdown file")
    
    args = parser.parse_args()
    
    asyncio.run(import_schema(args.project, args.file))
