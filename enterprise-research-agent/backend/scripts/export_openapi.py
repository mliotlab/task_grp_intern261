"""Export the OpenAPI contract so it can be committed and diffed in CI (NFR-07).

python scripts/export_openapi.py --out ../docs/api/openapi.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("../docs/api/openapi.yaml"))
    args = parser.parse_args()
    spec = create_app().openapi()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True), "utf-8")
    print(f"OpenAPI spec written to {args.out}")


if __name__ == "__main__":
    main()
