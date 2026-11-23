from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from shelfmon.pipeline import resize_max_side


def _load_script(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, Path(rel_path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prepare_subset = _load_script("prepare_subset", "training/scripts/prepare_subset.py")
eda = _load_script("eda", "training/scripts/eda.py")


def test_sample_split_is_deterministic_and_order_independent() -> None:
    ids = [f"img_{i}" for i in range(100)]
    a = prepare_subset.sample_split(ids, 10, seed=1)
    b = prepare_subset.sample_split(list(reversed(ids)), 10, seed=1)
    assert a == b and len(set(a)) == 10


def test_to_yolo_line_normalises() -> None:
    line = prepare_subset.to_yolo_line(0, 0, 100, 50, img_w=200, img_h=100)
    assert line == "0 0.250000 0.250000 0.500000 0.500000"


@pytest.mark.parametrize(
    ("shape", "expected"), [((3000, 1500, 3), (1920, 960)), ((800, 600, 3), (800, 600))]
)
def test_resize_max_side(shape: tuple[int, int, int], expected: tuple[int, int]) -> None:
    out, _ = resize_max_side(np.zeros(shape, dtype=np.uint8), 1920)
    assert out.shape[:2] == expected


def test_read_annotations_handles_header_clamping_and_invalid_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "annotations_train.csv"
    csv_path.write_text(
        "\n".join(
            [
                "image_name,x1,y1,x2,y2,class,image_width,image_height",
                "img_a.jpg,-10,5,250,100,object,200,100",
                "img_a.jpg,10,10,10,50,object,200,100",  # degenerate width=0 -> skipped
                "img_b.jpg,0,0,50,50,object,0,100",  # invalid image width -> skipped
                "bad_short_row",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    by_image, skipped = prepare_subset.read_annotations(csv_path)
    assert skipped == 3
    assert list(by_image.keys()) == ["img_a.jpg"]
    box = by_image["img_a.jpg"][0]
    assert (box.x1, box.y1, box.x2, box.y2) == (0.0, 5.0, 200.0, 100.0)


def _create_synthetic_raw_dataset(raw_dir: Path) -> None:
    (raw_dir / "annotations").mkdir(parents=True)
    (raw_dir / "images").mkdir(parents=True)

    split_specs = {
        "train": (6, (200, 100), [(0, 0, 20, 20), (40, 20, 140, 80)]),
        "val": (4, (400, 200), [(10, 10, 110, 110)]),
        "test": (4, (300, 300), [(0, 0, 150, 150), (150, 150, 290, 290), (20, 200, 80, 260)]),
    }

    for split, (count, (w, h), boxes) in split_specs.items():
        rows: list[str] = []
        for idx in range(count):
            img_name = f"{split}_{idx}.jpg"
            Image.new("RGB", (w, h), color=(128, 128, 128)).save(raw_dir / "images" / img_name)
            for x1, y1, x2, y2 in boxes:
                rows.append(f"{img_name},{x1},{y1},{x2},{y2},object,{w},{h}")
        (raw_dir / "annotations" / f"annotations_{split}.csv").write_text(
            "\n".join(rows) + "\n", encoding="utf-8"
        )


def test_build_subset_is_deterministic_and_creates_manifests(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _create_synthetic_raw_dataset(raw_dir)

    cfg = {
        "dataset_version": "sku110k-test-v1",
        "seed": 2026,
        "splits": {"train": 3, "val": 2, "test": 2},
    }

    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    meta_a = prepare_subset.build_subset(cfg, raw_dir=raw_dir, out_dir=out_a)
    meta_b = prepare_subset.build_subset(cfg, raw_dir=raw_dir, out_dir=out_b)

    assert meta_a["manifest_sha256"] == meta_b["manifest_sha256"]
    assert (out_a / "MANIFEST.csv").read_bytes() == (out_b / "MANIFEST.csv").read_bytes()
    assert meta_a["total_images"] == 7
    assert meta_a["splits"]["train"]["images"] == 3
    assert meta_a["splits"]["val"]["images"] == 2
    assert meta_a["splits"]["test"]["images"] == 2

    with (out_a / "manifests" / "train.csv").open("r", encoding="utf-8", newline="") as f:
        train_rows = list(csv.DictReader(f))
    assert len(train_rows) == 3
    for row in train_rows:
        stem = Path(row["image"]).stem
        assert (out_a / "images" / "train" / row["image"]).is_file()
        label_lines = (out_a / "labels" / "train" / f"{stem}.txt").read_text().splitlines()
        assert len(label_lines) == int(row["n_boxes"]) == 2


def test_build_subset_raises_when_split_too_small(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _create_synthetic_raw_dataset(raw_dir)
    cfg = {
        "dataset_version": "sku110k-test-v1",
        "seed": 2026,
        "splits": {"train": 100, "val": 2, "test": 2},
    }
    with pytest.raises(ValueError, match="requires 100 images"):
        prepare_subset.build_subset(cfg, raw_dir=raw_dir, out_dir=tmp_path / "out")


def test_run_eda_produces_summary_and_reports(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _create_synthetic_raw_dataset(raw_dir)
    out_dir = tmp_path / "subset"
    cfg = {
        "dataset_version": "sku110k-test-v1",
        "seed": 2026,
        "splits": {"train": 3, "val": 2, "test": 2},
    }
    prepare_subset.build_subset(cfg, raw_dir=raw_dir, out_dir=out_dir)

    out_md = tmp_path / "reports" / "eda.md"
    out_json = tmp_path / "reports" / "eda.json"
    report = eda.run_eda(data_dir=out_dir, out_md=out_md, out_json=out_json)

    assert report["overall"]["n_images"] == 7
    assert report["overall"]["n_boxes"] == 3 * 2 + 2 * 1 + 2 * 3
    assert report["splits"]["train"]["boxes_per_image"]["mean"] == pytest.approx(2.0)
    assert report["splits"]["val"]["image_resolution"]["width_px"]["median"] == pytest.approx(400.0)
    assert report["overall"]["bbox_size_distribution"]["pixel_area"]["count"] == 14

    assert out_md.is_file() and "Boxes per Image" in out_md.read_text(encoding="utf-8")
    loaded_json = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded_json["overall"]["n_boxes"] == 14


def test_eda_reads_image_dimensions_when_missing_from_manifest(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _create_synthetic_raw_dataset(raw_dir)
    out_dir = tmp_path / "subset"
    cfg = {
        "dataset_version": "sku110k-test-v1",
        "seed": 2026,
        "splits": {"train": 2, "val": 1, "test": 1},
    }
    prepare_subset.build_subset(cfg, raw_dir=raw_dir, out_dir=out_dir)

    # Rewrite MANIFEST.csv without image_width / image_height columns to test image fallback.
    manifest_path = out_dir / "MANIFEST.csv"
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "split", "n_boxes"], lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {"image": row["image"], "split": row["split"], "n_boxes": row["n_boxes"]}
            )

    report = eda.run_eda(data_dir=out_dir)
    assert report["splits"]["train"]["image_resolution"]["width_px"]["median"] == pytest.approx(
        200.0
    )
    assert report["splits"]["val"]["image_resolution"]["height_px"]["median"] == pytest.approx(
        200.0
    )


def test_select_split_with_exclusions_preserves_clean_base_and_backfills() -> None:
    ids = [f"img_{i:02d}.jpg" for i in range(20)]
    base = prepare_subset.sample_split(ids, 5, seed=42)
    dropped = {base[1], base[3]}

    selected = prepare_subset.select_split_with_exclusions(ids, 5, seed=42, excluded=dropped)
    assert len(selected) == 5
    # Clean base images remain in place; dropped slots are filled deterministically.
    assert [img for img in base if img not in dropped] == selected[:3]
    assert set(selected).isdisjoint(dropped)
    # Order-independent and repeatable.
    selected_rev = prepare_subset.select_split_with_exclusions(
        list(reversed(ids)), 5, seed=42, excluded=dropped
    )
    assert selected == selected_rev


def test_build_subset_with_exclude_file_prunes_stale_and_is_reproducible(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _create_synthetic_raw_dataset(raw_dir)
    out_dir = tmp_path / "subset"
    cfg = {
        "dataset_version": "sku110k-shelf-test-v2",
        "seed": 2026,
        "splits": {"train": 3, "val": 2, "test": 2},
    }

    # Build initial subset without exclusions.
    prepare_subset.build_subset(cfg, raw_dir=raw_dir, out_dir=out_dir)
    initial_train = sorted(p.name for p in (out_dir / "images" / "train").glob("*.jpg"))
    assert len(initial_train) == 3

    # Exclude one image from initial train split and rebuild into same out_dir.
    excluded_img = initial_train[0]
    exclude_csv = tmp_path / "excluded.csv"
    exclude_csv.write_text(
        f"split,image,reason\ntrain,{excluded_img},manual_review\n", encoding="utf-8"
    )

    meta_rebuilt = prepare_subset.build_subset(
        cfg, raw_dir=raw_dir, out_dir=out_dir, exclude_file=exclude_csv
    )
    rebuilt_train = sorted(p.name for p in (out_dir / "images" / "train").glob("*.jpg"))
    assert len(rebuilt_train) == 3
    assert excluded_img not in rebuilt_train
    assert not (out_dir / "labels" / "train" / f"{Path(excluded_img).stem}.txt").exists()

    # Fresh build into a clean directory must match bit-for-bit.
    fresh_dir = tmp_path / "fresh"
    meta_fresh = prepare_subset.build_subset(
        cfg, raw_dir=raw_dir, out_dir=fresh_dir, exclude_file=exclude_csv
    )
    assert meta_fresh["manifest_sha256"] == meta_rebuilt["manifest_sha256"]
    assert (fresh_dir / "MANIFEST.csv").read_bytes() == (out_dir / "MANIFEST.csv").read_bytes()
