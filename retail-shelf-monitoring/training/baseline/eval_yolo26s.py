"""Baseline evaluation script for pretrained Ultralytics YOLO26s (Issue #14).

python training/baseline/eval_yolo26s.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import (
    BASELINE_DIR,
    DEFAULT_DATA_DIR,
    DEFAULT_RESULTS_DIR,
    DEFAULT_SPIKE50_MANIFEST,
    DEFAULT_VAL_MANIFEST,
    DEFAULT_VISUALS_DIR,
    export_diagnostic_visuals,
    run_baseline_evaluation,
)


def load_yolo26s(weights: str, _prompts: list[str] | None = None):
    """Load pretrained YOLO26s detection weights."""
    from ultralytics import YOLO

    return YOLO(weights)


def _fmt_float(value: float | None, digits: int = 4) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _fmt_ms(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}"


def _rel_visual_link(path_str: str) -> str:
    rel = Path(path_str)
    try:
        rel_disp = rel.relative_to(BASELINE_DIR).as_posix()
    except ValueError:
        rel_disp = rel.as_posix()
    return f"[{rel.name}]({rel_disp})"


def render_baseline_markdown(
    summary: dict[str, Any],
    visual_exports: list[dict[str, Any]] | None = None,
    *,
    visual_conf: float | None = None,
) -> str:
    """Render local inspection Markdown report for the YOLO26s baseline run."""
    env = summary.get("environment", {})
    dataset = summary.get("dataset", {})
    cfg = summary.get("config", {})
    acc = summary.get("accuracy", {})
    diag = summary.get("diagnostics", {})
    lat = summary.get("latency_ms", {})
    gpu = lat.get("cuda", {})
    cpu = lat.get("cpu", {})

    n_imgs = dataset.get("n_images", 50)
    best_conf = acc.get("best_conf_f1", 0.0)
    vis_conf = best_conf if visual_conf is None else visual_conf
    vis_conf_str = f"{vis_conf:.4f}" if vis_conf < 0.05 else f"{vis_conf:.2f}"

    lines: list[str] = [
        f"# Pretrained Baseline Local Report – `{summary['model']}`",
        "",
        "## 1. Dataset & Environment",
        "",
        f"- **Dataset:** `{dataset.get('dataset_version', 'unknown')}` · "
        f"`{dataset.get('split', 'val_spike50')}` ({n_imgs} ảnh phân tầng `Q1`–`Q5`, "
        f"`seed={dataset.get('seed', 2026)}`, tổng `{dataset.get('total_gt_boxes', 0)}` GT boxes)",
        f"- **Commit:** `{env.get('git_commit', 'unknown')}` · "
        f"**PyTorch:** `{env.get('torch_version', '—')}` · "
        f"**Ultralytics:** `{env.get('ultralytics_version', '—')}`",
        f"- **GPU:** `{env.get('gpu_name', 'N/A')}` · **CPU:** `{env.get('cpu_name', 'N/A')}`",
        "",
        "## 2. Accuracy & Latency Summary",
        "",
        "| Model | imgsz | tile | agnostic | max_det | mAP@0.5 | mAP@0.5:0.95 | "
        "Best Conf (F1) | P / R / F1 | Imgs >300 | GPU mean / p95 | CPU mean / p95 |",
        "|---|---:|:---:|:---:|---:|---:|---:|---:|---|---:|---|---|",
        f"| `{summary['model']}` | {cfg.get('imgsz', '—')} | `{cfg.get('tile', False)}` "
        f"| `{cfg.get('agnostic_nms', False)}` | {cfg.get('max_det', '—')} "
        f"| **{_fmt_float(acc.get('map50'))}** | {_fmt_float(acc.get('map50_95'))} "
        f"| `{_fmt_float(best_conf)}` "
        f"| {_fmt_float(acc.get('precision'), 3)} / {_fmt_float(acc.get('recall'), 3)} "
        f"/ {_fmt_float(acc.get('best_f1'), 3)} "
        f"| {acc.get('images_over_300_preds', '—')} "
        f"| {_fmt_ms(gpu.get('mean'))} / {_fmt_ms(gpu.get('p95'))} ms "
        f"| {_fmt_ms(cpu.get('mean'))} / {_fmt_ms(cpu.get('p95'))} ms |",
        "",
        f"> Latency benchmarked at `conf={_fmt_float(cfg.get('latency_conf'))}`, "
        "`batch=1`, warmup 5 images (NFR-03 target: GPU p95 ≤ 2000 ms, CPU p95 ≤ 5000 ms).",
        "",
        "## 3. TIDE-Style Geometric Error Breakdown (Class-Agnostic)",
        "",
        "| Threshold | Pred/img | TP | Loc (`0.1-0.5`) | Dup | BG FP (`<0.1`) | "
        "Recall@0.5 | Precision | Missed-Loc | Missed-Complete |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    threshold_rows = [
        (f"**Best F1 (`{best_conf:.4f}`)**", diag.get("error_breakdown_best_f1")),
        ("`conf = 0.05`", diag.get("error_breakdown_005")),
        ("`conf = 0.25`", diag.get("error_breakdown_025")),
    ]
    for label, err in threshold_rows:
        if not err:
            continue
        lines.append(
            f"| {label} "
            f"| {err.get('avg_pred_per_img', '—')} "
            f"| {err.get('tp', '—')} "
            f"| {err.get('loc', '—')} ({_fmt_pct(err.get('loc_rate'))}) "
            f"| {err.get('dup', '—')} ({_fmt_pct(err.get('dup_rate'))}) "
            f"| {err.get('bg', '—')} ({_fmt_pct(err.get('bg_rate'))}) "
            f"| {_fmt_pct(err.get('recall'))} "
            f"| {_fmt_pct(err.get('precision'))} "
            f"| {err.get('gt_missed_loc', '—')} ({_fmt_pct(err.get('missed_loc_rate'))}) "
            f"| {err.get('gt_missed_complete', '—')} "
            f"({_fmt_pct(err.get('missed_complete_rate'))}) |"
        )

    sb = diag.get("stratum_breakdown", {})
    if sb:
        lines.extend(
            [
                "",
                f"## 4. Density Stratum Breakdown (`Q1`–`Q5`, Best F1 `conf={best_conf:.4f}`)",
                "",
                "| Stratum | GT (min-max) | mAP@0.5 | mAP@0.5:0.95 | Pred/img (`@best`) | "
                "R@best | P@best | Loc@best | BG@best | R@0.25 |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for stratum, st in sb.items():
            lines.append(
                f"| `{stratum}` | {st['gt_boxes']} ({st['gt_min']}-{st['gt_max']}) "
                f"| {_fmt_float(st['map50'])} | {_fmt_float(st['map50_95'])} "
                f"| {st.get('avg_pred_best', '—')} "
                f"| {_fmt_pct(st.get('recall_best'))} | {_fmt_pct(st.get('precision_best'))} "
                f"| {_fmt_pct(st.get('loc_rate_best'))} | {_fmt_pct(st.get('bg_rate_best'))} "
                f"| {_fmt_pct(st.get('recall_025'))} |"
            )

    sc = diag.get("scale_breakdown", {})
    if sc:
        lines.extend(
            [
                "",
                "## 5. Object Scale Breakdown (Network Input Space)",
                "",
                "| Bucket | GT Count (% GT) | Recall@0.001 | Recall@best | "
                "Recall@0.05 | Recall@0.25 | Hit >=0.1 IoU (@best) |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for bname in ("small", "medium", "large"):
            b = sc.get(bname, {})
            lines.append(
                f"| `{bname}` | {b.get('gt_count', 0)} ({b.get('gt_pct', 0.0):.1f}%) "
                f"| {_fmt_pct(b.get('recall_001'))} | {_fmt_pct(b.get('recall_best'))} "
                f"| {_fmt_pct(b.get('recall_005'))} | {_fmt_pct(b.get('recall_025'))} "
                f"| {_fmt_pct(b.get('loc_or_tp_best'))} |"
            )

    if visual_exports:
        lines.extend(
            [
                "",
                f"## 6. Visual Inspection ({len(visual_exports)} Images at `@conf={vis_conf_str}`)",
                "",
                "| # | Image | Stratum | GT | TP | Loc | Dup | BG FP | Missed | Visual File |",
                "|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for idx, item in enumerate(visual_exports, start=1):
            c = item["counts"]
            missed = c["gt_missed_loc"] + c["gt_missed_complete"]
            link = _rel_visual_link(item["out_path"])
            lines.append(
                f"| {idx} | `{item['image']}` | `{item['stratum']}` | {c['gt_total']} "
                f"| {c['tp']} | {c['loc']} | {c['dup']} | {c['bg']} | {missed} | {link} |"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", default="yolo26s.pt")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--val-manifest", type=Path, default=DEFAULT_VAL_MANIFEST)
    parser.add_argument("--spike-manifest", type=Path, default=DEFAULT_SPIKE50_MANIFEST)
    parser.add_argument("--total-images", type=int, default=50)
    parser.add_argument(
        "--rebuild-spike",
        action="store_true",
        help="Force rebuilding the stratified val spike manifest from val.csv.",
    )
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument(
        "--tile",
        type=int,
        default=1024,
        help="Tile size in pixels (0 disables tiling).",
    )
    parser.add_argument(
        "--agnostic-nms",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Collapse competing classes per anchor inside one2one head.",
    )
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--eval-conf", type=float, default=0.001)
    parser.add_argument(
        "--latency-conf",
        type=float,
        default=None,
        help="Confidence threshold for latency benchmark (default: auto best_conf_f1).",
    )
    parser.add_argument("--max-det", type=int, default=1000)
    parser.add_argument("--skip-cpu-latency", action="store_true")
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--visuals-dir", type=Path, default=None)
    parser.add_argument(
        "--visual-conf",
        type=float,
        default=None,
        help="Confidence threshold for diagnostic visuals (default: auto best_conf_f1).",
    )
    parser.add_argument("--skip-visuals", action="store_true")
    parser.add_argument("--out-md", type=Path, default=BASELINE_DIR / "YOLO26S_BASELINE_LOCAL.md")
    args = parser.parse_args()

    tile_opt: bool | int = args.tile if args.tile > 0 else False
    model_name = f"yolo26s_{args.imgsz}_tile" if tile_opt else f"yolo26s_{args.imgsz}"
    out_json = args.out_json or (DEFAULT_RESULTS_DIR / f"{model_name}.json")
    visuals_dir = args.visuals_dir or (DEFAULT_VISUALS_DIR / model_name)
    iou_opt = args.iou if tile_opt else None
    notes = (
        f"Pretrained COCO-80 YOLO26s, end2end=True, tile={tile_opt}, "
        f"agnostic_nms={args.agnostic_nms}, class-agnostic collapsed to product."
    )

    need_visuals = not args.skip_visuals
    result = run_baseline_evaluation(
        model_name=model_name,
        weights=args.weights,
        model_loader=load_yolo26s,
        out_json=out_json,
        data_dir=args.data_dir,
        val_manifest_path=args.val_manifest,
        spike_manifest_path=args.spike_manifest,
        total_images=args.total_images,
        force_rebuild_spike=args.rebuild_spike,
        imgsz=args.imgsz,
        eval_conf=args.eval_conf,
        latency_conf=args.latency_conf,
        max_det=args.max_det,
        end2end=True,
        agnostic_nms=args.agnostic_nms,
        tile=tile_opt,
        iou=iou_opt,
        notes=notes,
        measure_cpu=not args.skip_cpu_latency,
        return_records=need_visuals,
    )

    if need_visuals:
        summary, image_records = result
        resolved_vis_conf = (
            args.visual_conf
            if args.visual_conf is not None
            else (summary["accuracy"]["best_conf_f1"] or 0.25)
        )
        print(
            f"[visuals] exporting {len(image_records)} images at conf>={resolved_vis_conf:.4f}...",
            flush=True,
        )
        visual_exports = export_diagnostic_visuals(
            image_records,
            visuals_dir,
            conf_thresh=resolved_vis_conf,
        )
        summary_path = visuals_dir.parent / f"{model_name}_summary.json"
        summary_path.write_text(json.dumps(visual_exports, indent=2) + "\n", encoding="utf-8")
    else:
        summary = result
        resolved_vis_conf = args.visual_conf
        visual_exports = []

    if args.out_md is not None:
        md = render_baseline_markdown(
            summary,
            visual_exports=visual_exports or None,
            visual_conf=resolved_vis_conf,
        )
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(md, encoding="utf-8")

    print(json.dumps(summary, indent=2))
    if visual_exports:
        print(f"Exported {len(visual_exports)} diagnostic visuals to {visuals_dir}")
    if args.out_md is not None:
        print(f"Wrote local baseline report to {args.out_md}")


if __name__ == "__main__":
    main()
