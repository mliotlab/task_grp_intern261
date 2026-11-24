"""Build a deterministic SKU-110K subset in YOLO format.

python training/scripts/prepare_subset.py --config training/configs/data_subset.yaml
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, NamedTuple

import yaml

MANIFEST_FIELDS = ["image", "split", "n_boxes", "image_width", "image_height"]
SPLIT_ORDER = ("train", "val", "test")


class BoxRecord(NamedTuple):
    """Single ground-truth bounding box in absolute pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float
    img_w: int
    img_h: int


def sample_split(image_ids: list[str], n: int, seed: int) -> list[str]:
    """Deterministic sample of `n` ids (sorted first, so file-listing order does not matter)."""
    rng = random.Random(seed)
    return rng.sample(sorted(image_ids), n)


def load_excluded_ids(exclude_path: Path | None) -> dict[str, set[str]]:
    """Load `(split, image)` exclusions from a CSV file with `split,image,...` columns."""
    excluded: dict[str, set[str]] = defaultdict(set)
    if exclude_path is None:
        return excluded
    if not exclude_path.is_file():
        raise FileNotFoundError(f"Exclude CSV file not found: '{exclude_path}'")

    with exclude_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            split = (row.get("split") or "").strip()
            image = (row.get("image") or "").strip()
            if split and image:
                excluded[split].add(image)
    return dict(excluded)


def build_candidate_queue(image_ids: list[str], base_n: int, seed: int) -> list[str]:
    """Build deterministic priority queue: original `v1` sample followed by shuffled tail.

    This preserves clean images already vetted in `v1` while ensuring deterministic backfill
    for every excluded image when reproduced from raw annotations and `(seed, exclude_file)`.
    """
    sorted_ids = sorted(image_ids)
    base_ids = sample_split(sorted_ids, base_n, seed)
    base_set = set(base_ids)
    tail_ids = [img_id for img_id in sorted_ids if img_id not in base_set]
    random.Random(seed).shuffle(tail_ids)
    return base_ids + tail_ids


def select_split_with_exclusions(
    image_ids: list[str],
    n: int,
    seed: int,
    excluded: set[str] | None = None,
) -> list[str]:
    """Deterministically select `n` ids while skipping `excluded` via queue backfill."""
    if not excluded:
        return sample_split(image_ids, n, seed)

    queue = build_candidate_queue(image_ids, base_n=n, seed=seed)
    selected = [img_id for img_id in queue if img_id not in excluded]
    if len(selected) < n:
        raise ValueError(
            f"Requires {n} images after exclusions, but only {len(selected)} valid images remain."
        )
    return selected[:n]


def to_yolo_line(x1: float, y1: float, x2: float, y2: float, img_w: int, img_h: int) -> str:
    """Convert a pixel box to a YOLO label line: `class cx cy w h` normalised to [0, 1]."""
    cx = (x1 + x2) / 2 / img_w
    cy = (y1 + y2) / 2 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def find_annotation_csv(raw_dir: Path, split: str) -> Path:
    """Locate `annotations_<split>.csv` inside `raw_dir`."""
    candidates = [
        raw_dir / "annotations" / f"annotations_{split}.csv",
        raw_dir / f"annotations_{split}.csv",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"Missing annotation CSV for split '{split}'. Checked: "
        + ", ".join(str(p) for p in candidates)
    )


