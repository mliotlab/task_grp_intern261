"""Batch analysis of a folder of images → CSV report (FR-08).

shelfmon-batch --input data/samples --out reports/batch.csv --store-id S001
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--input", type=Path, required=True, help="Folder of .jpg/.png images")
    parser.add_argument("--out", type=Path, default=Path("reports/batch.csv"))
    parser.add_argument("--store-id", default="batch")
    args = parser.parse_args()

    images = sorted(
        p for p in args.input.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    print(f"Found {len(images)} images in {args.input}")
    # TODO(FR-08): load detector once, run pipeline.analyze_image per image (cv2.imread),
    # write one CSV row per image: file, product_count, gap_count, fill_rate, alert, latency_ms.
    raise SystemExit("Batch CLI not implemented yet (FR-08)")


if __name__ == "__main__":
    main()
