"""Build a deterministic SKU-110K subset in YOLO format.

python training/scripts/prepare_subset.py --config training/configs/data_subset.yaml
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import yaml


def sample_split(image_ids: list[str], n: int, seed: int) -> list[str]:
    """Deterministic sample of `n` ids (sorted first, so file-listing order does not matter)."""
    rng = random.Random(seed)
    return rng.sample(sorted(image_ids), n)


def to_yolo_line(x1: float, y1: float, x2: float, y2: float, img_w: int, img_h: int) -> str:
    """Convert a pixel box to a YOLO label line: `class cx cy w h` normalised to [0, 1]."""
    cx = (x1 + x2) / 2 / img_w
    cy = (y1 + y2) / 2 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = yaml.safe_load(args.config.read_text())
    print(f"Building {cfg['dataset_version']} from {cfg['raw_dir']} → {cfg['out_dir']}")
    # TODO(Sprint 1):
    #  1. read annotations_{train,val,test}.csv
    #     (image_name, x1, y1, x2, y2, class, image_width, image_height);
    #  2. sample_split() each official split to the sizes in cfg["splits"] using cfg["seed"];
    #  3. copy images to <out_dir>/images/<split>/,
    #     write labels/<split>/<image>.txt with to_yolo_line();
    #  4. write <out_dir>/MANIFEST.csv (image, split, n_boxes) and print stats.
    raise SystemExit("prepare_subset not implemented yet")


if __name__ == "__main__":
    main()
