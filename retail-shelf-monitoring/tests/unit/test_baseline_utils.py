from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


def _load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, Path(rel_path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = _load_module("baseline_common", "training/baseline/common.py")
sys.modules["common"] = common
eval_yolo26s = _load_module("eval_yolo26s", "training/baseline/eval_yolo26s.py")


def test_stratified_spike_manifest_is_deterministic_and_balanced(tmp_path: Path) -> None:
    val_csv = tmp_path / "val.csv"
    with val_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["image", "split", "n_boxes", "image_width", "image_height"],
            lineterminator="\n",
        )
        writer.writeheader()
        for i in range(100):
            writer.writerow(
                {
                    "image": f"val_{i:03d}.jpg",
                    "split": "val",
                    "n_boxes": str(50 + i * 3),
                    "image_width": "2448",
                    "image_height": "3264",
                }
            )

    out_a = tmp_path / "spike_a.csv"
    out_b = tmp_path / "spike_b.csv"
    rows_a = common.build_stratified_spike_manifest(
        val_manifest_path=val_csv, out_manifest_path=out_a, total_images=25, n_strata=5, seed=2026
    )
    rows_b = common.build_stratified_spike_manifest(
        val_manifest_path=val_csv, out_manifest_path=out_b, total_images=25, n_strata=5, seed=2026
    )

    assert len(rows_a) == 25
    assert out_a.read_bytes() == out_b.read_bytes()
    strata_counts = {
        f"Q{k}": sum(1 for r in rows_a if r["stratum"] == f"Q{k}") for k in range(1, 6)
    }
    assert all(count == 5 for count in strata_counts.values())
    assert len({r["image"] for r in rows_b}) == 25

    # Stale spike manifest referencing images no longer in val.csv must be rebuilt.
    stale_csv = tmp_path / "stale_spike.csv"
    stale_rows = [dict(r) for r in rows_a]
    stale_rows[0]["image"] = "deleted_image.jpg"
    with stale_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=common.MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(stale_rows)
    rebuilt = common.load_or_create_spike_manifest(
        val_manifest_path=val_csv,
        spike_manifest_path=stale_csv,
        total_images=25,
        n_strata=5,
        seed=2026,
    )
    assert [r["image"] for r in rebuilt] == [r["image"] for r in rows_a]


def test_load_yolo_gt_boxes_converts_normalized_to_xyxy(tmp_path: Path) -> None:
    label_path = tmp_path / "sample.txt"
    label_path.write_text("0 0.5 0.25 0.4 0.5\n", encoding="utf-8")
    boxes = common.load_yolo_gt_boxes(label_path, img_w=200, img_h=100)
    assert boxes.shape == (1, 4)
    assert boxes[0].tolist() == pytest.approx([60.0, 0.0, 140.0, 50.0])


def test_ap_metrics_perfect_and_empty_predictions() -> None:
    gt = np.array([[0.0, 0.0, 100.0, 100.0], [120.0, 0.0, 220.0, 100.0]])
    tp, scores = common.match_predictions_to_gt(gt, np.array([0.9, 0.8]), gt)
    perfect = common.compute_ap_metrics(tp, scores, total_gt=2)
    assert perfect["map50"] == pytest.approx(1.0)
    assert perfect["map50_95"] == pytest.approx(1.0)
    assert perfect["precision"] == pytest.approx(1.0)
    assert perfect["recall"] == pytest.approx(1.0)
    assert perfect["best_f1"] == pytest.approx(1.0)

    empty = common.compute_ap_metrics(
        np.zeros((0, len(common.IOU_THRESHOLDS)), dtype=bool), np.zeros((0,)), total_gt=2
    )
    assert empty["map50"] == 0.0
    assert empty["map50_95"] == 0.0
    assert empty["best_f1"] == 0.0

    # Duplicate prediction on the same GT box should count as 1 TP + 1 FP.
    dup_preds = np.array([[0.0, 0.0, 100.0, 100.0], [0.0, 0.0, 100.0, 100.0]])
    dup_tp, dup_scores = common.match_predictions_to_gt(
        dup_preds, np.array([0.95, 0.5]), np.array([[0.0, 0.0, 100.0, 100.0]])
    )
    assert dup_tp[0].all()
    assert not dup_tp[1].any()
    dup_metrics = common.compute_ap_metrics(dup_tp, dup_scores, total_gt=1)
    assert dup_metrics["map50"] == pytest.approx(1.0)
    assert dup_metrics["precision"] == pytest.approx(1.0)
    assert dup_metrics["recall"] == pytest.approx(1.0)


