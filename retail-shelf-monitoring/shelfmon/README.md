# `shelfmon` — Core Shelf Analysis Package

Pure-Python core shared by the FastAPI service (`services/api/`), batch CLI, and unit tests. Keeps ML/geometry logic decoupled from HTTP and database I/O.

## Dataflow

```text
original BGR image (H×W×3)
  │
  ├─ pipeline.resize_max_side()    ──▶ downscaled image (≤ max_image_side)
  ├─ inference.Detector.detect()   ──▶ raw product boxes (in resized pixels)
  ├─ postprocess.rescale_boxes()   ──▶ product boxes restored to original pixels
  ├─ postprocess.run_postprocess() ──▶ rows, gaps, row/image fill rates, alert + reason
  └─ postprocess.draw_annotations()──▶ annotated BGR image (in memory, on original pixels)
```

## Module Map

| Path | Responsibility | Spec / Contract |
|---|---|---|
| `schemas.py` | Canonical Pydantic API types: `BoundingBox`, `Gap`, `ShelfRow`, `AnalysisResult`. | [DESIGN.md §5](../docs/DESIGN.md#5-api) |
| `config.py` | `Settings` loaded from env / `.env` (model path, thresholds, upload/resize limits, storage). | [DESIGN.md §9](../docs/DESIGN.md#9-operations) |
| `pipeline.py` | Single-image orchestrator (`analyze_image`) + `resize_max_side`; owns coordinate rescaling back to original pixels and stage timing (`preprocess`, `inference`, `postprocess`). | [DESIGN.md §4.1](../docs/DESIGN.md#41-analyze-a-shelf-image) |
| `inference/` | `Detector` protocol, `FakeDetector` (deterministic tests / walking skeleton), `YoloDetector` + `load_detector` (model registry). | [DESIGN.md §3](../docs/DESIGN.md#3-architecture-overview) |
| `postprocess/` | Filtering, shelf/row geometry, Store ROI, gap detection, fill rates, and annotation rendering. See [postprocess/README.md](postprocess/README.md). | [ADR-0002](../docs/adr/0002-gap-detection-rule.md), [ADR-0003](../docs/adr/0003-post-processing-rule.md) |
| `alert.py` | `should_alert` (`fill_rate < threshold`), `determine_alert_reason` (`"no_detection"` vs `"low_fill"`), and FR-09 webhook stub. | [ADR-0002 §3](../docs/adr/0002-gap-detection-rule.md), [DESIGN.md §6](../docs/DESIGN.md#6-data-model) |
| `timing.py` | `StepTimer` context manager recording per-stage milliseconds for `timings_ms` and JSON logs (NFR-05). | [DESIGN.md §5](../docs/DESIGN.md#5-api) |
| `cli.py` | Batch folder-to-CSV CLI entrypoint (`shelfmon-batch`, FR-08 stub). | [PRD.md](../docs/PRD.md) |

## Backend Integration Boundary (`services/api/`)

1. Decode uploaded image bytes into an original-resolution BGR `np.ndarray`.
2. Call `analyze_image(image, store_id, detector, settings, roi=None)` → returns `AnalysisResult` ready for `POST /v1/analyze` JSON serialization.
3. Call `draw_annotations(image, result.boxes, result.gaps, fill_rate=result.fill_rate, rows=result.rows, alert=result.alert)` → returns an annotated BGR `np.ndarray` in memory to persist under `IMAGE_DIR`.
4. When `result.alert` is `True`, call `determine_alert_reason(result.fill_rate, len(result.rows), settings.fill_rate_alert_threshold)` for `Alert.reason`, and `PostprocessConfig.from_settings(settings).model_dump()` for `Analysis.config_snapshot`.
