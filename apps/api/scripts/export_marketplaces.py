from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = API_ROOT.parents[1]
OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "marketplaces.json"

sys.path.insert(0, str(API_ROOT))

from app.providers.adapters import adapter_registry  # noqa: E402


def render_marketplaces() -> str:
    """Serialise the store adapters' host rules for the frontend to consume.

    The API is the only place these are defined; the browser-side check in
    apps/web is generated from this file so the two cannot disagree about which
    URLs are accepted.
    """
    marketplaces = {
        adapter.store.value: {
            "domains": sorted(adapter.domains),
            "hostPrefixes": list(adapter.host_prefixes),
        }
        for adapter in adapter_registry.adapters
    }
    return json.dumps(marketplaces, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export PriceTracker's supported marketplaces.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when docs/marketplaces.json differs from the store adapters.",
    )
    args = parser.parse_args()
    rendered = render_marketplaces()

    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
            print("docs/marketplaces.json is stale; run the marketplace generation command.")
            return 1
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
