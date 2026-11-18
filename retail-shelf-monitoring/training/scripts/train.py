"""Fine-tune YOLO on the SKU-110K subset.

python training/scripts/train.py --config training/configs/train_yolov8n.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = yaml.safe_load(args.config.read_text())

    from ultralytics import YOLO  # requires `pip install -e ".[ml]"`

    model = YOLO(cfg["base_weights"])
    # TODO(Sprint 2–3): log params, metrics and GPU time to training/results.csv (+ MLflow).
    model.train(data=cfg["data"], name=cfg["run_name"], **cfg["train"])


if __name__ == "__main__":
    main()
