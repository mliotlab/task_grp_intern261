# Environment (Week 3)

DAFormer is built on **mmsegmentation 0.x** and pins old versions of PyTorch / mmcv (see
`external/DAFormer/README.md` and `requirements.txt`). The mentor provides a ready environment
(conda env or Docker image) and the GTA5 → Cityscapes checkpoint — **do not** try to install it from
scratch on a laptop without a GPU.

Record here exactly what you used, so someone else can reproduce your results:

| Item | Value |
|---|---|
| Machine / GPU | |
| OS | |
| Python | |
| PyTorch / CUDA | |
| mmcv / mmseg | |
| DAFormer commit | `git -C external/DAFormer rev-parse HEAD` → |
| Config file | |
| Checkpoint file + SHA-256 | |

## Steps

```bash
git clone https://github.com/lhoyer/DAFormer external/DAFormer
# activate the mentor-provided environment, then from sim2real-segmentation/:
python external/DAFormer/demo/image_demo.py <image> <config.py> <checkpoint.pth>
```

## Troubleshooting log

| Date | Error | What we tried | Result |
|---|---|---|---|
