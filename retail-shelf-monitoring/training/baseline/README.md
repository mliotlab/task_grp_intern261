# Pretrained Baseline Evaluation (Issue #14)

Thư mục này chứa script tái lập đánh giá model baseline **`yolo26s.pt`** (pretrain Objects365-v1 → COCO, không rò rỉ dữ liệu SKU-110K) trên **50 ảnh phân tầng `val_spike50`** của bộ **`sku110k-shelf-v2`**.

Báo cáo tổng kết chính thức nằm tại [`docs/reports/baseline_yolo26s.md`](../../docs/reports/baseline_yolo26s.md).

## Scripts

- `common.py`: Tạo/tải manifest phân tầng `val_spike50.csv` (5 tầng mật độ `Q1`–`Q5`, `seed=2026`), tính `mAP@0.5`, `mAP@0.5:0.95`, phân rã lỗi hình học TIDE, độ nhạy theo tầng mật độ & kích thước, đo độ trễ GPU/CPU và xuất ảnh trực quan.
- `eval_yolo26s.py`: Chạy đánh giá `yolo26s.pt` (`imgsz=1024`, `tile=1024`, `agnostic_nms=True`, `max_det=1000`, `end2end=True`, gộp 80 class COCO về `product`), tự động dùng ngưỡng `best_conf_f1` cho đo độ trễ & xuất đủ 50 ảnh kiểm tra trực quan.

## Cách chạy lại (từ `retail-shelf-monitoring/`)

```bash
python training/baseline/eval_yolo26s.py
```

Các file kết quả đầu ra (`results/`, `visuals/`, `YOLO26S_BASELINE_LOCAL.md`) được gitignore để giữ repo gọn nhẹ; chỉ commit script, manifest `val_spike50.csv`, dòng log trong `training/results.csv` và báo cáo trong `docs/reports/baseline_yolo26s.md`.
