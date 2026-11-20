# SKU-110K Subset Exploratory Data Analysis (EDA)

- **Dataset version:** `sku110k-subset-v1`
- **Seed:** `2026`
- **Manifest SHA-256:** `a8cb3cd88cbd1d8daed2edd608db34fafd6a08eec2157d49b71c1ddba176d8ca`

## 1. Split Overview & Boxes per Image

| Split | Images | Total Boxes | Min | P10 | Median | Mean | Std | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 1000 | 148029 | 51 | 110.0 | 137.0 | 148.0 | 46.8 | 198.0 | 226.1 | 576 |
| val | 200 | 30476 | 40 | 112.8 | 138.5 | 152.4 | 63.7 | 191.1 | 224.1 | 718 |
| test | 200 | 29379 | 63 | 116.0 | 137.5 | 146.9 | 40.4 | 184.1 | 210.5 | 421 |
| overall | 1400 | 207884 | 40 | 111.0 | 137.0 | 148.5 | 48.8 | 195.0 | 224.1 | 718 |

## 2. Image Resolution

| Split | Width (min / med / max) | Height (min / med / max) | Aspect Ratio (med) | Megapixels (med) | Unique |
|---|---|---|---|---:|---:|
| train | 720 / 2448 / 4160 | 1280 / 3264 / 5312 | 0.75 | 7.99 | 34 |
| val | 1920 / 2448 / 4160 | 1920 / 3264 / 4608 | 0.75 | 7.99 | 18 |
| test | 1920 / 2448 / 4160 | 1920 / 3264 / 4608 | 0.75 | 7.99 | 15 |
| overall | 720 / 2448 / 4160 | 1280 / 3264 / 5312 | 0.75 | 7.99 | 35 |

**Top resolutions (overall):**

- `2448x3264`: 573 images (40.93%)
- `1920x2560`: 307 images (21.93%)
- `2340x4160`: 90 images (6.43%)
- `2336x4160`: 90 images (6.43%)
- `2560x1920`: 79 images (5.64%)

## 3. Bounding Box Size Distribution

| Split | Norm W (med / mean) | Norm H (med / mean) | Norm Area (med / mean) | Pixel W (med / mean) | Pixel H (med / mean) | Box Aspect W/H (med) |
|---|---|---|---|---|---|---:|
| train | 0.0432 / 0.0492 | 0.0583 / 0.0616 | 0.00245 / 0.00287 | 103.0 / 120.3 | 179.0 / 189.3 | 0.70 |
| val | 0.0422 / 0.0480 | 0.0553 / 0.0585 | 0.00231 / 0.00270 | 98.0 / 114.3 | 169.0 / 178.4 | 0.74 |
| test | 0.0436 / 0.0509 | 0.0579 / 0.0601 | 0.00245 / 0.00284 | 100.0 / 120.9 | 176.0 / 186.1 | 0.70 |
| overall | 0.0429 / 0.0492 | 0.0578 / 0.0610 | 0.00243 / 0.00284 | 102.0 / 119.5 | 177.0 / 187.2 | 0.71 |

**COCO-style pixel area buckets (overall):**

- Small (`area < 32^2` px): 197 (0.09%)
- Medium (`32^2 <= area < 96^2` px): 42239 (20.32%)
- Large (`area >= 96^2` px): 165448 (79.59%)

## 4. Training & Inference Implications

- **Dense scenes:** overall max boxes/image is `718` (p95: `224.1`). Verify `max_det` in `training/configs/train_yolov8n.yaml` and `evaluate.py` exceeds the tail density.
- **Input resolution:** median image resolution is `2448x3264`; compare against `imgsz: 1024` during training and `1920` max-side resize in serving.
