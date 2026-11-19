# PRD – Retail Shelf Monitoring

**Status:** In review · **Version:** v1.0 · **Owner:** Trần Tất Nguyên · **Reviewers:** Phạm Minh Phú, Lê Trần Tấn Phát (Mentor)

## 1. Context and problem

In retail operations, out-of-stock (OOS) shelf conditions directly reduce sales revenue and degrade customer experience. Store staff currently inspect shelves manually by shift, which is slow, labor-intensive, and prone to human oversight.

Retailers can use shelf images captured by fixed cameras or staff smartphones together with computer vision to detect empty shelf gaps early and trigger timely replenishment. This project builds a minimal viable Retail Shelf Monitoring service following software and AI engineering practices. Given a shelf photo, the system detects product bounding boxes, groups products into shelf rows, identifies empty shelf gaps, computes row-level and overall fill rates, raises low-stock alerts, and stores analysis history for a web dashboard.

### Team roles and ownership

| Member | Primary role | Key responsibilities |
|---|---|---|
| **Phạm Minh Phú** | ML Engineer | Dataset preparation and EDA, model fine-tuning and evaluation, empty-shelf labeling guidelines, post-processing algorithms, Model Card, Evaluation Report |
| **Trần Tất Nguyên** | Backend and Platform Engineer | REST API, inference integration, database and image storage, Streamlit dashboard, Docker Compose, CI/CD, load testing, Runbook |

## 2. Users and personas

| Persona | Goals | Pain points |
|---|---|---|
| **Store Staff** | Capture shelf photos during a shift and receive actionable alerts on empty shelf gaps so products can be restocked promptly. | Manual visual inspection across aisles is repetitive, slow, and can miss partially depleted rows during peak hours. |
| **Store Manager** | Monitor shelf fill rates and review unresolved and resolved alert history across stores and time ranges through a dashboard. | Lacks historical visibility into recurring out-of-stock patterns and a centralized metric for shelf availability. |
| **External / Internal Systems** (cameras, store apps) | Submit shelf images programmatically through a reliable REST API and consume structured detection and alert results. | Need predictable response times, documented OpenAPI schemas, strict input validation, and clear error codes. |

## 3. User stories

| ID | Story | Acceptance criteria (Given / When / Then) |
|---|---|---|
| **US-01** | As a Store Staff member or External System, I want to upload a shelf image through a REST API with `store_id` so that I receive detected product boxes, empty gaps, fill rate, and an `analysis_id`. | Given a valid JPG/PNG shelf image up to 10 MB and a `store_id`, when `POST /v1/analyze` is called, then the API returns HTTP `200` with JSON containing `analysis_id`, product bounding boxes with confidence scores, product count, empty gap regions, and fill rate. |
| **US-02** | As a Store Staff member or Store Manager, I want to retrieve an annotated image highlighting detected products and empty shelf gaps so that I can visually verify the analysis. | Given a completed `analysis_id`, when `GET /v1/analyses/{id}/image` is called, then the service returns an annotated image with product boxes and highlighted empty gap regions. |
| **US-03** | As a Store Staff member, I want the system to group products by shelf row and detect significant horizontal gaps so that empty spaces are localized per shelf tier. | Given detected product bounding boxes on a multi-tier shelf, when post-processing runs, then boxes are grouped into shelf rows by vertical coordinates and horizontal gaps wider than a configurable multiple of average product width are flagged as empty gaps. |
| **US-04** | As a Store Manager, I want fill rates calculated per shelf row and across the whole shelf, with alerts when fill rate drops below a threshold, so that restocking can be prioritized. | Given detected products and empty gaps on a shelf image, when post-processing completes, then row-level and overall fill rates are computed and an alert record is created whenever fill rate falls below the configured threshold (default `80%`). |
| **US-05** | As a Store Manager, I want analysis history persisted and queryable by store and time range so that I can audit shelf performance over time. | Given multiple completed analyses stored in the database, when `GET /v1/analyses` is called with optional `store_id` and time-range filters, then matching historical records (timestamp, `store_id`, metrics, and image paths) are returned. |
| **US-06** | As a Platform / DevOps Engineer, I want a health-check endpoint and strict input validation so that service uptime is monitorable and malformed requests fail gracefully. | Given a running API service, when `GET /health` is called, then it returns HTTP `200`; when a corrupted, unsupported-format, or oversized file is uploaded, then the API returns an appropriate `4xx` error with a clear message without crashing. |
| **US-07** | As a Store Manager, I want a web dashboard to filter analyses by store, inspect annotated images, and acknowledge alerts so that I can manage store operations without calling raw APIs. | Given the Streamlit dashboard connected to the backend, when a manager filters by `store_id`, selects an analysis, or marks an alert as resolved, then the UI displays the annotated image and updates the alert status. |
| **US-08** | As an ML / Operations Engineer, I want a CLI tool to batch-process a folder of shelf images and export results to CSV so that offline audits and evaluations are streamlined. | Given a local directory of shelf images, when the batch CLI command runs, then all valid images are analyzed and a summary CSV report is generated. |
| **US-09** | As a Store Manager, I want optional webhook notifications (Telegram/Slack) when an alert triggers so that staff receive restock notifications through existing messaging channels. | Given a configured webhook URL, when an analysis triggers a low-fill-rate alert, then a formatted notification payload is dispatched to the webhook endpoint. |
| **US-10** | As a Store Manager, I want configurable Regions of Interest (ROI) per store/camera so that background clutter outside the target shelf is excluded from fill-rate calculations. | Given an ROI polygon or bounding box configured for a `store_id`, when an image from that store is analyzed, then detections and fill-rate metrics are restricted to the defined ROI. |

