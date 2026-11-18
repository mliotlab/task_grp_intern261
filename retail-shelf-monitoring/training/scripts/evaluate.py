"""Evaluate detector weights on a split and append the result to training/results.csv (NFR-01).

python training/scripts/evaluate.py --weights yolov8n.pt --split test
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path

RESULTS = Path("training/results.csv")
FIELDS = ["timestamp", "weights", "split", "map50", "map50_95", "precision", "recall", "notes"]


def append_result(row: dict) -> None:
    new = not RESULTS.exists()
    with RESULTS.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", default="training/configs/sku110k_subset.yaml")
    parser.add_argument("--split", default="test", choices=["val", "test"])
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    from ultralytics import YOLO

    metrics = YOLO(args.weights).val(
        data=args.data, split=args.split, imgsz=args.imgsz, max_det=400
    )
    row = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "weights": args.weights,
        "split": args.split,
        "map50": round(float(metrics.box.map50), 4),
        "map50_95": round(float(metrics.box.map), 4),
        "precision": round(float(metrics.box.mp), 4),
        "recall": round(float(metrics.box.mr), 4),
        "notes": args.notes,
    }
    append_result(row)
    print(row)


if __name__ == "__main__":
    main()
