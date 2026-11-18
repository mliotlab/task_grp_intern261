# Results

Side-by-side figures named `<domain>_<nn>.png` (`gta_01.png`, `cs_01.png`, `vn_01.png`, …), produced by
`scripts/run_folder_inference.py`. Check names with:

```python
from pathlib import Path
from s2r_tools.figures import invalid_result_names

print(invalid_result_names(Path("results")))  # should print []
```

Do **not** commit figures that contain Cityscapes images if the repository is public — keep those on the
shared Drive and commit only GTA5 / own-photo figures. Keep each PNG under ~1 MB (pre-commit blocks larger files).
