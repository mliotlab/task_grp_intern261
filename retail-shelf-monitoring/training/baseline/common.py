"""Shared utilities and architectural diagnostics for Issue #14 baseline evaluation."""

from __future__ import annotations

import csv
import json
import os
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

BASELINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASELINE_DIR.parents[1]
REPO_ROOT = PROJECT_ROOT.parent

DEFAULT_DATA_DIR = PROJECT_ROOT / "data/sku110k_subset"
DEFAULT_VAL_MANIFEST = DEFAULT_DATA_DIR / "manifests/val.csv"
DEFAULT_SPIKE50_MANIFEST = DEFAULT_DATA_DIR / "manifests/val_spike50.csv"
DEFAULT_RESULTS_DIR = BASELINE_DIR / "results"
DEFAULT_DIAGNOSTICS_DIR = DEFAULT_RESULTS_DIR / "diagnostics"
DEFAULT_VISUALS_DIR = BASELINE_DIR / "visuals"

IOU_THRESHOLDS = np.linspace(0.50, 0.95, 10)
MANIFEST_FIELDS = ["image", "split", "n_boxes", "image_width", "image_height", "stratum"]
SCALE_BUCKETS = ("small", "medium", "large")


def build_stratified_spike_manifest(
    val_manifest_path: Path = DEFAULT_VAL_MANIFEST,
    out_manifest_path: Path = DEFAULT_SPIKE50_MANIFEST,
    total_images: int = 50,
    n_strata: int = 5,
    seed: int = 2026,
) -> list[dict[str, str]]:
    """Deterministically sample `total_images` across `n_strata` box-density quintiles."""
    if total_images <= 0 or n_strata <= 0 or total_images % n_strata != 0:
        raise ValueError(
            f"total_images ({total_images}) must be positive and "
            f"divisible by n_strata ({n_strata})."
        )
    if not val_manifest_path.is_file():
        raise FileNotFoundError(f"Validation manifest not found: '{val_manifest_path}'")

    with val_manifest_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) < total_images:
        raise ValueError(
            f"Validation manifest has {len(rows)} rows, fewer than requested {total_images}."
        )

    rows_sorted = sorted(rows, key=lambda r: (int(r["n_boxes"]), r["image"]))
    per_stratum = total_images // n_strata
    rng = np.random.default_rng(seed)

    selected: list[dict[str, str]] = []
    strata = np.array_split(np.arange(len(rows_sorted)), n_strata)
    for stratum_idx, indices in enumerate(strata, start=1):
        if len(indices) < per_stratum:
            raise ValueError(
                f"Stratum Q{stratum_idx} has only {len(indices)} images (< {per_stratum})."
            )
        chosen = sorted(rng.choice(indices, size=per_stratum, replace=False).tolist())
        for idx in chosen:
            row = dict(rows_sorted[int(idx)])
            row["stratum"] = f"Q{stratum_idx}"
            selected.append(row)

    out_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with out_manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in selected:
            writer.writerow({field: row.get(field, "") for field in MANIFEST_FIELDS})

    return selected


def read_dataset_metadata(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, Any]:
    """Read `dataset_metadata.json` from `data_dir` if present."""
    meta_path = data_dir / "dataset_metadata.json"
    if not meta_path.is_file():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def load_or_create_spike_manifest(
    val_manifest_path: Path = DEFAULT_VAL_MANIFEST,
    spike_manifest_path: Path = DEFAULT_SPIKE50_MANIFEST,
    total_images: int = 50,
    n_strata: int = 5,
    seed: int = 2026,
    *,
    force_rebuild: bool = False,
) -> list[dict[str, str]]:
    """Load `spike_manifest_path` if present and aligned with `val_manifest_path`, else rebuild."""
    if not force_rebuild and spike_manifest_path.is_file():
        with spike_manifest_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if len(rows) == total_images:
            if not val_manifest_path.is_file():
                return rows
            with val_manifest_path.open("r", encoding="utf-8", newline="") as vf:
                valid_images = {r["image"] for r in csv.DictReader(vf)}
            if all(r["image"] in valid_images for r in rows):
                return rows
    return build_stratified_spike_manifest(
        val_manifest_path=val_manifest_path,
        out_manifest_path=spike_manifest_path,
        total_images=total_images,
        n_strata=n_strata,
        seed=seed,
    )


def load_yolo_gt_boxes(label_path: Path, img_w: int, img_h: int) -> np.ndarray:
    """Load YOLO normalized labels and convert to pixel `[x1, y1, x2, y2]` float64 array."""
    if not label_path.is_file():
        return np.zeros((0, 4), dtype=np.float64)

    boxes: list[list[float]] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        cx, cy, w, h = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
        if w <= 0.0 or h <= 0.0:
            continue
        x1 = (cx - w / 2.0) * img_w
        y1 = (cy - h / 2.0) * img_h
        x2 = (cx + w / 2.0) * img_w
        y2 = (cy + h / 2.0) * img_h
        boxes.append([x1, y1, x2, y2])

    if not boxes:
        return np.zeros((0, 4), dtype=np.float64)
    return np.asarray(boxes, dtype=np.float64)


