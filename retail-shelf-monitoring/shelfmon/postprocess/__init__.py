"""Pure-Python post-processing (no model, no I/O) – fully unit-testable with synthetic boxes."""

from shelfmon.postprocess.fill_rate import image_fill_rate, row_fill_rate
from shelfmon.postprocess.filtering import (
    clamp_boxes,
    filter_by_confidence,
    filter_geometric_outliers,
    rescale_boxes,
)
from shelfmon.postprocess.gaps import find_gaps, merge_intervals
from shelfmon.postprocess.roi import StoreROI
from shelfmon.postprocess.rows import estimate_shelf_rows, group_into_rows
from shelfmon.postprocess.runner import run_postprocess
from shelfmon.postprocess.types import (
    PostprocessConfig,
    PostprocessOutput,
    RowRegion,
    ShelfGeometry,
)
from shelfmon.postprocess.visualize import draw_annotations

__all__ = [
    "PostprocessConfig",
    "PostprocessOutput",
    "RowRegion",
    "ShelfGeometry",
    "StoreROI",
    "clamp_boxes",
    "draw_annotations",
    "estimate_shelf_rows",
    "filter_by_confidence",
    "filter_geometric_outliers",
    "find_gaps",
    "group_into_rows",
    "image_fill_rate",
    "merge_intervals",
    "rescale_boxes",
    "row_fill_rate",
    "run_postprocess",
]