## 4. Functional requirements

| ID | Requirement | Priority (MoSCoW) | User story |
|---|---|---|---|
| **FR-01** | `POST /v1/analyze` accepts a JPG/PNG image up to 10 MB and `store_id`, returning JSON with bounding boxes, confidence scores, product count, empty gaps, fill rate, and `analysis_id`. | Must | US-01 |
| **FR-02** | Generate an annotated image highlighting product bounding boxes and empty gaps, retrievable through `GET /v1/analyses/{id}/image`. | Must | US-02 |
| **FR-03** | Detect empty shelf gaps per row by grouping bounding boxes into shelf rows by vertical coordinates and identifying gaps exceeding a configurable threshold based on a multiple of mean product width. | Must | US-03 |
| **FR-04** | Compute fill rate per shelf row and for the entire image; generate an alert when fill rate falls below a configurable threshold (default `80%`). | Must | US-04 |
| **FR-05** | Persist analysis history (timestamp, `store_id`, results, and image paths) in a database; expose `GET /v1/analyses` with store and time-range filters. | Must | US-05 |
| **FR-06** | Provide `GET /health` and return standardized `4xx` errors for corrupted images, unsupported formats, or oversized uploads. | Must | US-06 |
| **FR-07** | Provide a Streamlit dashboard to list analyses, filter by store, view annotated images, view unresolved alerts, and mark alerts as resolved. | Should | US-07 |
| **FR-08** | Provide a CLI tool for batch-processing a directory of shelf images and exporting results to CSV. | Should | US-08 |
| **FR-09** | Send alert notifications through an outgoing webhook (e.g. Telegram or Slack). | Could | US-09 |
| **FR-10** | Configure Regions of Interest (ROI) per camera/store to restrict the analysis area. | Could | US-10 |

## 5. Non-functional requirements

| ID | Attribute | Target and how it is measured |
|---|---|---|
| **NFR-01** | Detection Accuracy | Report `mAP@0.5` and `mAP@0.5:0.95` on a test split of at least 200 SKU-110K images for both pretrained baseline and fine-tuned models. Reference target: `mAP@0.5 >= 0.75`. |
| **NFR-02** | Empty-Gap Detection Quality | Empty-gap precision and recall are each at least `0.70` on at least 30 team-annotated shelf images; document annotation rules in `EVAL_REPORT.md`. |
| **NFR-03** | Inference and API Latency | `p95` latency is at most 2 seconds/image on the lab GPU or 5 seconds/image on CPU for images with longest edge at most 1920 px, measured with a 100-request load test. |
| **NFR-04** | Reliability | No request causes the service to stop; 100% of invalid inputs in the negative test suite return a `4xx` status with an error message. |
| **NFR-05** | Observability | Emit structured JSON logs per request containing `request_id`, per-stage latency (preprocessing, inference, post-processing), detected box count, and model version. |
| **NFR-06** | Reproducibility | Commit training configurations, random seeds, and dataset split manifests; provide SHA-256 checksums and download links for model weights; `docker compose up` starts both API and dashboard. |
| **NFR-07** | Test Coverage | Achieve at least 60% unit and integration test coverage for the post-processing module and API; cover pure post-processing logic with deterministic unit tests using synthetic bounding boxes. |

