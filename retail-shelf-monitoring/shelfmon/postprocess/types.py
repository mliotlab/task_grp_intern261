"""Structured configuration and internal geometry carriers for post-processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from shelfmon.alert import AlertReason
from shelfmon.schemas import BoundingBox, Gap, ShelfRow

if TYPE_CHECKING:
    from shelfmon.config import Settings


class PostprocessConfig(BaseModel):
    """Configurable post-processing parameters aligned with ADR-0002 and ADR-0003."""

    # Pre-clustering filtering (ADR-0003 §1)
    conf_threshold: float = Field(0.25, ge=0.0, le=1.0)
    enable_outlier_filter: bool = True
    min_box_side_px: float = Field(2.0, ge=0.0)
    min_height_ratio: float = Field(0.12, ge=0.0, lt=1.0)
    max_height_ratio: float = Field(8.0, gt=1.0)
    min_area_ratio: float = Field(0.02, ge=0.0, lt=1.0)
    outlier_min_boxes: int = Field(6, ge=1)
    clamp_to_image: bool = True

    # Row clustering, stacked-tier consolidation & deskewing (ADR-0003 §2)
    clustering_method: Literal["center_y", "dbscan_1d"] = "center_y"
    row_y_tolerance_ratio: float = Field(0.45, gt=0.0)
    use_local_row_height: bool = True
    consolidate_stacked_boxes: bool = True
    stack_x_overlap_ratio: float = Field(0.45, gt=0.0, le=1.0)
    stack_v_gap_ratio: float = Field(0.05, ge=0.0)
    flat_stack_aspect_ratio: float = Field(1.3, gt=0.0)
    flat_stack_v_gap_ratio: float = Field(0.25, ge=0.0)
    row_v_merge_threshold: float = Field(0.45, gt=0.0, le=1.0)
    tilt_min_boxes_per_row: int = Field(4, ge=2)
    tilt_deadband_deg: float = Field(1.5, ge=0.0)
    tilt_max_deg: float = Field(20.0, gt=0.0)
    row_vertical_bounds: Literal["robust", "envelope"] = "robust"
    shelf_bound_mode: Literal["outer_products", "neighbor_median", "row_extent", "image_width"] = (
        "neighbor_median"
    )
    edge_min_neighbor_boxes: int = Field(3, ge=1)

    # Empty-tier inference (ADR-0003 §4)
    infer_empty_tiers: bool = True
    empty_tier_kv: float = Field(1.2, gt=0.0)
    empty_tier_min_pitch_ratio: float = Field(1.75, gt=1.0)
    max_empty_tiers_per_gap: int = Field(2, ge=1)

    # Gap detection & fill-rate alerting (ADR-0002 §1–§3)
    gap_width_multiplier: float = Field(1.5, gt=0.0)
    neighbor_count: int = Field(5, ge=1)
    single_box_use_shelf_median: bool = True
    use_local_gap_y: bool = True
    enable_cross_row_mask: bool = True
    cross_row_v_overlap: float = Field(0.35, gt=0.0, le=1.0)
    max_gap_product_coverage: float = Field(0.30, gt=0.0, le=1.0)
    deduplicate_gaps: bool = True
    fill_rate_alert_threshold: float = Field(0.80, ge=0.0, le=1.0)

    @classmethod
    def from_settings(cls, settings: Settings) -> PostprocessConfig:
        return cls(
            conf_threshold=settings.conf_threshold,
            gap_width_multiplier=settings.gap_width_multiplier,
            fill_rate_alert_threshold=settings.fill_rate_alert_threshold,
            clustering_method=settings.row_clustering_method,
            row_y_tolerance_ratio=settings.row_y_tolerance_ratio,
            shelf_bound_mode=settings.shelf_bound_mode,
            tilt_deadband_deg=settings.tilt_deadband_deg,
            empty_tier_kv=settings.empty_tier_kv,
            neighbor_count=settings.gap_neighbor_count,
        )


@dataclass
class RowRegion:
    """Unified per-row geometry produced by ADR-0003 rule-based estimation or Store ROI."""

    row: ShelfRow
    x1: float
    x2: float
    y1: float
    y2: float
    is_inferred_empty: bool = False


@dataclass
class ShelfGeometry:
    """Estimated shelf frame and per-row regions (internal to post-processing / visuals)."""

    mode: Literal["rule", "roi"]
    regions: list[RowRegion] = field(default_factory=list)
    tilt_deg: float = 0.0
    shelf_polygon: list[tuple[float, float]] | None = None

    @property
    def rows(self) -> list[ShelfRow]:
        return [reg.row for reg in self.regions]


@dataclass
class PostprocessOutput:
    """Complete deterministic output of the pure post-processing stage."""

    boxes: list[BoundingBox]
    rows: list[ShelfRow]
    gaps: list[Gap]
    fill_rate: float
    alert: bool
    alert_reason: AlertReason | None
    geometry: ShelfGeometry
