"""Print the unique file extensions found in all ZIP files in a folder.

Set ZIP_FOLDER below, then run:
    py list_zip_extensions.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path, PurePosixPath

# ---- Configuration --------------------------------------------------------
ZIP_FOLDER = Path(r"E:\_temp\Photo_Tagging\alben")
# --------------------------------------------------------------------------


def main() -> int:
    if not ZIP_FOLDER.is_dir():
        print(f"ZIP_FOLDER does not exist or is not a folder: {ZIP_FOLDER}", file=sys.stderr)
        return 2

    extensions: set[str] = set()
    archives = sorted(ZIP_FOLDER.glob("*.zip"))
    for archive_path in archives:
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    # ZIP paths always use forward slashes, including on Windows.
                    # Preserve case: .JPG and .jpg are reported separately.
                    extension = PurePosixPath(member.filename).suffix
                    extensions.add(extension or "[no extension]")
        except zipfile.BadZipFile:
            print(f"WARNING: skipped invalid ZIP: {archive_path}", file=sys.stderr)

    print(f"Scanned {len(archives)} ZIP file(s). Found {len(extensions)} unique extension(s):")
    for extension in sorted(extensions):
        print(extension)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
