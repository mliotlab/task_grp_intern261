"""Pure-Python post-processing (no model, no I/O) – fully unit-testable with synthetic boxes."""

from shelfmon.postprocess.fill_rate import image_fill_rate, row_fill_rate
from shelfmon.postprocess.filtering import filter_by_confidence
from shelfmon.postprocess.gaps import find_gaps
from shelfmon.postprocess.rows import group_into_rows

__all__ = [
    "filter_by_confidence",
    "find_gaps",
    "group_into_rows",
    "image_fill_rate",
    "row_fill_rate",
]