def compute_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU matrix of shape `(N, M)` for `[x1, y1, x2, y2]` boxes."""
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float64)

    ix1 = np.maximum(boxes_a[:, None, 0], boxes_b[None, :, 0])
    iy1 = np.maximum(boxes_a[:, None, 1], boxes_b[None, :, 1])
    ix2 = np.minimum(boxes_a[:, None, 2], boxes_b[None, :, 2])
    iy2 = np.minimum(boxes_a[:, None, 3], boxes_b[None, :, 3])

    inter = np.maximum(0.0, ix2 - ix1) * np.maximum(0.0, iy2 - iy1)
    area_a = np.maximum(0.0, boxes_a[:, 2] - boxes_a[:, 0]) * np.maximum(
        0.0, boxes_a[:, 3] - boxes_a[:, 1]
    )
    area_b = np.maximum(0.0, boxes_b[:, 2] - boxes_b[:, 0]) * np.maximum(
        0.0, boxes_b[:, 3] - boxes_b[:, 1]
    )
    union = area_a[:, None] + area_b[None, :] - inter
    return np.where(union > 0.0, inter / union, 0.0)


def match_predictions_to_gt(
    pred_boxes: np.ndarray,
    pred_scores: np.ndarray,
    gt_boxes: np.ndarray,
    iou_thresholds: np.ndarray = IOU_THRESHOLDS,
) -> tuple[np.ndarray, np.ndarray]:
    """Greedy confidence-ordered 1-to-1 matching across IoU thresholds.

    Returns `(tp_matrix, sorted_scores)` where `tp_matrix` has shape `(N, T)`.
    """
    n_preds = len(pred_boxes)
    n_thresholds = len(iou_thresholds)
    if n_preds == 0:
        return np.zeros((0, n_thresholds), dtype=bool), np.zeros((0,), dtype=np.float64)

    order = np.argsort(-pred_scores, kind="stable")
    sorted_boxes = pred_boxes[order]
    sorted_scores = pred_scores[order]
    tp = np.zeros((n_preds, n_thresholds), dtype=bool)

    if len(gt_boxes) == 0:
        return tp, sorted_scores

    ious = compute_iou_matrix(sorted_boxes, gt_boxes)
    for t_idx, thr in enumerate(iou_thresholds):
        unmatched = np.ones(len(gt_boxes), dtype=bool)
        for p_idx in range(n_preds):
            if not np.any(unmatched):
                break
            row = np.where(unmatched, ious[p_idx], -1.0)
            best_gt = int(np.argmax(row))
            if row[best_gt] >= thr:
                tp[p_idx, t_idx] = True
                unmatched[best_gt] = False

    return tp, sorted_scores


def _coco_101_ap(recall: np.ndarray, precision: np.ndarray) -> float:
    """Compute COCO 101-point interpolated Average Precision."""
    if len(recall) == 0:
        return 0.0
    mpre = np.flip(np.maximum.accumulate(np.flip(precision)))
    recall_thresholds = np.linspace(0.0, 1.0, 101)
    indices = np.searchsorted(recall, recall_thresholds, side="left")
    interpolated = np.where(indices < len(mpre), mpre[np.minimum(indices, len(mpre) - 1)], 0.0)
    return float(np.mean(interpolated))


def compute_ap_metrics(
    tp_matrix: np.ndarray,
    scores: np.ndarray,
    total_gt: int,
) -> dict[str, float]:
    """Compute COCO-style single-class mAP@0.5, mAP@0.5:0.95, max-F1 Precision and Recall."""
    if len(scores) == 0 or total_gt <= 0:
        return {
            "map50": 0.0,
            "map50_95": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "best_f1": 0.0,
            "best_conf_f1": 0.0,
        }

    order = np.argsort(-scores, kind="stable")
    tp_sorted = tp_matrix[order]
    scores_sorted = scores[order]

    aps: list[float] = []
    prec_50 = np.zeros(len(scores_sorted), dtype=np.float64)
    rec_50 = np.zeros(len(scores_sorted), dtype=np.float64)

    for t_idx in range(tp_sorted.shape[1]):
        tpc = np.cumsum(tp_sorted[:, t_idx].astype(np.float64))
        fpc = np.cumsum((~tp_sorted[:, t_idx]).astype(np.float64))
        rec = tpc / float(total_gt)
        prec = tpc / np.maximum(tpc + fpc, 1e-16)
        aps.append(_coco_101_ap(rec, prec))
        if t_idx == 0:
            prec_50 = prec
            rec_50 = rec

    f1 = 2.0 * prec_50 * rec_50 / np.maximum(prec_50 + rec_50, 1e-16)
    best_idx = int(np.argmax(f1))

    return {
        "map50": round(float(aps[0]), 4),
        "map50_95": round(float(np.mean(aps)), 4),
        "precision": round(float(prec_50[best_idx]), 4),
        "recall": round(float(rec_50[best_idx]), 4),
        "best_f1": round(float(f1[best_idx]), 4),
        "best_conf_f1": round(float(scores_sorted[best_idx]), 4),
    }


def classify_image_errors(
    pred_boxes: np.ndarray,
    pred_scores: np.ndarray,
    gt_boxes: np.ndarray,
    *,
    conf_thresh: float = 0.25,
    iou_tp: float = 0.50,
    iou_loc: float = 0.10,
) -> dict[str, Any]:
    """Decompose single-image predictions and GTs into TIDE-style geometric error buckets."""
    keep = pred_scores >= conf_thresh
    kept_boxes = pred_boxes[keep]
    kept_scores = pred_scores[keep]
    order = np.argsort(-kept_scores, kind="stable")
    sorted_boxes = kept_boxes[order]
    sorted_scores = kept_scores[order]

    n_preds = len(sorted_boxes)
    n_gt = len(gt_boxes)
    pred_labels: list[str] = []
    gt_matched = np.zeros(n_gt, dtype=bool)
    gt_max_iou = np.zeros(n_gt, dtype=np.float64)

    if n_preds > 0 and n_gt > 0:
        ious = compute_iou_matrix(sorted_boxes, gt_boxes)
        gt_max_iou = ious.max(axis=0)
        for p_idx in range(n_preds):
            row = ious[p_idx]
            unmatched_row = np.where(~gt_matched, row, -1.0)
            best_unmatched = int(np.argmax(unmatched_row))
            if unmatched_row[best_unmatched] >= iou_tp:
                gt_matched[best_unmatched] = True
                pred_labels.append("tp")
                continue
            max_iou = float(row.max())
            if max_iou >= iou_tp:
                pred_labels.append("dup")
            elif max_iou >= iou_loc:
                pred_labels.append("loc")
            else:
                pred_labels.append("bg")
    else:
        pred_labels = ["bg"] * n_preds

    gt_labels: list[str] = []
    for g_idx in range(n_gt):
        if gt_matched[g_idx]:
            gt_labels.append("matched")
        elif gt_max_iou[g_idx] >= iou_loc:
            gt_labels.append("missed_loc")
        else:
            gt_labels.append("missed_complete")

    counts = {
        "pred_total": n_preds,
        "tp": sum(1 for lbl in pred_labels if lbl == "tp"),
        "dup": sum(1 for lbl in pred_labels if lbl == "dup"),
        "loc": sum(1 for lbl in pred_labels if lbl == "loc"),
        "bg": sum(1 for lbl in pred_labels if lbl == "bg"),
        "gt_total": n_gt,
        "gt_matched": sum(1 for lbl in gt_labels if lbl == "matched"),
        "gt_missed_loc": sum(1 for lbl in gt_labels if lbl == "missed_loc"),
        "gt_missed_complete": sum(1 for lbl in gt_labels if lbl == "missed_complete"),
    }
    return {
        "counts": counts,
        "sorted_boxes": sorted_boxes,
        "sorted_scores": sorted_scores,
        "pred_labels": pred_labels,
        "gt_labels": gt_labels,
        "gt_matched_mask": gt_matched,
    }


def _aggregate_error_counts(image_errors: list[dict[str, int]]) -> dict[str, Any]:
    keys = (
        "pred_total",
        "tp",
        "dup",
        "loc",
        "bg",
        "gt_total",
        "gt_matched",
        "gt_missed_loc",
        "gt_missed_complete",
    )
    totals = {k: sum(item[k] for item in image_errors) for k in keys}
    pred_total = max(totals["pred_total"], 1)
    gt_total = max(totals["gt_total"], 1)
    n_imgs = max(len(image_errors), 1)
    return {
        **totals,
        "avg_pred_per_img": round(totals["pred_total"] / n_imgs, 1),
        "precision": round(totals["tp"] / pred_total, 4) if totals["pred_total"] else 0.0,
        "recall": round(totals["gt_matched"] / gt_total, 4) if totals["gt_total"] else 0.0,
        "dup_rate": round(totals["dup"] / pred_total, 4) if totals["pred_total"] else 0.0,
        "loc_rate": round(totals["loc"] / pred_total, 4) if totals["pred_total"] else 0.0,
        "bg_rate": round(totals["bg"] / pred_total, 4) if totals["pred_total"] else 0.0,
        "missed_loc_rate": round(totals["gt_missed_loc"] / gt_total, 4),
        "missed_complete_rate": round(totals["gt_missed_complete"] / gt_total, 4),
    }


def compute_effective_scale(img_w: int, img_h: int, imgsz: int, tile: bool | int = False) -> float:
    """Compute pixel scaling factor from source image into the model's input space."""
    if tile:
        tile_px = imgsz if tile is True else int(tile)
        return min(1.0, float(imgsz) / max(float(tile_px), 1.0))
    return min(1.0, float(imgsz) / max(float(img_w), float(img_h), 1.0))


