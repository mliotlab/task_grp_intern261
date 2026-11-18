"""Shelf analysis API.  Run: uvicorn services.api.main:app --reload  →  http://localhost:8000/docs"""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from shelfmon import __version__
from shelfmon.config import get_settings
from shelfmon.schemas import AnalysisResult

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}

app = FastAPI(
    title="Retail Shelf Monitoring API",
    version=__version__,
    description="Detect products and empty gaps on shelf photos; compute fill rate; raise alerts.",
)


def not_implemented(requirement: str) -> HTTPException:
    return HTTPException(status_code=501, detail=f"Not implemented yet ({requirement})")


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": __version__, "model_version": settings.model_version}


@app.post("/v1/analyze", response_model=AnalysisResult, tags=["analysis"])
async def analyze(
    image: UploadFile = File(..., description="JPG or PNG, ≤ 10 MB"),
    store_id: str = Form(..., min_length=1, max_length=64),
) -> AnalysisResult:
    """TODO(FR-01, FR-05, FR-06, NFR-05):
    1. reject wrong content type (415), > MAX_UPLOAD_MB (413) and undecodable images (422),
       each with a clear message;
    2. decode with cv2.imdecode; call pipeline.analyze_image(image, store_id, detector, settings);
    3. save original + annotated image and the result row (SQLAlchemy); maybe send webhook;
    4. log request_id, per-step timings, box count and model version as JSON.
    """
    raise not_implemented("FR-01")


@app.get("/v1/analyses", response_model=list[AnalysisResult], tags=["analysis"])
def list_analyses(
    store_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=500),
) -> list[AnalysisResult]:
    raise not_implemented("FR-05")


@app.get("/v1/analyses/{analysis_id}/image", response_class=FileResponse, tags=["analysis"])
def get_annotated_image(analysis_id: str) -> FileResponse:
    raise not_implemented("FR-02")
