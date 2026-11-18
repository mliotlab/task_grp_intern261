# Training pipeline (offline)

Produces an evaluated model and publishes it to the model registry (`models/<version>/`).
The online API only ever talks to the registry, never to this folder.

```mermaid
flowchart LR
  raw[SKU-110K raw<br/>images + CSV] --> prep[prepare_subset.py<br/>1000 / 200 / 200, seed]
  prep --> yolo[YOLO-format dataset<br/>data/sku110k_subset]
  yolo --> train[train.py<br/>fine-tune ≤ 10 GPU h]
  train --> eval[evaluate.py<br/>mAP@0.5, mAP@0.5:0.95]
  eval --> export[export_model.py<br/>weights + SHA256 + model card]
  export --> reg[(models/&lt;version&gt;)]
```

## Steps

```bash
pip install -e ".[ml]"                     # from retail-shelf-monitoring/

# 1. Download SKU-110K (Goldman et al., CVPR 2019) into data/raw/SKU110K_fixed/ (not committed)
# 2. Build the subset (deterministic, seed in the config)
python training/scripts/prepare_subset.py --config training/configs/data_subset.yaml
# 3. Baseline: evaluate the COCO-pretrained model first (NFR-01 requires both numbers)
python training/scripts/evaluate.py --weights yolov8n.pt --split test
# 4. Fine-tune
python training/scripts/train.py --config training/configs/train_yolov8n.yaml
# 5. Evaluate + publish to the registry
python training/scripts/evaluate.py --weights runs/detect/<run>/weights/best.pt --split test
python training/scripts/export_model.py --weights runs/detect/<run>/weights/best.pt --version yolov8n-sku-v1
```

## Reproducibility rules (NFR-06)

- Every run is driven by a committed config file; the seed and dataset version are in it.
- Results of every run are appended to `training/results.csv` (committed) — also log to MLflow / W&B if enabled.
- Total GPU budget for the whole project: **10 GPU-hours**. Log GPU time per run in `results.csv`.
