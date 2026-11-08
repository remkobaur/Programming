"""Tag images by comparing them with the contents of ZIP archives.

Set ZIP_FOLDER and SEARCH_FOLDER below, then run:
    py tag_images_from_zips.py

Each ZIP file name becomes a tag.  For example, ``Baiersbronn 2019.zip``
adds the tag ``Baiersbronn 2019`` to every matching image.  A match requires
both the same file name and the same byte size.  ZIP member directories are
ignored, so ``photos/IMG_1216.JPG`` matches ``IMG_1216.JPG`` anywhere below
SEARCH_FOLDER.

This script uses ExifTool because it reliably writes the metadata which
Windows Explorer shows as "Tags" / "Markierungen".  Install it once from
https://exiftool.org/ and either put ``exiftool.exe`` on PATH or set
EXIFTOOL below to its full path.
"""

from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

# ---- Configuration --------------------------------------------------------
ZIP_FOLDER = Path(r"E:\_temp\Photo_Tagging\alben2")
SEARCH_FOLDER = Path(r"E:\_temp\Photo_Tagging\Nas")
SEARCH_FOLDER = Path(r"\\irbmedserv\photo")

# Use None when exiftool.exe is on PATH, otherwise use e.g.
# Path(r"C:\Tools\exiftool.exe")
EXIFTOOL: Path | None = None

# Leave True for the first run.  It prints the planned changes without
# changing image metadata.  Change to False to actually write the tags.
DRY_RUN = False

# ExifTool will be invoked only for these usual image formats.  Add formats
# if your library contains other image types supported by ExifTool.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".heic", ".mp4"}
# --------------------------------------------------------------------------


def zip_members_by_key(zip_folder: Path) -> dict[tuple[str, int], set[str]]:
    """Return { (lower-case file name, uncompressed size): {tags} }."""
    matches: dict[tuple[str, int], set[str]] = defaultdict(set)
    for archive_path in sorted(zip_folder.glob("*.zip")):
        tag = archive_path.stem
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    name = Path(member.filename).name
                    if name:
                        matches[(name.casefold(), member.file_size)].add(tag)
        except zipfile.BadZipFile:
            print(f"WARNING: skipped invalid ZIP: {archive_path}", file=sys.stderr)
    return matches


def iter_files_deep(folder: Path):
    """Yield files recursively without building a list (suitable for a NAS)."""
    for root, _dirs, files in os.walk(folder):
        for name in files:
            yield Path(root) / name


def exiftool_command() -> str:
    if EXIFTOOL is not None:
        return str(EXIFTOOL)
    found = shutil.which("exiftool") or shutil.which("exiftool.exe")
    if not found:
        raise RuntimeError("ExifTool was not found. Install it or set EXIFTOOL.")
    return found


def existing_tags(image: Path, tool: str) -> set[str]:
    """Read tag values already stored in the Windows-compatible fields."""
    command = [
        tool, "-j", "-XMP-dc:Subject", "-IPTC:Keywords", "-EXIF:XPKeywords", str(image),
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ExifTool could not read metadata")

    records = json.loads(result.stdout)
    if not records:
        return set()
    values: set[str] = set()
    for field in ("Subject", "Keywords", "XPKeywords"):
        value = records[0].get(field)
        if isinstance(value, list):
            values.update(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, str):
            # XPKeywords is commonly returned as a semicolon-separated string.
            values.update(part.strip() for part in value.split(";") if part.strip())
    return values


def add_tags(image: Path, tags: set[str], tool: str) -> bool:
    # Write the common Windows-compatible keyword fields.  -P preserves the
    # original file modification time and -overwrite_original avoids *_original
    # backup files.  ExifTool handles each supported image format appropriately.
    command = [tool, "-overwrite_original", "-P", "-m"]
    for tag in sorted(tags, key=str.casefold):
        command.extend((f"-XMP-dc:Subject+={tag}", f"-IPTC:Keywords+={tag}", f"-EXIF:XPKeywords+={tag}"))
    command.append(str(image))
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        print(f"ERROR tagging {image}: {result.stderr.strip()}", file=sys.stderr)
        return False
    else:
        print(f"TAGGED  {image}  ->  {'; '.join(sorted(tags, key=str.casefold))}")
        return True


def main() -> int:
    if not ZIP_FOLDER.is_dir():
        print(f"ZIP_FOLDER does not exist or is not a folder: {ZIP_FOLDER}", file=sys.stderr)
        return 2
    if not SEARCH_FOLDER.is_dir():
        print(f"SEARCH_FOLDER does not exist or is not a folder: {SEARCH_FOLDER}", file=sys.stderr)
        return 2

    keys_to_tags = zip_members_by_key(ZIP_FOLDER)
    print(f"Read {len(list(ZIP_FOLDER.glob('*.zip')))} ZIP file(s), {len(keys_to_tags)} unique name/size entries.")
    if not keys_to_tags:
        return 0

    # Reading existing tags is necessary to make both dry and real runs safe
    # to repeat, so ExifTool is required in either mode.
    tool = exiftool_command()
    found = changed = already_present = 0
    for image in iter_files_deep(SEARCH_FOLDER):
        if image.suffix.casefold() not in IMAGE_EXTENSIONS:
            continue
        try:
            tags = keys_to_tags.get((image.name.casefold(), image.stat().st_size))
        except OSError as error:
            print(f"WARNING: cannot read {image}: {error}", file=sys.stderr)
            continue
        if not tags:
            continue
        found += 1
        try:
            current = existing_tags(image, tool)
        except (RuntimeError, json.JSONDecodeError) as error:
            print(f"ERROR reading tags from {image}: {error}", file=sys.stderr)
            continue
        current_normalized = {tag.casefold() for tag in current}
        missing = {tag for tag in tags if tag.casefold() not in current_normalized}
        if not missing:
            already_present += 1
            print(f"UNCHANGED  {image}  (all requested tags already exist)")
        elif DRY_RUN:
            print(f"WOULD TAG  {image}  ->  {'; '.join(sorted(missing, key=str.casefold))}")
        elif add_tags(image, missing, tool):
            changed += 1

    if DRY_RUN:
        print(f"Done: {found} matching image(s) checked; {already_present} already had all requested tags.")
    else:
        print(f"Done: {changed} image(s) tagged; {already_present} already had all requested tags.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
