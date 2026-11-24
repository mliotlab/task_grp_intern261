# Pretrained Baseline Evaluation Report – `yolo26s` (Issue #14)

- **Model:** `yolo26s.pt` (COCO-80 pretrained, collapsed class-agnostic → `product`)
- **Dataset version:** `sku110k-shelf-v2` (`val_spike50`, `seed=2026`)
- **Dataset manifest SHA-256:** `c18daf36f20b59c210c5a6265c65f024af26dd80ba80ce8215da01dc80fcf22d`
- **Base commit:** `c16e1c4` (`main` — `sku110k-shelf-v2`)
- **Date:** 2026-11-23

---

## 1. Objectives

Thiết lập mốc baseline chưa fine-tune (pretrained) cho bài toán phát hiện sản phẩm dày đặc trên kệ bán lẻ (Sprint 1 / Issue #14), làm cơ sở so sánh với mô hình fine-tune ở Sprint 3 và kiểm chứng sớm các yêu cầu phi chức năng liên quan:

| Requirement | Metric | Target / Reference | Sprint 1 Baseline Scope |
|---|---|---|---|
| **NFR-01** | Detection Accuracy (`mAP@0.5`, `mAP@0.5:0.95`) | Fine-tuned `mAP@0.5 >= 0.75` trên `test` (200 ảnh), vượt pretrained baseline | Thiết lập mốc pretrained trên `val_spike50` (giữ nguyên `test` 200 ảnh không chạm tới trước Sprint 3) |
| **NFR-03** | Inference Latency (`batch=1`) | `p95 <= 2000 ms` (GPU) hoặc `<= 5000 ms` (CPU), cạnh dài `<= 1920 px` | Đo độ trễ suy luận thuần GPU & CPU trên ảnh gốc `val_spike50` (`warmup=5`, `n=50`) |
| **NFR-06** | Reproducibility | Script, config, seed, dataset version & kết quả ghi nhận rõ ràng | Tái lập từ `training/baseline/eval_yolo26s.py`, log vào `training/results.csv` |

---

## 2. Evaluation Data

- **Nguồn dữ liệu:** Tập con được làm sạch **`sku110k-shelf-v2`** (1000 `train` / 200 `val` / 200 `test`, `seed=2026`; đã loại 193 ảnh lỗi/mờ/không phải kệ từ `v1` và bù xác định — xem [`sku110k_eda.md`](sku110k_eda.md)).
- **Tập đánh giá baseline:** [`data/sku110k_subset/manifests/val_spike50.csv`](../../data/sku110k_subset/manifests/val_spike50.csv) — lấy mẫu phân tầng xác định **50 ảnh từ `val`** chia đều theo 5 tầng mật độ sản phẩm (`Q1`–`Q5`, mỗi tầng 10 ảnh, `seed=2026`), tổng cộng **7.284 GT boxes** (trung bình 145.7 box/ảnh, min 61, max 349).
- **Quy ước không rò rỉ dữ liệu (No leakage):**
  - `yolo26s.pt` được pretrain trên Objects365-v1 → COCO-80, chưa từng huấn luyện trên SKU-110K.
  - Tập `test` (200 ảnh) được giữ kín hoàn toàn cho báo cáo `EVAL_REPORT.md` ở Sprint 3.

---

## 3. Method

### 3.1 Reproducible Command

Chạy từ thư mục `retail-shelf-monitoring/`:

```bash
python training/baseline/eval_yolo26s.py --tile 1024 --agnostic-nms --iou 0.5
```

Script tự động: (1) xác minh/tạo `val_spike50.csv`, (2) chạy suy luận class-agnostic tại `eval_conf=0.001` để tính đường cong PR & tìm ngưỡng tối ưu `best_conf_f1`, (3) đo độ trễ GPU & CPU tại `best_conf_f1`, và (4) xuất đủ 50 ảnh kiểm tra trực quan (lưu cục bộ, gitignored).

### 3.2 Configuration & Hardware

| Parameter | Value |
|---|---|
| Weights | `yolo26s.pt` (~9.5M params, ~20.9B FLOPs) |
| Inference mode | `end2end=True` (`nms=False`, one-to-one head), `agnostic_nms=True`, `max_det=1000` |
| Input & Tiling | `imgsz=1024`, `tile=1024`, `iou=0.5` (tiling trên ảnh gốc) |
| Label mapping | Class-agnostic — gộp toàn bộ 80 class COCO về 1 nhãn duy nhất `product` |
| Operating threshold | `best_conf_f1 = 0.0111` (tối ưu F1 trên đường cong PR tại `IoU = 0.50`) |
| Hardware | GPU: `NVIDIA GeForce RTX 3050 Laptop GPU` · CPU: `Intel64 Family 6 Model 141 Stepping 1` |
| Runtime | Python `3.13.9`, PyTorch `2.15.0+cu132`, Ultralytics `8.4.216` (Windows 11) |

---

## 4. Exploratory Model Selection Summary (Why `yolo26s`)

Trước khi chốt baseline chính thức trên `sku110k-shelf-v2`, nhóm đã thực hiện sàng lọc nhanh nhiều biến thể trên tập `v1` sơ bộ (không commit các script thử nghiệm phụ nhằm giữ repo gọn) và rút ra các kết luận chính để chọn **`yolo26s` + `tile=1024`**:

1. **Lý do chọn họ `YOLO26` (`<= small`):** Chưa từng dùng SKU-110K (tránh data leakage), hỗ trợ `end2end=True` (NMS-free cho phép nâng `max_det=1000` mà không nghẽn NMS trên kệ dày), có `STAL + ProgLoss` tối ưu vật thể nhỏ và bỏ `DFL` giúp dễ export ONNX/INT8.
2. **So sánh kích cỡ mạng (`yolo26n` vs `yolo26s` vs `yolo26m` @1024):**
   - `yolo26n` chạy nhanh nhất trên CPU nhưng ít box tin cậy cao hơn ở cảnh dày (`avg_pred@0.25` chỉ ~3.7 vs ~8.0 của `yolo26s`), dung lượng đặc trưng nhỏ hơn khi fine-tune kệ dày đặc.
   - `yolo26m` nặng hơn nhiều (~44 MB), không phù hợp mục tiêu gọn nhẹ/CPU, thậm chí đạt `mAP@0.5` zero-shot thấp hơn (`~0.18`) do bám chặt prior 80 class COCO hơn.
   - **`yolo26s`** cân bằng tốt nhất giữa dung lượng biểu diễn cho fine-tune Sprint 3 và tốc độ suy luận.
3. **Độ phân giải đầu vào & kỹ thuật cắt ô (`640` → `1024` → `1280` → `tile=1024`):**
   - Với ảnh kệ trung vị `2448×3264 px`, ép về `640` làm ~75% sản phẩm rơi xuống vùng `< 32×32 px` trên lưới `P3/8` (`mAP@0.5` chỉ ~0.19).
   - Nâng lên `1024` → `1280` cải thiện dần (`~0.24` → `~0.25`), và **`tile=1024`** cho bước nhảy lớn nhất (`~0.30` trên v1 và **`0.3753`** trên `sku110k-shelf-v2`) nhờ giữ tỷ lệ pixel gốc.
4. **Cấu hình `max_det=1000` & `agnostic_nms=True`:**
   - 46/50 ảnh có > 300 dự đoán thô (`max_pred_boxes = 894`; mật độ thật tối đa 349 ở `val`, 441 ở `train`), nên nâng `max_det` từ 300 lên 1000 là cần thiết để tránh cắt cụt dự đoán trên kệ dày.
   - `agnostic_nms=True` giảm cạnh tranh đa class trên cùng một anchor và triệt tiêu trùng lặp tốt khi gộp tile.
5. **Đối chiếu zero-shot với `yoloe-26s-seg` (open-vocabulary packaging prompts):**
   - Khi cung cấp 16 prompt bao bì (`bottle`, `can`, `box`, `carton`, `packet`, `bag`...), `yoloe-26s-seg` đạt `mAP@0.5 ~ 0.43` trên `v1` ngay ở mức zero-shot.
   - Kết quả này xác nhận nút thắt lớn nhất của `yolo26s` pretrained là **lệch ngữ nghĩa lớp COCO-80** (chủ yếu biết chai/lọ, không có lớp hộp/gói bán lẻ), **không phải** điểm yếu kiến trúc backbone. Vì Sprint 3 sẽ fine-tune đơn lớp `product` trực tiếp trên SKU-110K, **`yolo26s`** được chốt làm model nền vì nhẹ hơn, thuần detection (không mang đầu segmentation hay phụ thuộc CLIP text encoder) và đơn giản hơn khi triển khai sản phẩm.

---

## 5. Final Baseline Results (`yolo26s`, `tile=1024`, `sku110k-shelf-v2`)

### 5.1 Overall Accuracy & Latency vs. NFR Targets

| Metric | Target (NFR) | Pretrained `yolo26s` (`tile=1024`) | Status / Notes |
|---|---:|---:|---|
| `mAP@0.5` (`val_spike50`, class-agnostic) | Fine-tuned `>= 0.75` (NFR-01) | **0.3753** | Baseline mốc trước fine-tune |
| `mAP@0.5:0.95` (`val_spike50`) | Report (NFR-01) | **0.1731** | Baseline mốc trước fine-tune |
| Precision / Recall / F1 (@ `best_conf_f1 = 0.0111`) | — | **0.3999 / 0.5361 / 0.4581** | Avg `195.3` pred/ảnh (max raw `894`, `46/50` ảnh > 300) |
| GPU Latency mean / p50 / **p95** (`conf=0.0111`) | `p95 <= 2000 ms` (NFR-03) | 756.0 / 733.8 / **1153.6 ms** | **Pass** (min `406.5`, max `1281.9 ms`) |
| CPU Latency mean / p50 / **p95** (`conf=0.0111`) | `p95 <= 5000 ms` (NFR-03) | 3047.2 / 2922.6 / **4756.2 ms** | **Pass (sát ngưỡng)** — max `6525.7 ms` trên ảnh gốc ~8 MP; nhạy tải CPU |

> **Ghi chú độ trễ CPU:** Đo trực tiếp trên ảnh gốc độ phân giải ~`2448×3264 px` cắt nhiều tile `1024×1024`. Trong serving thực tế (NFR-03 giới hạn cạnh dài `<= 1920 px`) và sau khi fine-tune đơn lớp ở Sprint 3, cần đối chiếu lại `imgsz=1024` single-pass (CPU p95 chỉ ~`300–450 ms`) so với tiling để bảo đảm biên an toàn CPU.

### 5.2 TIDE-Style Geometric Error Breakdown (Class-Agnostic)

| Threshold | Pred/img | TP | Loc (`0.1–0.5`) | Dup | BG FP (`<0.1`) | Recall@0.5 | Precision | Missed-Loc | Missed-Complete |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Best F1 (`0.0111`)** | **195.3** | **3905** | **2756 (28.2%)** | **61 (0.6%)** | **3044 (31.2%)** | **53.6%** | **40.0%** | **1246 (17.1%)** | **2133 (29.3%)** |
| `conf = 0.05` | 99.3 | 2540 | 1160 (23.4%) | 10 (0.2%) | 1255 (25.3%) | 34.9% | 51.2% | 763 (10.5%) | 3981 (54.6%) |
| `conf = 0.25` (mặc định) | 37.8 | 1205 | 290 (15.3%) | 1 (0.1%) | 394 (20.8%) | 16.5% | 63.8% | 269 (3.7%) | 5810 (79.8%) |

Nhận xét chính:
- **Điểm tin cậy bị nén rất thấp do lệch domain:** Hạ từ `0.25` xuống `0.0111` giúp số `TP` tăng hơn **3.2 lần** (`1205` → `3905`, Recall từ `16.5%` lên `53.6%`), đồng thời tỷ lệ bỏ sót hoàn toàn giảm từ `79.8%` xuống `29.3%`.
- **Trùng lặp (`Dup`) cực thấp (`0.6%`):** Chứng tỏ `end2end=True` + `agnostic_nms=True` + tile NMS `iou=0.5` kiểm soát tốt lỗi dự đoán trùng lặp.
- **Hai nguồn lỗi chính tại `best_conf_f1`:** `BG FP` (`31.2%` tổng dự đoán) và `Loc` (`28.2%` tổng dự đoán), đều xuất phát trực tiếp từ prior 80 class COCO chưa khớp định nghĩa sản phẩm SKU-110K.

### 5.3 Performance by Scene Density Stratum (`Q1`–`Q5`)

| Stratum | GT Boxes (min–max) | `mAP@0.5` | `mAP@0.5:0.95` | Pred/img (`@best`) | Recall@best | Precision@best | Loc@best | BG@best |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `Q1` (thưa nhất) | 1061 (61–120) | 0.3709 | 0.1813 | 193.0 | 55.5% | 30.5% | 33.4% | 35.5% |
| `Q2` | 1265 (122–131) | 0.3823 | 0.1769 | 193.0 | 55.7% | 36.5% | 26.7% | 36.4% |
| `Q3` | 1364 (133–142) | **0.5282** | **0.2608** | 204.7 | **71.6%** | **47.7%** | 22.8% | 29.3% |
| `Q4` | 1589 (148–168) | 0.3984 | 0.1824 | 184.5 | 52.5% | 45.2% | 26.3% | 27.9% |
| `Q5` (dày nhất) | 2005 (168–349) | 0.2920 | 0.1182 | 201.4 | 39.9% | 39.7% | 32.0% | 27.0% |

### 5.4 Sensitivity by Object Scale (In-Network Tile Pixel Area)

| Scale Bucket | GT Count (% GT) | Recall@0.001 | Recall@best (`0.0111`) | Recall@0.05 | Recall@0.25 | Hit `>= 0.1` IoU (`@best`) |
|---|---:|---:|---:|---:|---:|---:|
| `small` (`< 32² px`) | 2 (0.03%) | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| `medium` (`32²–96² px`) | 1401 (19.2%) | 46.4% | 24.1% | 12.8% | 2.5% | 44.2% |
| `large` (`>= 96² px`) | 5881 (80.7%) | 84.2% | 60.7% | 40.2% | 19.9% | **77.0%** |

Nhờ `tile=1024`, `80.7%` GT nằm ở nhóm `large` trong không gian đầu vào mạng và **77.0%** trong số đó đã có box phủ `>= 0.1 IoU` tại `best_conf_f1` — khẳng định mạng nhìn thấy phần lớn vật thể nhưng cần fine-tune để kéo độ chính xác khung (`IoU >= 0.50`) và nâng điểm tin cậy.

---

## 6. Visual Error Analysis (50 Inspected Images at `@conf = 0.0111`)

Kiểm tra trực quan toàn bộ 50 ảnh (`val_spike50`, xuất tại `training/baseline/visuals/yolo26s_1024_tile/`) cho thấy mô hình nhận diện rất tốt các kệ dạng chai/lọ/bình thẳng đứng (ví dụ `val_30.jpg` Q5 đạt **160/182 TP** — Recall 87.9%; `val_499.jpg` Q3 đạt **125/133 TP** — Recall 94.0%), nhưng gặp 5 nhóm lỗi hệ thống sau:

| # | Image (Stratum) | Expected (GT) | Actual (`@0.0111`) | Root-Cause Category | Visual Observation |
|---|---|---:|---|---|---|
| 1 | `val_167.jpg` (`Q1`) | 110 | `94 TP`, **`148 Loc`**, **`129 BG FP`**, `16 Missed` | **COCO sub-object hallucination & background leakage** | Hộp thuốc trẻ em (Nurofen, Hedrin, Lyclear) in ảnh khuôn mặt em bé/người trên bao bì → COCO-80 kích hoạt class `person` bên trong từng vỏ hộp tạo hàng loạt box `Loc`; kèm `BG FP` trên bảng chữ đầu kệ và dãy kệ xa phía sau. |
| 2 | `val_82.jpg` (`Q2`) | 127 | `73 TP`, `73 Loc`, **`165 BG FP`**, `54 Missed` | **Multi-pack granularity mismatch** | Kệ lốc bia 6-pack (`Shiner`, `Revolver`): GT gán nhãn cả hộp 6-pack là 1 sản phẩm, nhưng COCO-80 bắt từng cổ chai nhô ra trên miệng hộp thành `BG FP`/`Loc` và bỏ sót vỏ hộp lốc. |
| 3 | `val_63.jpg` (`Q1`) | 117 | `22 TP`, `51 Loc`, `31 BG FP`, **`95 Missed`** | **COCO-80 semantic gap (horizontal boxes/packages)** | Bắt tốt chai nước súc miệng `Listerine` tầng trên, nhưng bỏ sót gần như toàn bộ hộp kem đánh răng nằm ngang (`Colgate`, `2080`) bên dưới vì COCO-80 không có lớp hộp/gói bán lẻ; thay vào đó vẽ nhầm hình nhân vật hoạt hình in trên hộp và thẻ giá. |
| 4 | `val_451.jpg` (`Q5`) | 183 | **`12 TP`**, **`77 Loc`**, `43 BG FP`, **`171 Missed`** | **Tray occlusion & oblique camera angle** | Góc chụp xiên, chai nước ngọt nằm trong khay carton che nửa thân dưới: model chỉ khoanh phần đầu chai lộ trên mép khay (`Loc` do `IoU < 0.50` so với GT toàn thân chai) và sót các thùng nước xếp chồng bên dưới. |
| 5 | `val_504.jpg` (`Q5`) | 349 | `78 TP`, `20 Loc`, `26 BG FP`, **`271 Missed`** | **Extreme density of small rectangular boxes + tile-scale BG FP** | Ảnh dày nhất tập `val` (349 hộp thuốc nhỏ xếp khít): bỏ sót phần lớn hộp thuốc chữ nhật nhỏ, đồng thời xuất hiện các khung `BG FP` cỡ lớn bao nguyên mảng kệ hoặc đèn trần (COCO prior `tv`/`refrigerator`). |

---

## 7. Limitations & Next Steps

### Limitations
- **Không thể dùng ngưỡng `0.0111` trực tiếp cho production:** Dù tối ưu F1 của mô hình pretrained, `conf=0.0111` tạo `31.2%` `BG FP` (nhiều khung lớn phủ mảng kệ/bảng giá) và `28.2%` `Loc`, sẽ làm nhiễu nặng bước hậu xử lý gom hàng & phát hiện khoảng trống (`ADR-0002`, `ADR-0003`).
- **Tập đánh giá hiện tại là `val_spike50` (50 ảnh):** Đủ đại diện cho lựa chọn baseline Sprint 1, chưa phải đánh giá cuối cùng trên 200 ảnh `test` của NFR-01.
- **Độ trễ CPU khi bật `tile=1024` sát ngưỡng 5 s:** `p95 = 4756.2 ms` (max `6525.7 ms`) trên ảnh gốc ~8 MP.

### Next Steps (Sprint 2 → Sprint 3)
1. **Fine-tune `yolo26s.pt` đơn lớp `product` trên `sku110k-shelf-v2`** (1000 `train` / 200 `val`) để xóa bỏ hoàn toàn lệch ngữ nghĩa COCO-80 (`person` trên vỏ hộp, `BG FP` cỡ lớn, bỏ sót hộp/gói bán lẻ) và hướng tới mục tiêu **NFR-01 (`mAP@0.5 >= 0.75`)**.
2. **Hiệu chỉnh lại ngưỡng `conf_threshold` và so sánh single-pass vs tiling sau fine-tune:** Khi model đã học đúng phân bố sản phẩm SKU-110K, kiểm tra lại `imgsz=1024` / `1280` single-pass (với cạnh dài serving `<= 1920 px`) so với `tile=1024` để bảo đảm cả `mAP@0.5 >= 0.75` lẫn biên độ an toàn cho **NFR-03** trên CPU.
3. **Đánh giá cuối cùng trên tập `test` 200 ảnh** và tổng hợp vào `docs/EVAL_REPORT.md` + `models/<version>/MODEL_CARD.md` (Sprint 3).
4. **Ghi nhận quyết định model & bản quyền Ultralytics AGPL-3.0** (chỉ dùng nội bộ mục đích học tập) trong `docs/adr/0005-detector-model-and-license.md`.
