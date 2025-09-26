#!/usr/bin/env python3
"""Parse a Dune dashboard export (JSON) to pull query titles and IDs."""

import json
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: extract_dashboard_queries.py <dashboard_export.json>")
    sys.exit(1)

path = Path(sys.argv[1])
if not path.exists():
    print(f"File does not exist: {path}")
    sys.exit(1)

data = json.loads(path.read_text())

for block in data.get("visualizations", []):
    viz = block.get("visualization", {})
    name = viz.get("title", "<untitled>")
    query = viz.get("query")
    if not query:
        continue
    query_id = query.get("id")
    author = query.get("author", {}).get("name", "?")
    print(f"{name} (query id: {query_id}, author: {author})")