def test_configure_max_det_updates_final_head() -> None:
    class DummyHead:
        def __init__(self) -> None:
            self.max_det = 300

    class DummyInner:
        def __init__(self) -> None:
            self.model = [DummyHead()]

    class DummyWrapper:
        def __init__(self) -> None:
            self.model = DummyInner()

    wrapper = DummyWrapper()
    common.configure_max_det(wrapper, 1000)
    assert wrapper.model.model[-1].max_det == 1000


def test_classify_image_errors_separates_tp_dup_loc_bg_and_missed() -> None:
    gt = np.array(
        [
            [0.0, 0.0, 100.0, 100.0],  # matched by pred 0 -> TP
            [200.0, 0.0, 300.0, 100.0],  # overlapped ~0.25 IoU -> missed_loc
            [400.0, 0.0, 500.0, 100.0],  # untouched -> missed_complete
        ]
    )
    preds = np.array(
        [
            [0.0, 0.0, 100.0, 100.0],  # TP
            [0.0, 0.0, 100.0, 100.0],  # Dup
            [200.0, 0.0, 250.0, 50.0],  # IoU = 0.25 -> Loc
            [700.0, 700.0, 800.0, 800.0],  # BG
            [400.0, 0.0, 500.0, 100.0],  # Below conf_thresh -> filtered out
        ]
    )
    scores = np.array([0.9, 0.8, 0.6, 0.4, 0.1])
    res = common.classify_image_errors(preds, scores, gt, conf_thresh=0.25)
    assert res["counts"] == {
        "pred_total": 4,
        "tp": 1,
        "dup": 1,
        "loc": 1,
        "bg": 1,
        "gt_total": 3,
        "gt_matched": 1,
        "gt_missed_loc": 1,
        "gt_missed_complete": 1,
    }


def test_scale_stratum_breakdown_and_baseline_markdown() -> None:
    gt = np.array([[0.0, 0.0, 20.0, 20.0], [100.0, 0.0, 250.0, 150.0]])  # small + large @1:1
    preds = np.array([[100.0, 0.0, 250.0, 150.0]])
    scores = np.array([0.9])
    tp, sorted_scores = common.match_predictions_to_gt(preds, scores, gt)
    rec = {
        "image": "val_1.jpg",
        "stratum": "Q1",
        "img_w": 1000,
        "img_h": 1000,
        "gt_boxes": gt,
        "pred_boxes": preds,
        "pred_scores": scores,
        "tp": tp,
        "sorted_scores": sorted_scores,
    }
    scale = common.compute_scale_breakdown([rec], imgsz=1000, tile=False, best_conf=0.5)
    assert scale["small"]["gt_count"] == 1 and scale["small"]["recall_best"] == 0.0
    assert scale["large"]["gt_count"] == 1 and scale["large"]["recall_best"] == 1.0

    stratum = common.compute_stratum_breakdown([rec], best_conf=0.5)
    assert stratum["Q1"]["gt_boxes"] == 2
    assert stratum["Q1"]["recall_best"] == pytest.approx(0.5)

    summary = {
        "model": "yolo26s_1024_tile",
        "weights": "yolo26s.pt",
        "environment": {
            "git_commit": "abc1234",
            "gpu_name": "RTX 3050",
            "cpu_name": "i7",
            "torch_version": "2.15",
            "ultralytics_version": "8.4",
        },
        "dataset": {
            "dataset_version": "sku110k-shelf-v2",
            "split": "val_spike50",
            "n_images": 50,
            "seed": 2026,
            "total_gt_boxes": 7284,
        },
        "config": {
            "imgsz": 1024,
            "tile": 1024,
            "agnostic_nms": True,
            "max_det": 1000,
            "latency_conf": 0.0111,
        },
        "accuracy": {
            "map50": 0.3753,
            "map50_95": 0.1731,
            "precision": 0.3999,
            "recall": 0.5361,
            "best_f1": 0.4581,
            "best_conf_f1": 0.0111,
            "images_over_300_preds": 46,
        },
        "diagnostics": {
            "error_breakdown_best_f1": {
                "avg_pred_per_img": 195.0,
                "tp": 3905,
                "loc": 2000,
                "loc_rate": 0.2,
                "dup": 20,
                "dup_rate": 0.002,
                "bg": 3825,
                "bg_rate": 0.39,
                "recall": 0.5361,
                "precision": 0.3999,
                "gt_missed_loc": 1000,
                "missed_loc_rate": 0.137,
                "gt_missed_complete": 2379,
                "missed_complete_rate": 0.327,
            },
            "stratum_breakdown": stratum,
            "scale_breakdown": scale,
        },
        "latency_ms": {
            "cuda": {"mean": 523.2, "p95": 743.7},
            "cpu": {"mean": 4024.1, "p95": 8409.9},
        },
    }
    md = eval_yolo26s.render_baseline_markdown(summary)
    assert "`yolo26s_1024_tile`" in md
    assert "0.3753" in md
    assert "0.0111" in md
    assert "8409.9" in md