def compute_scale_breakdown(
    image_records: list[dict[str, Any]],
    imgsz: int,
    tile: bool | int = False,
    *,
    best_conf: float | None = None,
) -> dict[str, dict[str, Any]]:
    """Measure Recall and localization-hit rates across network-input GT pixel area buckets."""
    buckets: dict[str, dict[str, int]] = {
        name: {
            "gt_count": 0,
            "hit_001": 0,
            "hit_best": 0,
            "hit_005": 0,
            "hit_025": 0,
            "loc_or_tp_best": 0,
            "loc_or_tp_005": 0,
        }
        for name in SCALE_BUCKETS
    }
    total_gt = 0

    for rec in image_records:
        gt_boxes = rec["gt_boxes"]
        if len(gt_boxes) == 0:
            continue
        total_gt += len(gt_boxes)
        scale = compute_effective_scale(rec["img_w"], rec["img_h"], imgsz=imgsz, tile=tile)
        areas = ((gt_boxes[:, 2] - gt_boxes[:, 0]) * scale) * (
            (gt_boxes[:, 3] - gt_boxes[:, 1]) * scale
        )

        err_001 = classify_image_errors(
            rec["pred_boxes"], rec["pred_scores"], gt_boxes, conf_thresh=0.001
        )
        err_best = (
            classify_image_errors(
                rec["pred_boxes"], rec["pred_scores"], gt_boxes, conf_thresh=best_conf
            )
            if best_conf is not None
            else None
        )
        err_005 = classify_image_errors(
            rec["pred_boxes"], rec["pred_scores"], gt_boxes, conf_thresh=0.05
        )
        err_025 = classify_image_errors(
            rec["pred_boxes"], rec["pred_scores"], gt_boxes, conf_thresh=0.25
        )

        for g_idx, area in enumerate(areas):
            if area < 32.0 * 32.0:
                bname = "small"
            elif area < 96.0 * 96.0:
                bname = "medium"
            else:
                bname = "large"

            bucket = buckets[bname]
            bucket["gt_count"] += 1
            if err_001["gt_matched_mask"][g_idx]:
                bucket["hit_001"] += 1
            if err_best is not None:
                if err_best["gt_matched_mask"][g_idx]:
                    bucket["hit_best"] += 1
                if err_best["gt_labels"][g_idx] in {"matched", "missed_loc"}:
                    bucket["loc_or_tp_best"] += 1
            if err_005["gt_matched_mask"][g_idx]:
                bucket["hit_005"] += 1
            if err_025["gt_matched_mask"][g_idx]:
                bucket["hit_025"] += 1
            if err_005["gt_labels"][g_idx] in {"matched", "missed_loc"}:
                bucket["loc_or_tp_005"] += 1

    summary: dict[str, dict[str, Any]] = {}
    for name, b in buckets.items():
        cnt = b["gt_count"]
        entry: dict[str, Any] = {
            "gt_count": cnt,
            "gt_pct": round(100.0 * cnt / total_gt, 2) if total_gt else 0.0,
            "recall_001": round(b["hit_001"] / cnt, 4) if cnt else 0.0,
            "recall_005": round(b["hit_005"] / cnt, 4) if cnt else 0.0,
            "recall_025": round(b["hit_025"] / cnt, 4) if cnt else 0.0,
            "loc_or_tp_005": round(b["loc_or_tp_005"] / cnt, 4) if cnt else 0.0,
        }
        if best_conf is not None:
            entry["recall_best"] = round(b["hit_best"] / cnt, 4) if cnt else 0.0
            entry["loc_or_tp_best"] = round(b["loc_or_tp_best"] / cnt, 4) if cnt else 0.0
        summary[name] = entry
    return summary


