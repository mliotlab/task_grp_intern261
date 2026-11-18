# Reading list

## Week 1 – one paper per member

| # | Paper | Venue | Direction | Owner |
|---|---|---|---|---|
| [1] | Y.-H. Tsai et al., *Learning to Adapt Structured Output Space for Semantic Segmentation* (**AdaptSegNet**) | CVPR 2018 | Adversarial alignment in output space | Member 1 |
| [2] | W. Tranheden et al., *DACS: Domain Adaptation via Cross-domain Mixed Sampling* | WACV 2021 | Self-training + cross-domain mixing | Member 2 |
| [3] | L. Hoyer, D. Dai, L. Van Gool, *DAFormer: Improving Network Architectures and Training Strategies for Domain-Adaptive Semantic Segmentation* | CVPR 2022 | Transformer + training strategies (used for the Week-3 demo) | Member 3 |

## Background

| # | Paper | Why |
|---|---|---|
| [4] | S. R. Richter et al., *Playing for Data: Ground Truth from Computer Games* | ECCV 2016 – the GTA5 dataset |
| [5] | M. Cordts et al., *The Cityscapes Dataset for Semantic Urban Scene Understanding* | CVPR 2016 – target domain + metric |
| [6] | L. Hoyer et al., *HRDA: Context-Aware High-Resolution Domain-Adaptive Semantic Segmentation* | ECCV 2022 – follow-up to DAFormer |
| [7] | L. Hoyer et al., *MIC: Masked Image Consistency for Context-Enhanced Domain Adaptation* | CVPR 2023 – current strong baseline |

> Numbers reported by different papers use different backbones and settings — never compare them
> as if they were run under the same conditions; always cite where each number comes from.

## How to read (three-pass method)

1. **Pass 1 (≈ 15 min):** title, abstract, figures, conclusion — what problem, what idea?
2. **Pass 2 (≈ 2 h):** method and experiments — inputs/outputs, components, datasets, main table, ablation.
3. **Pass 3 (optional):** details needed to explain or reproduce a specific part.

Write notes in `papers/notes/<short-name>.md` using [`notes/_template.md`](notes/_template.md).