def find_image_path(raw_dir: Path, split: str, image_name: str) -> Path:
    """Locate an image file under `raw_dir/images/`."""
    candidates = [
        raw_dir / "images" / image_name,
        raw_dir / "images" / split / image_name,
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"Image '{image_name}' not found for split '{split}'. Checked: "
        + ", ".join(str(p) for p in candidates)
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def read_annotations(csv_path: Path) -> tuple[dict[str, list[BoxRecord]], int]:
    """Parse SKU-110K CSV rows into `{image_name: [BoxRecord, ...]}` and skipped row count."""
    by_image: dict[str, list[BoxRecord]] = defaultdict(list)
    skipped = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row_idx, row in enumerate(reader):
            if not row:
                continue
            if len(row) < 8:
                skipped += 1
                continue

            image_name = row[0].strip()
            try:
                raw_x1 = float(row[1])
                raw_y1 = float(row[2])
                raw_x2 = float(row[3])
                raw_y2 = float(row[4])
                img_w = int(float(row[6]))
                img_h = int(float(row[7]))
            except ValueError:
                # Standard SKU-110K CSVs are headerless; skip a header row if present.
                if row_idx == 0:
                    continue
                skipped += 1
                continue

            if not image_name or img_w <= 0 or img_h <= 0:
                skipped += 1
                continue

            x1 = _clamp(raw_x1, 0.0, float(img_w))
            y1 = _clamp(raw_y1, 0.0, float(img_h))
            x2 = _clamp(raw_x2, 0.0, float(img_w))
            y2 = _clamp(raw_y2, 0.0, float(img_h))
            if x2 <= x1 or y2 <= y1:
                skipped += 1
                continue

            by_image[image_name].append(
                BoxRecord(x1=x1, y1=y1, x2=x2, y2=y2, img_w=img_w, img_h=img_h)
            )

    return dict(by_image), skipped


def _write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prune_stale_files(images_dir: Path, labels_dir: Path, keep_names: set[str]) -> None:
    """Remove files in `images_dir` and `labels_dir` that are not in `keep_names`."""
    keep_stems = {Path(name).stem for name in keep_names}
    for img_path in images_dir.iterdir():
        if img_path.is_file() and img_path.name not in keep_names:
            img_path.unlink()
    for lbl_path in labels_dir.iterdir():
        if lbl_path.is_file() and lbl_path.stem not in keep_stems:
            lbl_path.unlink()


def build_subset(
    cfg: dict[str, Any],
    raw_dir: Path | None = None,
    out_dir: Path | None = None,
    exclude_file: Path | None = None,
) -> dict[str, Any]:
    """Generate deterministic train/val/test YOLO subset, labels, manifests, and metadata."""
    resolved_raw = raw_dir if raw_dir is not None else Path(cfg["raw_dir"])
    resolved_out = out_dir if out_dir is not None else Path(cfg["out_dir"])
    cfg_exclude = cfg.get("exclude_file")
    resolved_exclude = (
        exclude_file if exclude_file is not None else (Path(cfg_exclude) if cfg_exclude else None)
    )
    seed = int(cfg["seed"])
    dataset_version = str(cfg["dataset_version"])
    splits_cfg: dict[str, int] = cfg["splits"]

    if not resolved_raw.is_dir():
        raise FileNotFoundError(
            f"Raw dataset directory does not exist: '{resolved_raw}'. "
            "See data/README.md for download and extraction instructions."
        )

    excluded_by_split = load_excluded_ids(resolved_exclude)
    ordered_splits = [s for s in SPLIT_ORDER if s in splits_cfg] + [
        s for s in splits_cfg if s not in SPLIT_ORDER
    ]

    all_manifest_rows: list[dict[str, Any]] = []
    split_summaries: dict[str, dict[str, int]] = {}

    for split in ordered_splits:
        target_count = int(splits_cfg[split])
        csv_path = find_annotation_csv(resolved_raw, split)
        by_image, skipped = read_annotations(csv_path)

        if len(by_image) < target_count:
            raise ValueError(
                f"Split '{split}' requires {target_count} images, "
                f"but only {len(by_image)} valid images found in '{csv_path}'."
            )

        split_excluded = excluded_by_split.get(split, set())
        selected_ids = select_split_with_exclusions(
            list(by_image.keys()), target_count, seed, excluded=split_excluded
        )
        # Keep manifest and output order deterministic across runs.
        selected_ids_sorted = sorted(selected_ids)

        images_out = resolved_out / "images" / split
        labels_out = resolved_out / "labels" / split
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)
        _prune_stale_files(images_out, labels_out, set(selected_ids_sorted))

        split_rows: list[dict[str, Any]] = []
        total_boxes = 0

        for image_name in selected_ids_sorted:
            boxes = by_image[image_name]
            src_img = find_image_path(resolved_raw, split, image_name)
            dst_img = images_out / image_name
            if not dst_img.is_file() or dst_img.stat().st_size != src_img.stat().st_size:
                shutil.copy2(src_img, dst_img)

            label_lines = [to_yolo_line(b.x1, b.y1, b.x2, b.y2, b.img_w, b.img_h) for b in boxes]
            label_path = labels_out / f"{Path(image_name).stem}.txt"
            with label_path.open("w", encoding="utf-8", newline="\n") as lf:
                lf.write("\n".join(label_lines) + "\n")

            row = {
                "image": image_name,
                "split": split,
                "n_boxes": len(boxes),
                "image_width": boxes[0].img_w,
                "image_height": boxes[0].img_h,
            }
            split_rows.append(row)
            all_manifest_rows.append(row)
            total_boxes += len(boxes)

        _write_manifest(resolved_out / "manifests" / f"{split}.csv", split_rows)
        split_summaries[split] = {
            "images": len(split_rows),
            "boxes": total_boxes,
            "skipped_rows": skipped,
            "excluded_images": len(split_excluded),
        }

    manifest_path = resolved_out / "MANIFEST.csv"
    _write_manifest(manifest_path, all_manifest_rows)

    metadata: dict[str, Any] = {
        "dataset_version": dataset_version,
        "seed": seed,
        "splits": split_summaries,
        "total_images": sum(s["images"] for s in split_summaries.values()),
        "total_boxes": sum(s["boxes"] for s in split_summaries.values()),
        "manifest_sha256": _sha256_file(manifest_path),
    }
    if resolved_exclude is not None:
        metadata["exclude_file_sha256"] = _sha256_file(resolved_exclude)

    metadata_path = resolved_out / "dataset_metadata.json"
    with metadata_path.open("w", encoding="utf-8", newline="\n") as mf:
        json.dump(metadata, mf, indent=2)
        mf.write("\n")

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--exclude-file", type=Path, default=None)
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    raw_dir = args.raw_dir or Path(cfg["raw_dir"])
    out_dir = args.out_dir or Path(cfg["out_dir"])
    print(f"Building {cfg['dataset_version']} from {raw_dir} -> {out_dir} (seed={cfg['seed']})")

    metadata = build_subset(
        cfg, raw_dir=args.raw_dir, out_dir=args.out_dir, exclude_file=args.exclude_file
    )
    for split, info in metadata["splits"].items():
        avg_boxes = info["boxes"] / info["images"] if info["images"] else 0.0
        print(
            f"  {split:<5}: {info['images']} images, {info['boxes']} boxes "
            f"(mean {avg_boxes:.1f}/img, excluded {info['excluded_images']}, "
            f"skipped {info['skipped_rows']} invalid rows)"
        )
    print(
        f"Done: {metadata['total_images']} images, {metadata['total_boxes']} boxes. "
        f"MANIFEST SHA-256: {metadata['manifest_sha256']}"
    )


if __name__ == "__main__":
    main()
