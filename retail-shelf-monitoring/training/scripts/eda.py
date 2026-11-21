"""Compute and document EDA statistics for a generated SKU-110K YOLO subset.

python training/scripts/eda.py --data-dir data/sku110k_subset
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

SPLIT_ORDER = ("train", "val", "test")


def _summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "p10": 0.0,
            "median": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "max": 0.0,
        }
    arr = np.asarray(values, dtype=np.float64)
    p10, p50, p90, p95 = np.percentile(arr, [10, 50, 90, 95])
    return {
        "count": int(arr.size),
        "min": round(float(arr.min()), 6),
        "p10": round(float(p10), 6),
        "median": round(float(p50), 6),
        "mean": round(float(arr.mean()), 6),
        "std": round(float(arr.std(ddof=0)), 6),
        "p90": round(float(p90), 6),
        "p95": round(float(p95), 6),
        "max": round(float(arr.max()), 6),
    }


def _load_manifest_rows(data_dir: Path, manifest_path: Path | None = None) -> list[dict[str, str]]:
    if manifest_path is not None:
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Manifest file not found: '{manifest_path}'")
        with manifest_path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    combined = data_dir / "MANIFEST.csv"
    if combined.is_file():
        with combined.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    rows: list[dict[str, str]] = []
    manifests_dir = data_dir / "manifests"
    for split in SPLIT_ORDER:
        split_csv = manifests_dir / f"{split}.csv"
        if split_csv.is_file():
            with split_csv.open("r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    row.setdefault("split", split)
                    rows.append(row)

    if not rows:
        raise FileNotFoundError(
            f"No MANIFEST.csv or manifests/*.csv found under '{data_dir}'. "
            "Run prepare_subset.py first."
        )
    return rows


def _resolve_image_size(
    row: dict[str, str], data_dir: Path, split: str, image_name: str
) -> tuple[int, int] | None:
    raw_w = row.get("image_width", "").strip()
    raw_h = row.get("image_height", "").strip()
    if raw_w and raw_h:
        w = int(float(raw_w))
        h = int(float(raw_h))
        if w > 0 and h > 0:
            return w, h

    image_path = data_dir / "images" / split / image_name
    if image_path.is_file():
        with Image.open(image_path) as img:
            return img.size
    return None


def _parse_yolo_labels(label_path: Path) -> list[tuple[float, float]]:
    """Return list of `(w_norm, h_norm)` pairs from a YOLO label file."""
    if not label_path.is_file():
        return []

    boxes: list[tuple[float, float]] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        w_norm = float(parts[3])
        h_norm = float(parts[4])
        if w_norm > 0.0 and h_norm > 0.0:
            boxes.append((w_norm, h_norm))
    return boxes


def _compute_split_stats(rows: list[dict[str, str]], data_dir: Path) -> dict[str, Any]:
    boxes_per_image: list[float] = []
    widths: list[float] = []
    heights: list[float] = []
    img_aspect_ratios: list[float] = []
    megapixels: list[float] = []
    resolutions: Counter[str] = Counter()

    norm_w: list[float] = []
    norm_h: list[float] = []
    norm_area: list[float] = []
    box_aspect_ratios: list[float] = []

    px_w: list[float] = []
    px_h: list[float] = []
    px_area: list[float] = []

    coco_buckets = {"small_lt_32sq": 0, "medium_32_to_96sq": 0, "large_ge_96sq": 0}
    norm_buckets = {
        "tiny_lt_0.001": 0,
        "small_0.001_to_0.005": 0,
        "medium_0.005_to_0.02": 0,
        "large_ge_0.02": 0,
    }

    empty_images = 0

    for row in rows:
        image_name = row["image"].strip()
        split = row["split"].strip()
        label_path = data_dir / "labels" / split / f"{Path(image_name).stem}.txt"
        label_boxes = _parse_yolo_labels(label_path)

        n_boxes = len(label_boxes) if label_path.is_file() else int(row.get("n_boxes", 0))
        boxes_per_image.append(float(n_boxes))
        if n_boxes == 0:
            empty_images += 1

        size = _resolve_image_size(row, data_dir, split, image_name)
        if size is not None:
            img_w, img_h = size
            widths.append(float(img_w))
            heights.append(float(img_h))
            img_aspect_ratios.append(img_w / img_h)
            megapixels.append((img_w * img_h) / 1_000_000.0)
            resolutions[f"{img_w}x{img_h}"] += 1

        for bw, bh in label_boxes:
            area = bw * bh
            norm_w.append(bw)
            norm_h.append(bh)
            norm_area.append(area)
            box_aspect_ratios.append(bw / bh)

            if area < 0.001:
                norm_buckets["tiny_lt_0.001"] += 1
            elif area < 0.005:
                norm_buckets["small_0.001_to_0.005"] += 1
            elif area < 0.02:
                norm_buckets["medium_0.005_to_0.02"] += 1
            else:
                norm_buckets["large_ge_0.02"] += 1

            if size is not None:
                img_w, img_h = size
                bw_px = bw * img_w
                bh_px = bh * img_h
                area_px2 = bw_px * bh_px
                px_w.append(bw_px)
                px_h.append(bh_px)
                px_area.append(area_px2)

                if area_px2 < 32 * 32:
                    coco_buckets["small_lt_32sq"] += 1
                elif area_px2 < 96 * 96:
                    coco_buckets["medium_32_to_96sq"] += 1
                else:
                    coco_buckets["large_ge_96sq"] += 1

    n_images = len(rows)
    total_norm_boxes = len(norm_area)
    total_px_boxes = len(px_area)

    top_resolutions = [
        {
            "resolution": res,
            "count": count,
            "pct": round(100.0 * count / n_images, 2) if n_images else 0.0,
        }
        for res, count in resolutions.most_common(5)
    ]

    return {
        "n_images": n_images,
        "n_boxes": int(sum(boxes_per_image)),
        "empty_images": empty_images,
        "boxes_per_image": _summarize(boxes_per_image),
        "image_resolution": {
            "width_px": _summarize(widths),
            "height_px": _summarize(heights),
            "aspect_ratio": _summarize(img_aspect_ratios),
            "megapixels": _summarize(megapixels),
            "unique_resolutions": len(resolutions),
            "top_resolutions": top_resolutions,
        },
        "bbox_size_distribution": {
            "norm_width": _summarize(norm_w),
            "norm_height": _summarize(norm_h),
            "norm_area": _summarize(norm_area),
            "aspect_ratio_w_over_h": _summarize(box_aspect_ratios),
            "pixel_width": _summarize(px_w),
            "pixel_height": _summarize(px_h),
            "pixel_area": _summarize(px_area),
            "coco_area_buckets": {
                k: {
                    "count": v,
                    "pct": round(100.0 * v / total_px_boxes, 2) if total_px_boxes else 0.0,
                }
                for k, v in coco_buckets.items()
            },
            "norm_area_buckets": {
                k: {
                    "count": v,
                    "pct": round(100.0 * v / total_norm_boxes, 2) if total_norm_boxes else 0.0,
                }
                for k, v in norm_buckets.items()
            },
        },
    }


def compute_eda(data_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    """Compute EDA statistics per split and overall from generated subset files."""
    rows = _load_manifest_rows(data_dir, manifest_path=manifest_path)

    rows_by_split: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        rows_by_split.setdefault(row["split"].strip(), []).append(row)

    ordered_splits = [s for s in SPLIT_ORDER if s in rows_by_split] + [
        s for s in sorted(rows_by_split) if s not in SPLIT_ORDER
    ]

    metadata_path = data_dir / "dataset_metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    splits_stats = {
        split: _compute_split_stats(rows_by_split[split], data_dir) for split in ordered_splits
    }
    overall_stats = _compute_split_stats(rows, data_dir)

    return {
        "dataset_version": metadata.get("dataset_version", data_dir.name),
        "seed": metadata.get("seed"),
        "manifest_sha256": metadata.get("manifest_sha256"),
        "splits": splits_stats,
        "overall": overall_stats,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Format EDA statistics as a Markdown report."""
    lines: list[str] = [
        "# SKU-110K Subset Exploratory Data Analysis (EDA)",
        "",
        f"- **Dataset version:** `{report.get('dataset_version', 'unknown')}`",
    ]
    if report.get("seed") is not None:
        lines.append(f"- **Seed:** `{report['seed']}`")
    if report.get("manifest_sha256"):
        lines.append(f"- **Manifest SHA-256:** `{report['manifest_sha256']}`")

    lines.extend(
        [
            "",
            "## 1. Split Overview & Boxes per Image",
            "",
            "| Split | Images | Total Boxes | Min | P10 | Median | Mean | Std | P90 | P95 | Max |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    sections = [*report["splits"].items(), ("overall", report["overall"])]
    for name, stats in sections:
        b = stats["boxes_per_image"]
        lines.append(
            f"| {name} | {stats['n_images']} | {stats['n_boxes']} | "
            f"{b['min']:.0f} | {b['p10']:.1f} | {b['median']:.1f} | {b['mean']:.1f} | "
            f"{b['std']:.1f} | {b['p90']:.1f} | {b['p95']:.1f} | {b['max']:.0f} |"
        )

    lines.extend(
        [
            "",
            "## 2. Image Resolution",
            "",
            "| Split | Width (min / med / max) | Height (min / med / max) | "
            "Aspect Ratio (med) | Megapixels (med) | Unique |",
            "|---|---|---|---|---:|---:|",
        ]
    )
    for name, stats in sections:
        res = stats["image_resolution"]
        w = res["width_px"]
        h = res["height_px"]
        ar = res["aspect_ratio"]
        mp = res["megapixels"]
        lines.append(
            f"| {name} | {w['min']:.0f} / {w['median']:.0f} / {w['max']:.0f} | "
            f"{h['min']:.0f} / {h['median']:.0f} / {h['max']:.0f} | "
            f"{ar['median']:.2f} | {mp['median']:.2f} | {res['unique_resolutions']} |"
        )

    top_res = report["overall"]["image_resolution"]["top_resolutions"]
    if top_res:
        lines.extend(["", "**Top resolutions (overall):**", ""])
        for item in top_res:
            lines.append(f"- `{item['resolution']}`: {item['count']} images ({item['pct']:.2f}%)")

    lines.extend(
        [
            "",
            "## 3. Bounding Box Size Distribution",
            "",
            "| Split | Norm W (med / mean) | Norm H (med / mean) | Norm Area (med / mean) | "
            "Pixel W (med / mean) | Pixel H (med / mean) | Box Aspect W/H (med) |",
            "|---|---|---|---|---|---|---:|",
        ]
    )
    for name, stats in sections:
        bb = stats["bbox_size_distribution"]
        nw = bb["norm_width"]
        nh = bb["norm_height"]
        na = bb["norm_area"]
        pw = bb["pixel_width"]
        ph = bb["pixel_height"]
        bar = bb["aspect_ratio_w_over_h"]
        lines.append(
            f"| {name} | {nw['median']:.4f} / {nw['mean']:.4f} | "
            f"{nh['median']:.4f} / {nh['mean']:.4f} | "
            f"{na['median']:.5f} / {na['mean']:.5f} | "
            f"{pw['median']:.1f} / {pw['mean']:.1f} | "
            f"{ph['median']:.1f} / {ph['mean']:.1f} | "
            f"{bar['median']:.2f} |"
        )

    coco = report["overall"]["bbox_size_distribution"]["coco_area_buckets"]
    lines.extend(
        [
            "",
            "**COCO-style pixel area buckets (overall):**",
            "",
            f"- Small (`area < 32^2` px): {coco['small_lt_32sq']['count']} "
            f"({coco['small_lt_32sq']['pct']:.2f}%)",
            f"- Medium (`32^2 <= area < 96^2` px): {coco['medium_32_to_96sq']['count']} "
            f"({coco['medium_32_to_96sq']['pct']:.2f}%)",
            f"- Large (`area >= 96^2` px): {coco['large_ge_96sq']['count']} "
            f"({coco['large_ge_96sq']['pct']:.2f}%)",
            "",
            "## 4. Training & Inference Implications",
            "",
            f"- **Dense scenes:** overall max boxes/image is "
            f"`{report['overall']['boxes_per_image']['max']:.0f}` "
            f"(p95: `{report['overall']['boxes_per_image']['p95']:.1f}`). "
            "Verify `max_det` in `training/configs/train_yolov8n.yaml` and `evaluate.py` "
            "exceeds the tail density.",
            f"- **Input resolution:** median image resolution is "
            f"`{report['overall']['image_resolution']['width_px']['median']:.0f}x"
            f"{report['overall']['image_resolution']['height_px']['median']:.0f}`; "
            "compare against `imgsz: 1024` during training and `1920` max-side resize in serving.",
            "",
        ]
    )
    return "\n".join(lines)


def run_eda(
    data_dir: Path,
    manifest_path: Path | None = None,
    out_md: Path | None = None,
    out_json: Path | None = None,
) -> dict[str, Any]:
    """Run EDA and optionally write Markdown and JSON reports."""
    report = compute_eda(data_dir, manifest_path=manifest_path)

    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with out_json.open("w", encoding="utf-8", newline="\n") as jf:
            json.dump(report, jf, indent=2)
            jf.write("\n")

    if out_md is not None:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        with out_md.open("w", encoding="utf-8", newline="\n") as mf:
            mf.write(render_markdown(report))

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/sku110k_subset"))
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=Path("docs/reports/sku110k_eda.md"))
    parser.add_argument("--out-json", type=Path, default=Path("docs/reports/sku110k_eda.json"))
    args = parser.parse_args()

    report = run_eda(
        data_dir=args.data_dir,
        manifest_path=args.manifest,
        out_md=args.out_md,
        out_json=args.out_json,
    )
    print(render_markdown(report))
    print(f"Wrote Markdown report to {args.out_md} and JSON summary to {args.out_json}")


if __name__ == "__main__":
    main()
