"""Core data types shared by inference, post-processing, API and dashboard."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class BoundingBox(BaseModel):
    """Axis-aligned box in pixel coordinates (x1, y1) top-left, (x2, y2) bottom-right."""

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = Field(1.0, ge=0, le=1)
    label: str = "product"

    @model_validator(mode="after")
    def _check_order(self) -> BoundingBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("expected x2 > x1 and y2 > y1")
        return self

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class Gap(BaseModel):
    """An empty region on one shelf row."""

    row_index: int
    x1: float
    y1: float
    x2: float
    y2: float

    @model_validator(mode="after")
    def _check_order(self) -> Gap:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("expected x2 > x1 and y2 > y1")
        return self

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


class ShelfRow(BaseModel):
    index: int
    y1: float
    y2: float
    boxes: list[BoundingBox]
    gaps: list[Gap] = Field(default_factory=list)
    fill_rate: float = Field(1.0, ge=0, le=1)


class AnalysisResult(BaseModel):
    """Response of POST /v1/analyze (FR-01)."""

    analysis_id: str
    store_id: str
    created_at: datetime
    model_version: str
    product_count: int
    boxes: list[BoundingBox]
    rows: list[ShelfRow]
    gaps: list[Gap]
    fill_rate: float = Field(ge=0, le=1)
    alert: bool
    timings_ms: dict[str, float] = Field(default_factory=dict)
