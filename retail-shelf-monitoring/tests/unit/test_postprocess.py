"""Post-processing tests with synthetic boxes (NFR-07: coverage ≥ 60 % on this module).

Remove the `skip` marks as each function is implemented.
"""

from __future__ import annotations

import pytest

from shelfmon.postprocess import find_gaps, group_into_rows, image_fill_rate, row_fill_rate
from shelfmon.schemas import BoundingBox

TODO_FR03 = pytest.mark.skip(reason="TODO(FR-03): implement group_into_rows / find_gaps")
TODO_FR04 = pytest.mark.skip(reason="TODO(FR-04): implement fill-rate functions")


@TODO_FR03
def test_groups_boxes_into_two_rows(two_row_shelf: list[BoundingBox]) -> None:
    rows = group_into_rows(two_row_shelf)
    assert [len(r.boxes) for r in rows] == [7, 10]
    assert rows[0].y1 < rows[1].y1


@TODO_FR03
def test_empty_input_gives_no_rows() -> None:
    assert group_into_rows([]) == []


@TODO_FR03
def test_finds_the_single_gap(two_row_shelf: list[BoundingBox]) -> None:
    rows = group_into_rows(two_row_shelf)
    gaps = find_gaps(rows[0], shelf_x1=0, shelf_x2=1000, width_multiplier=1.5)
    assert len(gaps) == 1
    assert (gaps[0].x1, gaps[0].x2) == (400, 700)
    assert find_gaps(rows[1], 0, 1000, 1.5) == []


@TODO_FR04
def test_fill_rates(two_row_shelf: list[BoundingBox]) -> None:
    rows = group_into_rows(two_row_shelf)
    assert row_fill_rate(rows[0], 0, 1000) == pytest.approx(0.7)
    assert row_fill_rate(rows[1], 0, 1000) == pytest.approx(1.0)
    assert 0.7 <= image_fill_rate(rows) <= 1.0


@TODO_FR04
def test_overlapping_boxes_are_not_double_counted() -> None:
    boxes = [
        BoundingBox(x1=0, y1=0, x2=60, y2=10),
        BoundingBox(x1=40, y1=0, x2=100, y2=10),
    ]
    (row,) = group_into_rows(boxes)
    assert row_fill_rate(row, 0, 200) == pytest.approx(0.5)


@TODO_FR04
def test_no_rows_means_zero_fill_rate() -> None:
    assert image_fill_rate([]) == 0.0
