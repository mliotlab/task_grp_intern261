# Sim2Real Domain Adaptation in Semantic Segmentation (GTA5 → Cityscapes)

> A 4-week mini research project: survey unsupervised domain adaptation (UDA) for semantic
> segmentation, explain one method in depth, run a pretrained **DAFormer** on synthetic, real-world
> and **Vietnamese street** images, and analyse where the Sim2Real gap remains.

| | |
|---|---|
| **Track** | Research Familiarization |
| **Members** | [Member 1] · [Member 2] · [Member 3] |
| **Mentor** | [Mentor name] |
| **Timeline** | 4 weeks · 5–7 h/person/week |
| **Status** | 🚧 Week 0 – scaffold |

## Highlights

- Structured **literature review** of three UDA families: adversarial alignment (AdaptSegNet), self-training with cross-domain mixing (DACS), Transformer-based training strategies (DAFormer)
- **Reproduced inference** of a state-of-the-art UDA model from its public implementation
- **Out-of-distribution study** on Vietnamese street scenes (motorbike-dense traffic, signage) not seen in GTA5 or Cityscapes
- Evidence-based **qualitative error analysis** (observation → hypothesis) and a written report + talk

## The problem in one paragraph

Pixel-level labels for real images are expensive (≈ 1.5 h per Cityscapes image), while game engines
such as GTA5 produce labels for free (24,966 labeled frames). A model trained only on GTA5 loses much
of its accuracy on real streets because textures, lighting and object shapes differ (**domain shift**).
**UDA** trains with labeled source images (GTA5) plus *unlabeled* target images (Cityscapes) to close
that gap. Evaluation uses **mIoU** over the 19 shared classes on the 500 Cityscapes validation images.

## Repository structure

```text
sim2real-segmentation/
├── deliverables/            # one folder per weekly deliverable (mirrors the shared Drive /W1…/W4, /Final)
│   ├── W1/                  # 3-paper summary table + 4 intro slides
│   ├── W2/                  # methodology diagram + 1–2 page explanation
│   ├── W3/                  # demo + results + observation notes
│   ├── W4/                  # analysis notes, report & slide drafts
│   └── Final/               # final report PDF, slides, contribution table
├── papers/                  # reading list + per-paper notes
├── s2r_tools/               # shared helpers: Cityscapes palette, side-by-side figures, name checks
├── scripts/                 # run_folder_inference.py (Week 3)
├── notebooks/               # exploration notebooks (clear outputs before committing large images)
├── results/                 # <domain>_<nn>.png figures (gta_01, cs_01, vn_01, ...)
├── data/                    # input images (git-ignored, see data/README.md)
├── checkpoints/             # DAFormer weights from the mentor (git-ignored)
├── external/                # DAFormer source clone (git-ignored)
├── docs/                    # environment setup, weekly report template, contribution log
└── tests/                   # tests for s2r_tools (run in CI)
```

## Weekly plan

| Week | Research step | Team deliverable | Done when |
|---|---|---|---|
| 1 | **Explore the topic** – each member reads one paper | [3-paper summary table + 4 slides](deliverables/W1/) | Problem stated in our own words; ≥ 1 limitation per paper; same comparison criteria |
| 2 | **Understand the method** (DAFormer recommended) | [Methodology diagram + 1–2 page explanation](deliverables/W2/) | Diagram shows source/target data flow; every component's role explained; any member can explain all of it |
| 3 | **Experiment** – run pretrained DAFormer | [Runnable code + results + observation notes](deliverables/W3/) | Someone outside the team can re-run it from the README; GTA5, Cityscapes and Vietnam images; ≥ 5 "observation → hypothesis" notes |
| 4 | **Analyse & present** | [3–5 page report + 8–10 slides + 15-min talk](deliverables/Final/) | Every claim backed by a figure, table or paper; contribution table included |

Rhythm: **Monday** ≤ 15-min planning · **Thursday** internal deadline · **Friday** submit + 20-min check-in.
Weekly lead rotates: W1 → Member 1, W2 → Member 2, W3 → Member 3, W4 → Member 1.

## Quick start (Week 3)

```bash
# 1. Environment and checkpoint are provided by the mentor – see docs/ENVIRONMENT.md
git clone https://github.com/lhoyer/DAFormer external/DAFormer
# 2. Put images in data/gta, data/cs, data/vn (see data/README.md)
# 3. Run on a folder
python scripts/run_folder_inference.py --config <cfg.py> --checkpoint checkpoints/<ckpt>.pth \
    --input data/vn --domain vn --out results
```

Helper tests (also run in CI): `pip install pytest numpy pillow && pytest -q`.

## Grading (from the project brief)

| Team – 70 % | | Individual – 30 % | |
|---|---|---|---|
| Problem & motivation (W1 table, slides) | 15 % | On time & progress (tracker, weekly report) | 10 % |
| Literature review (3-paper comparison, limitations) | 15 % | Quality of own work (named sections) | 10 % |
| Understanding the method (W2) | 15 % | Q&A & check-ins (can explain the whole project) | 10 % |
| Experiments & observations (W3) | 15 % | | |
| Report & presentation (W4) | 10 % | | |

## Out of scope

Training models, implementing algorithms from scratch, or claiming new contributions.

## References

See [`papers/README.md`](papers/README.md).

## Licenses

| Component | License / terms |
|---|---|
| This code (`s2r_tools`, `scripts`) | MIT |
| DAFormer | See the license file of `lhoyer/DAFormer` (check before redistributing anything) |
| GTA5 (Playing for Data) | Research use, see dataset page |
| Cityscapes | Cityscapes license – non-commercial research; images may **not** be redistributed, so do not commit them |
| Vietnamese street photos | Taken by the team or with a license that allows reuse; record the source of each image |
