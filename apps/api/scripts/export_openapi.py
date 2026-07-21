from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = API_ROOT.parents[1]
OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "openapi.json"

sys.path.insert(0, str(API_ROOT))

from app.main import app  # noqa: E402


def render_openapi() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export PriceTracker's OpenAPI schema.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when docs/openapi.json differs from the application schema.",
    )
    args = parser.parse_args()
    rendered = render_openapi()

    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
            print("docs/openapi.json is stale; run the OpenAPI generation command.")
            return 1
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