## 6. Success metrics

| Metric | Target | How it is measured |
|---|---|---|
| **Product Detection `mAP@0.5`** | At least `0.75` and improved over the pretrained baseline. | Run the evaluation script on the fixed 200-image SKU-110K test split; report results in `EVAL_REPORT.md` and `MODEL_CARD.md`. |
| **Empty-Gap Precision and Recall** | Precision and recall each at least `0.70`. | Evaluate against ground-truth gap annotations on at least 30 shelf images using the IoU matching criteria documented in `EVAL_REPORT.md`. |
| **End-to-End `p95` Latency** | At most 2.0 seconds (GPU) or 5.0 seconds (CPU) per image. | Run a 100-request HTTP load test against `POST /v1/analyze` using images with longest edge at most 1920 px (`hey` or Locust). |
| **Automated Test Coverage** | At least 60% for post-processing and API modules. | Measure with `pytest --cov`; the RSM GitHub Actions workflow reports coverage for relevant pull requests. This is a reported metric, not a CI-enforced coverage threshold. |
| **One-Command Deployment** | A person outside the team can start the system from a clean clone within 15 minutes. | Separately, CI smoke-tests the API by starting it with Docker Compose and checking `GET /health`; in Sprint 4, a person outside the team follows `README.md` from a clean clone and times startup of the API and dashboard. |

## 7. Out of scope (non-goals)

- Fine-grained SKU classification (identifying exact product brands or barcodes) and detailed planogram compliance checking.
- Real-time streaming video ingestion from live CCTV feeds.
- Native mobile applications, user authentication/authorization (RBAC), and cloud production deployment.
- Training object-detection architectures from scratch or designing novel neural-network backbones.

## 8. Assumptions, dependencies, risks

- **Dataset constraint and assumption:** Experiments use a deterministic subset of the public SKU-110K dataset (1,000 train / 200 validation / 200 test images) to fit available compute resources. The subset is assumed to represent shelf density and camera viewpoints sufficiently for evaluating row-clustering and gap heuristics.
- **Compute dependency:** Fine-tuning depends on scheduled lab GPU access allocated by the mentor, with a total budget of at most 10 GPU hours across the four-week internship.
- **Licensing and data privacy:** Ultralytics YOLO is used under AGPL-3.0 for internal educational/research purposes. No proprietary customer data or PII is used. Secrets and credentials are excluded from Git through `.env` handling; `.env.example` contains only safe example values.
- **Perspective distortion and tilted shelves:** Angled camera views can skew vertical row clustering. Normalize vertical coordinates relative to local box heights and document failure modes in `EVAL_REPORT.md` and `MODEL_CARD.md`.
- **Occluded or irregular gaps:** Shelf dividers or overhanging items may cause false positives or missed gaps. Establish explicit empty-shelf annotation guidelines in Sprint 1 and cross-check annotations between team members.
- **CPU inference latency bottleneck:** Larger YOLO variants may exceed the 5-second `p95` CPU target. Benchmark YOLO nano/small early and apply image resizing (longest edge at most 1920 px) and model warm-up as appropriate.

## 9. Open questions

1. **Default database engine:** Should `docker-compose.yml` use SQLite with a zero-configuration volume by default for Sprint 2 and optionally support PostgreSQL through environment variables, or run PostgreSQL as the primary container from Sprint 2?
2. **Minimum empty-gap threshold:** What default multiplier of average product width (e.g. `1.2x` or `1.5x` mean box width) should be used for FR-03 before tuning on the 30 annotated images?
3. **Annotated image storage:** Should original and annotated images be stored on a local Docker volume (`./data/images/`) by default, or is MinIO object storage preferred?
