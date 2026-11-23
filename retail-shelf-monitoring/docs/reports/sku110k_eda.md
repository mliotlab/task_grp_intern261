# SKU-110K Subset Exploratory Data Analysis (EDA)

- **Dataset version:** `sku110k-shelf-v2`
- **Seed:** `2026`
- **Manifest SHA-256:** `c18daf36f20b59c210c5a6265c65f024af26dd80ba80ce8215da01dc80fcf22d`

## 1. Split Overview & Boxes per Image

| Split | Images | Total Boxes | Min | P10 | Median | Mean | Std | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 1000 | 145470 | 51 | 111.0 | 136.5 | 145.5 | 39.5 | 191.0 | 218.2 | 441 |
| val | 200 | 29533 | 61 | 113.9 | 136.5 | 147.7 | 39.8 | 189.1 | 214.5 | 349 |
| test | 200 | 28870 | 83 | 116.9 | 136.0 | 144.3 | 34.5 | 182.1 | 203.1 | 421 |
| overall | 1400 | 203873 | 51 | 112.0 | 136.0 | 145.6 | 38.9 | 189.1 | 214.0 | 441 |

## 2. Image Resolution

| Split | Width (min / med / max) | Height (min / med / max) | Aspect Ratio (med) | Megapixels (med) | Unique |
|---|---|---|---|---:|---:|
| train | 720 / 2448 / 4160 | 1280 / 3264 / 5312 | 0.75 | 7.99 | 33 |
| val | 1920 / 2448 / 4160 | 1920 / 3264 / 5312 | 0.75 | 7.99 | 19 |
| test | 1920 / 2448 / 4160 | 1920 / 3264 / 4608 | 0.75 | 7.99 | 16 |
| overall | 720 / 2448 / 4160 | 1280 / 3264 / 5312 | 0.75 | 7.99 | 34 |

**Top resolutions (overall):**

- `2448x3264`: 543 images (38.79%)
- `1920x2560`: 320 images (22.86%)
- `2336x4160`: 105 images (7.50%)
- `2340x4160`: 99 images (7.07%)
- `2560x1920`: 83 images (5.93%)

## 3. Bounding Box Size Distribution

| Split | Norm W (med / mean) | Norm H (med / mean) | Norm Area (med / mean) | Pixel W (med / mean) | Pixel H (med / mean) | Box Aspect W/H (med) |
|---|---|---|---|---|---|---:|
| train | 0.0449 / 0.0507 | 0.0599 / 0.0625 | 0.00255 / 0.00297 | 106.0 / 123.2 | 184.0 / 193.3 | 0.71 |
| val | 0.0449 / 0.0517 | 0.0570 / 0.0598 | 0.00246 / 0.00285 | 105.0 / 124.2 | 176.0 / 185.5 | 0.74 |
| test | 0.0458 / 0.0528 | 0.0597 / 0.0613 | 0.00256 / 0.00297 | 105.0 / 125.1 | 180.0 / 191.0 | 0.73 |
| overall | 0.0449 / 0.0511 | 0.0594 / 0.0620 | 0.00254 / 0.00296 | 106.0 / 123.6 | 182.0 / 191.8 | 0.72 |

**COCO-style pixel area buckets (overall):**

- Small (`area < 32^2` px): 175 (0.09%)
- Medium (`32^2 <= area < 96^2` px): 34656 (17.00%)
- Large (`area >= 96^2` px): 169042 (82.92%)

## 4. Training & Inference Implications

- **Dense scenes:** overall max boxes/image is `441` (p95: `214.0`). Verify `max_det` in `training/configs/train_yolov8n.yaml` and `evaluate.py` exceeds the tail density.
- **Input resolution:** median image resolution is `2448x3264`; compare against `imgsz: 1024` during training and `1920` max-side resize in serving.
