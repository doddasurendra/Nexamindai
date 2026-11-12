"""
Parse the public-apis README.md to extract all APIs, categories, and MCP servers.
Outputs structured JSON for ingestion into NexaMind AI.
"""
import re
import json
import urllib.request
from datetime import datetime, timezone

README_URL = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
OUTPUT = "public_apis_catalog.json"


def fetch_readme() -> str:
    with urllib.request.urlopen(README_URL) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_apis(content: str):
    lines = content.splitlines()
    entries = []  # API entries
    mcps = []     # MCP server entries
    categories = []
    current_category = None
    current_section = None  # 'apis' | 'mcps' | None

    api_re = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$")
    mcp_re = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$")

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Detect category headers: ### Name
        mcat = re.match(r"^###\s+(.+?)\s*$", line)
        if mcat:
            cat_name = mcat.group(1).strip()
            # Skip the header/apilayer banner and index navigation lines
            if cat_name in ("APIs Covered Under APILayer Suite!",):
                i += 1
                continue
            current_category = cat_name
            categories.append(cat_name)
            current_section = None
            i += 1
            continue

        # Detect section header lines
        if line.strip() == "### APIs Covered Under APILayer Suite!":
            current_section = "api_layer"
            i += 1
            continue
        if line.strip() == "## MCP Servers":
            current_section = "mcps"
            i += 1
            continue
        if line.strip() == "## Index":
            current_section = "index"
            i += 1
            continue

        # Header row separator lines for tables
        if line.strip().startswith("|") and "|:---" in line or line.strip().startswith("|---"):
            # Determine if it's an API table (Auth | HTTPS | CORS) or MCP (Auth | Transport | Install)
            # Look at next line to determine
            i += 1
            continue

        # Table rows
        if line.strip().startswith("|") and "]" in line and "(" in line:
            if current_section == "mcps":
                m = mcp_re.match(line.strip())
                if m:
                    mcps.append({
                        "name": m.group(1).strip(),
                        "url": m.group(2).strip(),
                        "description": m.group(3).strip(),
                        "auth": m.group(4).strip(),
                        "transport": m.group(5).strip(),
                        "install": m.group(6).strip(),
                        "category": current_category,
                        "source": "public-apis README",
                    })
            else:
                m = api_re.match(line.strip())
                if m:
                    entries.append({
                        "name": m.group(1).strip(),
                        "url": m.group(2).strip(),
                        "description": m.group(3).strip(),
                        "auth": m.group(4).strip(),
                        "https": m.group(5).strip(),
                        "cors": m.group(6).strip(),
                        "category": current_category,
                        "source": "public-apis README",
                    })
        i += 1

    return entries, mcps, categories


def main():
    content = fetch_readme()
    entries, mcps, categories = parse_apis(content)

    catalog = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_url": README_URL,
        "total_apis": len(entries),
        "total_mcps": len(mcps),
        "categories": categories,
        "category_count": len(categories),
        "apis": entries,
        "mcps": mcps,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Retrieved README from {README_URL}")
    print(f"Categories found: {len(categories)}")
    print(f"APIs found: {len(entries)}")
    print(f"MCP servers found: {len(mcps)}")
    print(f"Output written to {OUTPUT}")

    # Show category breakdown
    from collections import Counter
    cat_counts = Counter(e["category"] for e in entries)
    print("\n=== Category breakdown ===")
    for cat, count in cat_counts.most_common():
        print(f"  {cat}: {count}")
    print(f"\nMCP servers: {len(mcps)}")


if __name__ == "__main__":
    main()
