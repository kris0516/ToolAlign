"""Read Hatchling's selection without creating an archive or printing private paths.

Run with: uv run --locked --with hatchling==1.27.0 python
reports/hardware/P01_CHECK_SDIST_SELECTION.py
An exit code of 1 means a private file would be included in the sdist.
"""

import json
from pathlib import Path

from hatchling.builders.sdist import SdistBuilder

builder = SdistBuilder(str(Path.cwd()))
count = total_bytes = private_count = 0
for entry in builder.recurse_included_files():
    count += 1
    total_bytes += Path(entry.path).stat().st_size
    private_count += entry.relative_path.startswith(".toolalign-local/")
print(
    json.dumps(
        {
            "selected_files": count,
            "selected_bytes": total_bytes,
            "private_files": private_count,
            "git_marker_is_file": Path(".git").is_file(),
            "archive_created": False,
        }
    )
)
raise SystemExit(1 if private_count else 0)
