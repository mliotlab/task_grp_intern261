# Week 3 – Experiment: run pretrained DAFormer

**Goal:** run the demo and observe model behaviour. Environment + GTA5 → Cityscapes checkpoint are
provided by the mentor. **No training, no full GTA5 download.**

| Member | Task |
|---|---|
| Member 1 | Set up and run `demo/image_demo.py` on the sample image; implement `scripts/run_folder_inference.py`; write the run instructions in the project README |
| Member 2 | Run on 5 GTA5 + 5 Cityscapes images (from the mentor); compare which classes are right/wrong in each domain |
| Member 3 | Collect and run on 10 Vietnamese street photos; optional: change resolution or brightness on 3–5 images; note frequently wrong classes (motorbike, signs, …) |

## Deliverables (Drive `/W3` + repo link)

1. **Runnable code** – script/notebook + README (environment, commands, checkpoint path, folder layout).
2. **Results folder** – `results/<domain>_<nn>.png` (`gta_01`, `cs_01`, `vn_01`, …), input and prediction side by side with the shared legend (`s2r_tools.figures.side_by_side`).
3. **Observation notes (1–2 pages)** – [`OBSERVATIONS.md`](OBSERVATIONS.md), ≥ 5 notes, each tied to a specific image.

## Passes when

Someone outside the team can re-run it from the README · all three image groups are present ·
notes separate *what we see* from *why we think so* · if something did not run, the error, the steps
tried and the final state are documented.