def compute_stratum_breakdown(
    image_records: list[dict[str, Any]],
    *,
    best_conf: float | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute mAP, prediction counts, and error rates grouped by density stratum (`Q1`..`Q5`)."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rec in image_records:
        grouped.setdefault(str(rec.get("stratum") or "unknown"), []).append(rec)

    breakdown: dict[str, dict[str, Any]] = {}
    for stratum in sorted(grouped):
        recs = grouped[stratum]
        tp_chunks = [r["tp"] for r in recs]
        score_chunks = [r["sorted_scores"] for r in recs]
        all_tp = (
            np.vstack(tp_chunks) if tp_chunks else np.zeros((0, len(IOU_THRESHOLDS)), dtype=bool)
        )
        all_scores = (
            np.concatenate(score_chunks) if score_chunks else np.zeros((0,), dtype=np.float64)
        )
        gt_total = sum(len(r["gt_boxes"]) for r in recs)
        ap = compute_ap_metrics(all_tp, all_scores, gt_total)

        err_best = (
            _aggregate_error_counts(
                [
                    classify_image_errors(
                        r["pred_boxes"], r["pred_scores"], r["gt_boxes"], conf_thresh=best_conf
                    )["counts"]
                    for r in recs
                ]
            )
            if best_conf is not None
            else None
        )
        err_005 = _aggregate_error_counts(
            [
                classify_image_errors(
                    r["pred_boxes"], r["pred_scores"], r["gt_boxes"], conf_thresh=0.05
                )["counts"]
                for r in recs
            ]
        )
        err_025 = _aggregate_error_counts(
            [
                classify_image_errors(
                    r["pred_boxes"], r["pred_scores"], r["gt_boxes"], conf_thresh=0.25
                )["counts"]
                for r in recs
            ]
        )
        gt_counts = [len(r["gt_boxes"]) for r in recs]
        pred_counts_001 = [len(r["pred_boxes"]) for r in recs]

        entry: dict[str, Any] = {
            "n_images": len(recs),
            "gt_boxes": gt_total,
            "gt_min": min(gt_counts) if gt_counts else 0,
            "gt_max": max(gt_counts) if gt_counts else 0,
            "map50": ap["map50"],
            "map50_95": ap["map50_95"],
            "avg_pred_001": round(float(np.mean(pred_counts_001)), 1) if pred_counts_001 else 0.0,
            "avg_pred_025": err_025["avg_pred_per_img"],
            "recall_005": err_005["recall"],
            "recall_025": err_025["recall"],
            "precision_025": err_025["precision"],
            "loc_rate_025": err_025["loc_rate"],
            "bg_rate_025": err_025["bg_rate"],
        }
        if err_best is not None:
            entry["avg_pred_best"] = err_best["avg_pred_per_img"]
            entry["recall_best"] = err_best["recall"]
            entry["precision_best"] = err_best["precision"]
            entry["loc_rate_best"] = err_best["loc_rate"]
            entry["bg_rate_best"] = err_best["bg_rate"]
        breakdown[stratum] = entry
    return breakdown


def _read_git_commit(repo_root: Path = REPO_ROOT) -> str:
    head_file = repo_root / ".git" / "HEAD"
    if not head_file.is_file():
        return "unknown"
    head_text = head_file.read_text(encoding="utf-8").strip()
    if head_text.startswith("ref: "):
        ref_path = repo_root / ".git" / head_text.removeprefix("ref: ").strip()
        if ref_path.is_file():
            return ref_path.read_text(encoding="utf-8").strip()[:7]
    return head_text[:7]


def collect_environment_metadata() -> dict[str, Any]:
    """Gather hardware, OS, Python, and ML runtime metadata for reproducible reports."""
    meta: dict[str, Any] = {
        "git_commit": _read_git_commit(),
        "platform": platform.platform(),
        "cpu_name": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
        "python_version": platform.python_version(),
        "torch_version": "not_installed",
        "cuda_available": False,
        "gpu_name": "N/A",
        "ultralytics_version": "not_installed",
    }

    try:
        import torch

        meta["torch_version"] = torch.__version__
        meta["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            meta["gpu_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    try:
        import ultralytics

        meta["ultralytics_version"] = ultralytics.__version__
    except ImportError:
        pass

    return meta


def configure_max_det(model: Any, max_det: int) -> None:
    """Set `max_det` on the final Ultralytics detection/segmentation head."""
    inner = getattr(model, "model", model)
    layers = getattr(inner, "model", inner)
    head = layers[-1]
    if hasattr(head, "max_det"):
        head.max_det = max_det


def _summarize_latencies(latencies_ms: list[float]) -> dict[str, float]:
    arr = np.asarray(latencies_ms, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": round(float(arr.mean()), 2),
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "min": round(float(arr.min()), 2),
        "max": round(float(arr.max()), 2),
    }


def _run_single_predict(
    model: Any,
    image_path: Path,
    imgsz: int,
    conf: float,
    max_det: int,
    device: str,
    end2end: bool,
    *,
    agnostic_nms: bool = False,
    tile: bool | int = False,
    iou: float | None = None,
) -> Any:
    """Execute one Ultralytics prediction call with `nms` mapped from `end2end`."""
    import torch

    kwargs: dict[str, Any] = {
        "source": str(image_path),
        "imgsz": imgsz,
        "conf": conf,
        "max_det": max_det,
        "device": device,
        "nms": not end2end,
        "agnostic_nms": agnostic_nms,
        "verbose": False,
    }
    if tile:
        kwargs["tile"] = tile
        kwargs["iou"] = 0.5 if iou is None else iou
    elif iou is not None:
        kwargs["iou"] = iou

    with torch.inference_mode():
        return model.predict(**kwargs)


def _predict_boxes(
    model: Any,
    image_path: Path,
    imgsz: int,
    conf: float,
    max_det: int,
    device: str,
    end2end: bool,
    *,
    agnostic_nms: bool = False,
    tile: bool | int = False,
    iou: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Run Ultralytics prediction and return class-agnostic `(xyxy, conf)` arrays."""
    configure_max_det(model, max_det)
    results = _run_single_predict(
        model,
        image_path,
        imgsz,
        conf,
        max_det,
        device,
        end2end,
        agnostic_nms=agnostic_nms,
        tile=tile,
        iou=iou,
    )
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return np.zeros((0, 4), dtype=np.float64), np.zeros((0,), dtype=np.float64)
    return (
        boxes.xyxy.detach().cpu().numpy().astype(np.float64),
        boxes.conf.detach().cpu().numpy().astype(np.float64),
    )


def _measure_device_latency(
    model: Any,
    image_paths: list[Path],
    imgsz: int,
    conf: float,
    max_det: int,
    device: str,
    end2end: bool,
    *,
    agnostic_nms: bool = False,
    tile: bool | int = False,
    iou: float | None = None,
    warmup: int = 5,
) -> dict[str, float]:
    import torch

    configure_max_det(model, max_det)
    is_cuda = device.startswith("cuda")
    label = "cuda" if is_cuda else "cpu"
    print(
        f"[{label} latency] warmup={min(warmup, len(image_paths))}, "
        f"n={len(image_paths)}, conf={conf:.4f}",
        flush=True,
    )

    for path in image_paths[:warmup]:
        _run_single_predict(
            model,
            path,
            imgsz,
            conf,
            max_det,
            device,
            end2end,
            agnostic_nms=agnostic_nms,
            tile=tile,
            iou=iou,
        )
    if is_cuda:
        torch.cuda.synchronize()

    latencies_ms: list[float] = []
    total = len(image_paths)
    for idx, path in enumerate(image_paths, start=1):
        if is_cuda:
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        _run_single_predict(
            model,
            path,
            imgsz,
            conf,
            max_det,
            device,
            end2end,
            agnostic_nms=agnostic_nms,
            tile=tile,
            iou=iou,
        )
        if is_cuda:
            torch.cuda.synchronize()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)
        if idx % 10 == 0 or idx == total:
            print(
                f"[{label} latency] {idx}/{total} (last={elapsed_ms:.1f}ms, "
                f"mean={float(np.mean(latencies_ms)):.1f}ms)",
                flush=True,
            )

    return _summarize_latencies(latencies_ms)


def export_diagnostic_visuals(
    image_records: list[dict[str, Any]],
    out_dir: Path,
    *,
    conf_thresh: float = 0.25,
    max_side: int = 1400,
) -> list[dict[str, Any]]:
    """Render GT vs prediction error overlays for visual inspection (Issue #14 / #15)."""
    import cv2

    out_dir.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, Any]] = []

    color_map = {
        "tp": (40, 200, 60),
        "loc": (0, 175, 255),
        "dup": (255, 210, 40),
        "bg": (220, 60, 220),
        "missed": (40, 40, 235),
    }

    for rec in image_records:
        img = cv2.imread(str(rec["image_path"]))
        if img is None:
            raise FileNotFoundError(f"Could not read image '{rec['image_path']}'")

        h, w = img.shape[:2]
        scale = min(1.0, float(max_side) / max(h, w))
        if scale < 1.0:
            img = cv2.resize(
                img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA
            )

        diag = classify_image_errors(
            rec["pred_boxes"],
            rec["pred_scores"],
            rec["gt_boxes"],
            conf_thresh=conf_thresh,
        )

        # Draw missed GT boxes first so matched/error predictions stay visible on top.
        for g_box, g_lbl in zip(rec["gt_boxes"], diag["gt_labels"], strict=True):
            if g_lbl != "matched":
                x1, y1, x2, y2 = (round(v * scale) for v in g_box)
                cv2.rectangle(img, (x1, y1), (x2, y2), color_map["missed"], 2)

        for p_box, p_lbl in zip(diag["sorted_boxes"], diag["pred_labels"], strict=True):
            x1, y1, x2, y2 = (round(v * scale) for v in p_box)
            cv2.rectangle(img, (x1, y1), (x2, y2), color_map[p_lbl], 2)

        banner_h = 54
        canvas = np.full((img.shape[0] + banner_h, img.shape[1], 3), 24, dtype=np.uint8)
        canvas[banner_h:] = img

        counts = diag["counts"]
        missed_total = counts["gt_missed_loc"] + counts["gt_missed_complete"]
        conf_str = f"{conf_thresh:.4f}" if conf_thresh < 0.05 else f"{conf_thresh:.2f}"
        header = (
            f"{rec['image']} ({rec['stratum']}) | GT:{counts['gt_total']} | "
            f"TP:{counts['tp']} Loc:{counts['loc']} Dup:{counts['dup']} "
            f"BG_FP:{counts['bg']} Missed:{missed_total} @conf>={conf_str}"
        )
        cv2.putText(
            canvas,
            header,
            (12, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (245, 245, 245),
            1,
            cv2.LINE_AA,
        )
        legend = "GREEN=TP  ORANGE=Loc(0.1-0.5)  MAGENTA=BG_FP(<0.1)  CYAN=Dup  RED=Missed_GT"
        cv2.putText(
            canvas,
            legend,
            (12, 44),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (205, 205, 205),
            1,
            cv2.LINE_AA,
        )

        out_path = out_dir / f"{Path(rec['image']).stem}_diag.jpg"
        cv2.imwrite(str(out_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])
        try:
            rel_out = out_path.relative_to(BASELINE_DIR).as_posix()
        except ValueError:
            rel_out = out_path.as_posix()
        exported.append(
            {
                "image": rec["image"],
                "stratum": rec["stratum"],
                "out_path": rel_out,
                "counts": counts,
            }
        )

    return exported


def run_baseline_evaluation(
    model_name: str,
    weights: str,
    model_loader: Any,
    out_json: Path,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    val_manifest_path: Path = DEFAULT_VAL_MANIFEST,
    spike_manifest_path: Path = DEFAULT_SPIKE50_MANIFEST,
    total_images: int = 50,
    force_rebuild_spike: bool = False,
    imgsz: int = 1024,
    eval_conf: float = 0.001,
    latency_conf: float | None = None,
    max_det: int = 1000,
    end2end: bool = True,
    agnostic_nms: bool = False,
    tile: bool | int = False,
    iou: float | None = None,
    prompts: list[str] | None = None,
    notes: str = "",
    measure_cpu: bool = True,
    return_records: bool = False,
) -> dict[str, Any] | tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run class-agnostic accuracy, diagnostics, and GPU/CPU latency on the stratified val spike."""
    import torch

    rows = load_or_create_spike_manifest(
        val_manifest_path=val_manifest_path,
        spike_manifest_path=spike_manifest_path,
        total_images=total_images,
        force_rebuild=force_rebuild_spike,
    )
    image_paths = [data_dir / "images" / r["split"] / r["image"] for r in rows]
    for img_path in image_paths:
        if not img_path.is_file():
            raise FileNotFoundError(f"Missing image: '{img_path}'")

    eval_device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model = model_loader(weights, prompts)
    configure_max_det(model, max_det)

    tp_chunks: list[np.ndarray] = []
    score_chunks: list[np.ndarray] = []
    pred_counts: list[int] = []
    image_records: list[dict[str, Any]] = []
    total_gt = 0
    total_imgs = len(rows)
    print(f"[eval] running {model_name} on {total_imgs} images ({eval_device})...", flush=True)

    for idx, (row, img_path) in enumerate(zip(rows, image_paths, strict=True), start=1):
        img_w = int(row["image_width"])
        img_h = int(row["image_height"])
        label_path = data_dir / "labels" / row["split"] / f"{Path(row['image']).stem}.txt"
        gt_boxes = load_yolo_gt_boxes(label_path, img_w, img_h)
        total_gt += len(gt_boxes)

        pred_boxes, pred_scores = _predict_boxes(
            model,
            img_path,
            imgsz=imgsz,
            conf=eval_conf,
            max_det=max_det,
            device=eval_device,
            end2end=end2end,
            agnostic_nms=agnostic_nms,
            tile=tile,
            iou=iou,
        )
        pred_counts.append(len(pred_boxes))
        tp, sorted_scores = match_predictions_to_gt(pred_boxes, pred_scores, gt_boxes)
        tp_chunks.append(tp)
        score_chunks.append(sorted_scores)
        image_records.append(
            {
                "image": row["image"],
                "stratum": row.get("stratum", ""),
                "image_path": img_path,
                "img_w": img_w,
                "img_h": img_h,
                "gt_boxes": gt_boxes,
                "pred_boxes": pred_boxes,
                "pred_scores": pred_scores,
                "tp": tp,
                "sorted_scores": sorted_scores,
            }
        )
        if idx % 10 == 0 or idx == total_imgs:
            print(f"[eval] {idx}/{total_imgs} images processed", flush=True)

    all_tp = np.vstack(tp_chunks) if tp_chunks else np.zeros((0, len(IOU_THRESHOLDS)), dtype=bool)
    all_scores = np.concatenate(score_chunks) if score_chunks else np.zeros((0,), dtype=np.float64)
    ap_metrics = compute_ap_metrics(all_tp, all_scores, total_gt)
    best_conf = ap_metrics["best_conf_f1"]
    resolved_latency_conf = (
        latency_conf if latency_conf is not None else (best_conf if best_conf > 0 else 0.25)
    )
    print(
        f"[eval] done: mAP@0.5={ap_metrics['map50']:.4f}, "
        f"mAP@0.5:0.95={ap_metrics['map50_95']:.4f}, "
        f"best_conf_f1={best_conf:.4f} (F1={ap_metrics['best_f1']:.4f})",
        flush=True,
    )

    err_best = _aggregate_error_counts(
        [
            classify_image_errors(
                r["pred_boxes"], r["pred_scores"], r["gt_boxes"], conf_thresh=best_conf
            )["counts"]
            for r in image_records
        ]
    )
    err_005 = _aggregate_error_counts(
        [
            classify_image_errors(
                r["pred_boxes"], r["pred_scores"], r["gt_boxes"], conf_thresh=0.05
            )["counts"]
            for r in image_records
        ]
    )
    err_025 = _aggregate_error_counts(
        [
            classify_image_errors(
                r["pred_boxes"], r["pred_scores"], r["gt_boxes"], conf_thresh=0.25
            )["counts"]
            for r in image_records
        ]
    )
    stratum_breakdown = compute_stratum_breakdown(image_records, best_conf=best_conf)
    scale_breakdown = compute_scale_breakdown(
        image_records, imgsz=imgsz, tile=tile, best_conf=best_conf
    )

    latency_results: dict[str, dict[str, float]] = {}
    if torch.cuda.is_available():
        latency_results["cuda"] = _measure_device_latency(
            model,
            image_paths,
            imgsz=imgsz,
            conf=resolved_latency_conf,
            max_det=max_det,
            device="cuda:0",
            end2end=end2end,
            agnostic_nms=agnostic_nms,
            tile=tile,
            iou=iou,
        )
    if measure_cpu:
        cpu_model = model_loader(weights, prompts)
        configure_max_det(cpu_model, max_det)
        latency_results["cpu"] = _measure_device_latency(
            cpu_model,
            image_paths,
            imgsz=imgsz,
            conf=resolved_latency_conf,
            max_det=max_det,
            device="cpu",
            end2end=end2end,
            agnostic_nms=agnostic_nms,
            tile=tile,
            iou=iou,
        )

    dataset_meta = read_dataset_metadata(data_dir)
    try:
        manifest_rel = spike_manifest_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        manifest_rel = spike_manifest_path.as_posix()

    dataset_info: dict[str, Any] = {
        "dataset_version": str(dataset_meta.get("dataset_version", "unknown")),
        "split": spike_manifest_path.stem,
        "seed": int(dataset_meta.get("seed", 2026)),
        "manifest_path": manifest_rel,
        "n_images": len(rows),
        "total_gt_boxes": total_gt,
    }
    if "manifest_sha256" in dataset_meta:
        dataset_info["manifest_sha256"] = str(dataset_meta["manifest_sha256"])

    summary = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": model_name,
        "weights": weights,
        "environment": collect_environment_metadata(),
        "dataset": dataset_info,
        "config": {
            "imgsz": imgsz,
            "eval_conf": eval_conf,
            "latency_conf": resolved_latency_conf,
            "max_det": max_det,
            "end2end": end2end,
            "agnostic_nms": agnostic_nms,
            "tile": tile,
            "iou": iou,
            "eval_device": eval_device,
            "prompts": prompts,
        },
        "accuracy": {
            **ap_metrics,
            "avg_pred_boxes": round(float(np.mean(pred_counts)), 1) if pred_counts else 0.0,
            "avg_pred_boxes_best_f1": err_best["avg_pred_per_img"],
            "avg_pred_boxes_005": err_005["avg_pred_per_img"],
            "avg_pred_boxes_025": err_025["avg_pred_per_img"],
            "max_pred_boxes": max(pred_counts) if pred_counts else 0,
            "images_over_300_preds": sum(1 for c in pred_counts if c > 300),
        },
        "diagnostics": {
            "error_breakdown_best_f1": err_best,
            "error_breakdown_005": err_005,
            "error_breakdown_025": err_025,
            "stratum_breakdown": stratum_breakdown,
            "scale_breakdown": scale_breakdown,
        },
        "latency_ms": latency_results,
        "notes": notes,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    if return_records:
        return summary, image_records
    return summary
