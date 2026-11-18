r"""Run the pretrained DAFormer (GTA5 → Cityscapes) on every image in a folder (Week 3, Member 1).

Run inside the mentor-provided DAFormer environment, from this project folder:

    python scripts/run_folder_inference.py \
        --config external/DAFormer/configs/daformer/<config-matching-the-checkpoint>.py \
        --checkpoint checkpoints/daformer_gta2cs.pth \
        --input data/vn --domain vn --out results

Writes `<out>/raw/<domain>_<nn>.npy` (label maps) and `<out>/<domain>_<nn>.png`
(side-by-side figure). Use the config that matches the checkpoint provided by the mentor.
"""

from __future__ import annotations

import argparse
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def list_images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--domain", choices=["gta", "cs", "vn"], required=True)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    images = list_images(args.input)
    print(f"{len(images)} images in {args.input}")

    # TODO(Week 3 – Member 1). DAFormer is built on mmsegmentation 0.x:
    #   from mmseg.apis import inference_segmentor, init_segmentor
    #   model = init_segmentor(args.config, args.checkpoint, device=args.device)
    #   for i, path in enumerate(images, start=1):
    #       pred = inference_segmentor(model, str(path))[0]   # HxW train ids
    #       np.save(args.out / "raw" / f"{args.domain}_{i:02d}.npy", pred)
    #       side_by_side(Image.open(path), pred).save(args.out / f"{args.domain}_{i:02d}.png")
    #   Compare with external/DAFormer/demo/image_demo.py; note any changes in the README.
    raise SystemExit("Not implemented yet – see TODO above.")


if __name__ == "__main__":
    main()
