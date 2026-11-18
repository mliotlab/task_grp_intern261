"""Publish trained weights to the model registry.

Creates models/<version>/{weights.pt, SHA256SUMS, MODEL_CARD.md}. Usage:

    python training/scripts/export_model.py \\
        --weights runs/detect/<run>/weights/best.pt --version yolov8n-sku-v1
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[3] / "docs" / "templates" / "MODEL_CARD.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--registry", type=Path, default=Path("models"))
    args = parser.parse_args()

    out = args.registry / args.version
    out.mkdir(parents=True, exist_ok=False)
    target = out / "weights.pt"
    shutil.copy2(args.weights, target)
    (out / "SHA256SUMS").write_text(f"{sha256(target)}  weights.pt\n")
    if TEMPLATE.exists():
        shutil.copy2(TEMPLATE, out / "MODEL_CARD.md")
    print(f"Published {args.version} → {out}.")
    print("Fill in MODEL_CARD.md and upload weights.pt to the lab drive (never to Git).")


if __name__ == "__main__":
    main()
