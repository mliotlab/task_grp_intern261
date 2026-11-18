# Model registry

Each published model lives in its own folder. **Weights are never committed** (see root `.gitignore`);
only the model card and checksum are. Upload `weights.pt` to the lab drive / GitHub Release assets and
put the link in the model card.

```text
models/
└── <version>/                  e.g. yolov8n-sku-v1
    ├── MODEL_CARD.md           # data, training config, metrics, limits, license, download link
    ├── SHA256SUMS              # checksum verified at load time
    └── weights.pt              # downloaded locally, git-ignored
```

| Version | Base | Data | mAP@0.5 (test) | mAP@0.5:0.95 (test) | Download |
|---|---|---|---|---|---|
| `yolov8n-pretrained` | YOLOv8n COCO | — | _baseline_ | | Ultralytics release |
| `yolov8n-sku-v1` | YOLOv8n | sku110k-subset-v1 | | | |

Select the model served by the API with `MODEL_VERSION` in `.env`.
