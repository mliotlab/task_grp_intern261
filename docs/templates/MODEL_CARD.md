# Model Card – <model name> v<version>

## Model details

- **Architecture / base model:** <e.g. YOLOv8n, pretrained on COCO>
- **Version:** <semver> · **Date:** <dd/mm/yyyy> · **Owner:** <name>
- **Weights:** <download link> · **SHA-256:** `<checksum>`
- **License:** <license of the base model and of the fine-tuned weights>

## Intended use

<What it is for, who uses it. Out-of-scope uses.>

## Training data

<Dataset, subset, version, preprocessing, splits.>

## Training procedure

<Config file, hyper-parameters, seed, hardware, GPU hours.>

## Evaluation

| Metric | Split | Value |
|---|---|---|
| mAP@0.5 | test | |
| mAP@0.5:0.95 | test | |

## Limitations and biases

## How to load

```python
from shelfmon.inference import load_detector

detector = load_detector("models/<version>")
```
