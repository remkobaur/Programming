"""Find geographic coordinates from location-like folder names.

Set SEARCH_FOLDER below, then run:
    py find_folder_locations.py

For example, ``2019_07_21_Baiersbronn`` becomes the search term
``Baiersbronn``.  It adds GPS coordinates to image files only when they have
no existing GPS location.

Results come from OpenStreetMap's Nominatim service.  A one-second pause is
kept between requests, as required by its public usage policy.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---- Configuration --------------------------------------------------------
SEARCH_FOLDER = Path(r"E:\_temp\Photo_Tagging\Nas\Urlaub\2020_08_10_Weimar")
SEARCH_FOLDER = Path(r"\\irbmedserv\photo\Urlaub")

# Leave as None to search worldwide.  Set, for example, "Germany" only when
# every folder in the scanned collection is known to be in that country.
COUNTRY: str | None = None
RECURSIVE = True      # False checks only immediate child folders.
MAX_PARENT_DISTANCE_KM = 250
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic"}
AUTO_GPS_TAG = "GPS-auto-tagged-by-path"

# Enabled for safety: list planned GPS/tag changes without modifying files.
# Change to False only after reviewing the output.
DRY_RUN = False

# Set False to process every folder location without enumerating image files,
# reading GPS metadata, or writing tags. This is faster for location review.
CHECK_IMAGE_FILES = True

# Completion markers are created only in active image-tagging mode
# (DRY_RUN = False and CHECK_IMAGE_FILES = True). Marked folder trees are
# skipped on later runs when this option is enabled.
SKIP_ALREADY_TAGGED_FOLDERS = True
TAGGED_MARKER_NAME = "tagged"

# Use None when exiftool.exe is on PATH, otherwise set its full path, e.g.
# Path(r"C:\Tools\exiftool.exe"). ExifTool reads and writes GPS metadata.
EXIFTOOL: Path | None = None

# The workbook is recreated after each completed run. Its Valid column is
# intentionally left blank for manual review in Excel.
EXCEL_REPORT = Path(__file__).with_name("folder_location_review.xlsx")
# Words/phrases used as labels rather than location names. Add your own
# recurring labels here; comparison is case-insensitive. Underscores in a
# phrase also match spaces or hyphens (for example, "Best Of").
NON_LOCATION_WORDS = {
    "ira", "remko", "jannek", "dcim", "best_of", "lift", "ostern",
    "weihnachten", "wasserspaß","Femke","Urlaub","Mosel","CANON","Andere","Christina",
    "Bestof"
}
NON_LOCATION_WORDS.add("Wandern")
NON_LOCATION_WORDS.add("Skifreizeit")
NON_LOCATION_WORDS.add("Rest")
NON_LOCATION_WORDS.add("Papa")
NON_LOCATION_WORDS.add("Ludwig")
NON_LOCATION_WORDS.add("Fasching")
NON_LOCATION_WORDS.add("Auslandssemester")
NON_LOCATION_WORDS.add("Comics")
NON_LOCATION_WORDS.add("Herbstferien")
NON_LOCATION_WORDS.add("Handy")
NON_LOCATION_WORDS_NORMALIZED = {word.casefold() for word in NON_LOCATION_WORDS}
# Use this for album locations that are ambiguous in OpenStreetMap. Keys are
# the extracted folder names (case-insensitive); values are precise queries.
LOCATION_QUERY_OVERRIDES = {
    "weimar": "Weimar, Thüringen, Deutschland",
    "moskau": "Moscow, Russia",
    "prag": "Prague, Czechia",
    "dänemark": "Denmark",
    "andalusien": "Andalusia, Spain",
    "madeira": "Madeira Island, Portugal",
    "nagoldtalsperre": "Nagoldtalsperre, Seewald, Germany",
    "ruhestein": "Ruhestein, Seebach, Germany",
    "sankenbachsee": "Sankenbachsee, Baiersbronn, Germany",
    "königsstein festung": "Festung Königstein, Sachsen, Germany",
    "datong": "Datong, Shanxi, China",
    "peking verbotene stadt": "Forbidden City, Beijing, China",
    "peking": "Beijing, China",
    "nordsee": "North Sea, Germany",
    "harz": "Harz, Germany",
    "tuebingen": "Tübingen, Germany",
    "bayrischer wald": "Bayerischer Wald, Germany",
    "schloss dankern": "Schloss Dankern, Haren (Ems), Germany",
    "stolpen": "Stolpen, Sachsen, Germany",
    "landal hochwald park kell am see": "Landal Hochwald, Kell am See, Germany",
    "comer see": "Lake Como, Italy",
    "klaistow blaubeeren": "Erlebnishof Klaistow, Beelitz, Germany",
    "wernigerode": "Wernigerode, Sachsen-Anhalt, Germany",
    "lübben": "Lübben (Spreewald), Brandenburg, Germany",
    "mallorca alcudia": "Alcúdia, Mallorca, Spain",
    "zutphen": "Zutphen, Netherlands",
    "thonon": "Thonon-les-Bains, France",
    "clausthal": "Clausthal-Zellerfeld, Germany",
    "hongkong": "Hong Kong, China",
    "femarn": "Fehmarn, Germany",
    "brocken": "Brocken, Harz, Germany",
    "st p ording": "Sankt Peter-Ording, Germany",
    "kärnten": "Carinthia, Austria",
    "ötztal96": "Ötztal, Tyrol, Austria",
    "istanbul": "Istanbul, Türkiye",
    "spanien": "Spain",
    "bulgarien": "Bulgaria",
    "altenmarkt": "Altenmarkt im Pongau, Austria",
    "dolomiten": "Dolomites, Italy",
    "spanien empuriabrava": "Empuriabrava, Spain",
    "norwegen": "Norway",
    "stubeital": "Stubaital, Austria",
    "besancon": "Besançon, France",
    "slowenien": "Slovenia",
    "soller alfabia": "Jardins d'Alfàbia, Bunyola, Mallorca, Spain",
    "kreta": "Crete, Greece",
    "side": "Side, Antalya, Türkiye",
    "zoo hannover": "Zoo Hannover, Germany",
    "riesengebirge polen": "Karkonosze, Poland",
    "brook": "Brook, Kalkhorst, Mecklenburg-Vorpommern, Germany",
    "nationalpark bayrischerwald": "Bavarian Forest National Park, Germany",
    "frankreich": "France",
    "london": "London, United Kingdom",
    "china hk": "China",
    "östereich": "Austria",
    "mauterndorf": "Mauterndorf, Salzburg, Austria",
}
# Use exact folder-name overrides when a generic name (such as Mosel) has a
# different intended location in a particular album.
FOLDER_NAME_QUERY_OVERRIDES = {
    "2022_10_mosel": ("Traben-Trarbach", "Traben-Trarbach, Germany"),
}
# Folder names that use a local-language spelling while the map's primary
# location name uses another spelling.
LOCATION_NAME_ALIASES = {
    "moskau": "Moscow",
    "prag": "Prague",
    "dänemark": "Denmark",
    "andalusien": "Andalusia",
    "königsstein festung": "Festung Königstein",
}
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "photo-folder-location-helper/1.0 (personal local metadata tool)"
# --------------------------------------------------------------------------


def location_text(folder_name: str) -> str | None:
    """Extract a plausible location from an album-style folder name.

    Numeric date/time pieces are removed wherever they occur.  Separators
    (underscore, dash and dot) become spaces, while ordinary location text is
    retained.  A plus sign starts an additional description/event and is not
    part of the location.  Examples:
      2019_07_21_Baiersbronn -> Baiersbronn
      Baiersbronn-2019       -> Baiersbronn
      2009_12_Moskau+Hochzeit -> Moskau
    """
    def usable_words(text: str) -> list[str]:
        pieces = re.split(r"[_\-.\s]+", remove_non_location_phrases(text))
        return [
            piece
            for piece in pieces
            if not re.fullmatch(r"\d{1,8}", piece)
            and not re.fullmatch(
                r"(?:jan|januar|feb|februar|mär|märz|mae|mar|apr|april|mai|jun|juni|jul|juli|aug|august|sep|september|okt|oktober|nov|november|dez|dezember)\d{2,4}",
                piece,
                flags=re.IGNORECASE,
            )
            and piece.casefold() not in NON_LOCATION_WORDS_NORMALIZED
        ]

    parts = folder_name.split("+")
    words = usable_words(parts[0])
    # Usually text after '+' is an event label. If the first part is only an
    # ignored person/name, however, the following part can contain the place.
    if not words and len(parts) > 1:
        words = usable_words(" ".join(parts[1:]))
    text = " ".join(words).strip()
    return text or None


def remove_non_location_phrases(text: str) -> str:
    """Remove configured multi-word ignored phrases before tokenizing."""
    for ignored in NON_LOCATION_WORDS:
        if "_" in ignored:
            pattern = re.escape(ignored).replace("_", r"[_\s-]+")
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def geocode_results(query: str, limit: int = 1) -> list[dict[str, object]]:
    parameters = urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": str(limit)})
    request = urllib.request.Request(f"{NOMINATIM_URL}?{parameters}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            results = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"ERROR searching {query!r}: {error}", file=sys.stderr)
        return []
    return results


def normalized_name(text: str) -> str:
    """Normalize spacing/case for an exact location-name comparison."""
    return " ".join(re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE))


def has_exact_location_name(result: dict[str, object], expected_name: str) -> bool:
    """Match the expected name as whole consecutive words in the map label."""
    expected_words = normalized_name(expected_name).split()
    result_words = normalized_name(str(result.get("display_name", ""))).split()
    if not expected_words:
        return False
    # Whole-word comparison accepts "Ruhestein, Seebach" or
    # "Nagoldtalsperre Erzgrube", but rejects "Ruhesteiner".
    width = len(expected_words)
    return any(result_words[index:index + width] == expected_words for index in range(len(result_words) - width + 1))


def geocode(query: str, expected_name: str | None = None) -> dict[str, object] | None:
    # Request multiple candidates so an exact-name result is not hidden behind
    # a similar but augmented name such as "La Moselle" for "Mosel".
    results = geocode_results(query, limit=10 if expected_name else 1)
    if expected_name:
        exact_matches = [result for result in results if has_exact_location_name(result, expected_name)]
        # Never guess between identically named places.  A missing location is
        # safer than applying GPS coordinates for the wrong "Mosel", etc.
        if len(exact_matches) == 1:
            return exact_matches[0]
        # A city may additionally have a same-name administrative record.
        # When there is one unambiguous city result, it is safe to prefer it;
        # a town/village match alone (such as Mosel near Zwickau) is not.
        cities = [
            result for result in exact_matches
            if str(result.get("addresstype", "")).casefold() == "city"
            or str(result.get("type", "")).casefold() == "city"
        ]
        return cities[0] if len(cities) == 1 else None
    return results[0] if results else None


def search_query(location: str, near: str | None = None) -> str:
    parts = [location]
    if near:
        parts.append(near)
    if COUNTRY:
        parts.append(COUNTRY)
    return ", ".join(parts)


def distance_km(first: dict[str, object], second: dict[str, object]) -> float | None:
    """Return great-circle distance between two Nominatim results in km."""
    try:
        from math import asin, cos, radians, sin, sqrt

        latitude_1, longitude_1 = radians(float(first["lat"])), radians(float(first["lon"]))
        latitude_2, longitude_2 = radians(float(second["lat"])), radians(float(second["lon"]))
    except (KeyError, TypeError, ValueError):
        return None
    latitude_delta = latitude_2 - latitude_1
    longitude_delta = longitude_2 - longitude_1
    value = sin(latitude_delta / 2) ** 2 + cos(latitude_1) * cos(latitude_2) * sin(longitude_delta / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(value))


def is_near_parent(child: dict[str, object] | None, parent: dict[str, object] | None) -> bool:
    """Accept a child result when no parent exists or it is close enough."""
    if child is None or parent is None:
        return child is not None
    distance = distance_km(child, parent)
    if distance is None:
        return False
    if distance > MAX_PARENT_DISTANCE_KM:
        print(f"REJECTED  child result is {distance:.1f} km from its parent (limit: {MAX_PARENT_DISTANCE_KM} km)")
        return False
    return True


def unique_location_component(folder: Path, parent: dict[str, object]) -> tuple[str, str, dict[str, object]] | None:
    """Find one unambiguous, nearby location word from a compound folder name."""
    pieces = re.split(r"[_\-.\s+]+", remove_non_location_phrases(folder.name))
    terms = list(dict.fromkeys(
        piece for piece in pieces
        if not re.fullmatch(r"\d{1,8}", piece) and len(piece) > 2 and piece.casefold() not in NON_LOCATION_WORDS_NORMALIZED
    ))
    for term in terms:
        query = search_query(term)
        results = geocode_results(query, limit=10)
        time.sleep(1)
        # A generic word (such as "Lift") normally has many results.  Accept
        # only an exactly unique result, then apply the parent-distance check.
        if len(results) == 1 and has_exact_location_name(results[0], term) and is_near_parent(results[0], parent):
            return term, query, results[0]
    return None


LOOKUP_CACHE: dict[tuple[Path, str | None], tuple[str | None, str | None, dict[str, object] | None]] = {}


def lookup_folder_name(
    folder: Path, near: str | None = None
) -> tuple[str | None, str | None, dict[str, object] | None]:
    """Return the candidate, query and result for one folder name."""
    cache_key = (folder, near)
    if cache_key in LOOKUP_CACHE:
        return LOOKUP_CACHE[cache_key]
    folder_override = FOLDER_NAME_QUERY_OVERRIDES.get(folder.name.casefold())
    candidate = folder_override[0] if folder_override else location_text(folder.name)
    if not candidate:
        answer = (None, None, None)
        LOOKUP_CACHE[cache_key] = answer
        return answer
    # A precise configured query avoids guessing between identically named
    # places. Parent context still takes precedence for ordinary folder names.
    override_query = folder_override[1] if folder_override else LOCATION_QUERY_OVERRIDES.get(candidate.casefold())
    query = override_query or search_query(candidate, near)
    # Explicit overrides are manually selected precise locations, so do not
    # reject them merely because the service displays another language/spelling.
    expected_name = None if override_query else LOCATION_NAME_ALIASES.get(candidate.casefold(), candidate)
    result = geocode(query, expected_name)
    # Public Nominatim requests must not exceed one request per second.
    time.sleep(1)
    answer = (candidate, query, result)
    LOOKUP_CACHE[cache_key] = answer
    return answer


def iter_subfolders(folder: Path):
    # Include the selected folder itself: it may directly contain images even
    # when it has no child folders.
    if SKIP_ALREADY_TAGGED_FOLDERS and has_tagged_marker(folder):
        print(f"SKIPPED  {folder}  (already marked as tagged)")
        return
    yield folder
    if RECURSIVE:
        for root, directories, _files in os.walk(folder):
            root_path = Path(root)
            if SKIP_ALREADY_TAGGED_FOLDERS:
                directories[:] = [name for name in directories if not has_tagged_marker(root_path / name)]
            for name in directories:
                yield root_path / name
    else:
        for path in folder.iterdir():
            if path.is_dir() and not (SKIP_ALREADY_TAGGED_FOLDERS and has_tagged_marker(path)):
                yield path


def has_tagged_marker(folder: Path) -> bool:
    return (folder / TAGGED_MARKER_NAME).is_file()


def exiftool_command() -> str:
    if EXIFTOOL is not None:
        return str(EXIFTOOL)
    found = shutil.which("exiftool") or shutil.which("exiftool.exe")
    if not found:
        raise RuntimeError("ExifTool was not found. Install it or set EXIFTOOL.")
    return found


def images_and_subfolders(folder: Path) -> tuple[list[Path], bool]:
    """Return immediate image files and whether this folder has subfolders."""
    images: list[Path] = []
    has_subfolders = False
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    has_subfolders = True
                elif Path(entry.name).suffix.casefold() in IMAGE_EXTENSIONS:
                    images.append(Path(entry.path))
    except OSError as error:
        print(f"WARNING: cannot inspect {folder}: {error}", file=sys.stderr)
    return images, has_subfolders


def has_gps_location(image: Path, tool: str) -> bool | None:
    result = subprocess.run([tool, "-j", "-GPSLatitude", "-GPSLongitude", str(image)], text=True, capture_output=True)
    if result.returncode:
        print(f"ERROR reading GPS from {image}: {result.stderr.strip()}", file=sys.stderr)
        return None  # Do not mark a folder complete if metadata cannot be read.
    try:
        metadata = json.loads(result.stdout)[0]
    except (IndexError, json.JSONDecodeError):
        print(f"ERROR reading GPS from {image}: invalid ExifTool output", file=sys.stderr)
        return None
    return "GPSLatitude" in metadata or "GPSLongitude" in metadata


def add_gps_location(image: Path, latitude: float, longitude: float, tool: str) -> bool:
    if DRY_RUN:
        return True
    latitude_ref = "N" if latitude >= 0 else "S"
    longitude_ref = "E" if longitude >= 0 else "W"
    command = [
        tool, "-overwrite_original", "-P", "-m",
        f"-GPSLatitude={abs(latitude)}", f"-GPSLatitudeRef={latitude_ref}",
        f"-GPSLongitude={abs(longitude)}", f"-GPSLongitudeRef={longitude_ref}", str(image),
    ]
    # Write the keyword fields Windows Explorer uses for Tags/Markierungen.
    command[4:4] = [
        f"-XMP-dc:Subject+={AUTO_GPS_TAG}",
        f"-IPTC:Keywords+={AUTO_GPS_TAG}",
        f"-EXIF:XPKeywords+={AUTO_GPS_TAG}",
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        print(f"ERROR tagging {image}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"GEO-TAGGED  {image}  ->  {latitude}, {longitude}; tag: {AUTO_GPS_TAG}")
    return True


def short_location(result: dict[str, object] | None) -> str:
    """Return the city/place portion of a Nominatim result."""
    if result is None:
        return ""
    return str(result.get("display_name", "")).split(",", maxsplit=1)[0]


def write_excel_report(rows: list[list[str]]) -> None:
    """Create the manual folder-location validation workbook."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError as error:
        raise RuntimeError("Creating the Excel report requires openpyxl.") from error

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Location review"
    sheet.append(["Folder name", "Valid", "Found location", "Parent location", "Parent name"])
    for row in rows:
        sheet.append(row)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:E{max(1, len(rows) + 1)}"
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")
    for column, width in {"A": 34, "B": 12, "C": 28, "D": 28, "E": 34}.items():
        sheet.column_dimensions[column].width = width
    workbook.save(EXCEL_REPORT)
    print(f"Excel review report written to: {EXCEL_REPORT}")


def main() -> int:
    if not SEARCH_FOLDER.is_dir():
        print(f"SEARCH_FOLDER does not exist or is not a folder: {SEARCH_FOLDER}", file=sys.stderr)
        return 2

    folders = list(iter_subfolders(SEARCH_FOLDER))
    print(f"Checking {len(folders)} folder(s) at or below {SEARCH_FOLDER}")
    checked = found = tagged = 0
    tool: str | None = None
    report_rows: list[list[str]] = []
    own_complete: dict[Path, bool] = {}
    for folder in folders:
        if CHECK_IMAGE_FILES:
            images, has_subfolders = images_and_subfolders(folder)
            if not images and not has_subfolders:
                print(f"SKIPPED  {folder}  (empty leaf folder)")
                report_rows.append([folder.name, "", "", "", folder.parent.name])
                own_complete[folder] = True
                continue
        else:
            images = []

        # A folder without direct image files is complete from the image-tag
        # perspective; its descendants are checked separately below.
        folder_complete = not images

        # Resolve the parent first.  A recognized parent becomes geographical
        # context for its child, e.g. "Holzweg, Baiersbronn".
        parent_location, _parent_query, parent_result = lookup_folder_name(folder.parent)
        location, query, result = lookup_folder_name(folder, near=parent_location if parent_result else None)
        source = "folder near parent folder" if parent_result and location else "folder"
        if location:
            checked += 1

        if result is not None and not is_near_parent(result, parent_result):
            result = None

        # A parent itinerary location can be useful context, but it may be too
        # narrow for a nearby attraction (for example, Nagoldtalsperre near
        # Seewald rather than Baiersbronn).  In that case, try the child's
        # location name worldwide before using the parent coordinates.
        if result is None and parent_result is not None and location:
            standalone_location, standalone_query, standalone_result = lookup_folder_name(folder)
            if is_near_parent(standalone_result, parent_result):
                location, query, result = standalone_location, standalone_query, standalone_result
                source = "folder (without parent context)"

        # For a compound name such as "Lift_Ruhestein", test the individual
        # words only after both normal searches failed.  A term is accepted
        # only if it resolves uniquely and is within the parent distance limit.
        if result is None and parent_result is not None:
            component_result = unique_location_component(folder, parent_result)
            if component_result is not None:
                location, query, result = component_result
                source = "unique folder-name component near parent folder"

        # If no child location can be resolved, use only its direct parent;
        # grandparents are intentionally ignored.
        if result is None and parent_result is not None:
            location, query, result = parent_location, _parent_query, parent_result
            source = "parent folder"

        if result is None:
            attempted = query or "no non-numeric location text"
            print(f"NOT FOUND  {folder}  ->  {attempted} (parent also had no resolved location)")
            if images:
                # No GPS can be added without a valid location, but this
                # folder is still complete when every image already has GPS.
                folder_complete = True
                if tool is None:
                    tool = exiftool_command()
                for image in images:
                    if has_gps_location(image, tool) is not True:
                        folder_complete = False
        else:
            found += 1
            latitude = result["lat"]
            longitude = result["lon"]
            print(
                f"FOUND\n"
                f"  Folder:    {folder}\n"
                f"  Source:    {source}\n"
                f"  Query:     {query}\n"
                f"  Location:  {result.get('display_name', '')}\n"
                f"  Latitude:  {latitude}\n"
                f"  Longitude: {longitude}"
            )
            if images:
                folder_complete = True
                if tool is None:
                    tool = exiftool_command()
                for image in images:
                    gps_location = has_gps_location(image, tool)
                    if gps_location is None:
                        folder_complete = False
                    elif gps_location:
                        if not DRY_RUN:
                            print(f"UNCHANGED  {image}  (GPS location already exists)")
                    elif DRY_RUN:
                        # For validation, one untagged image proves this
                        # resolved folder would cause a change. Do not scan
                        # the remaining files in this folder.
                        tagged += 1
                        break
                    elif add_gps_location(image, float(latitude), float(longitude), tool):
                        tagged += 1
                    else:
                        folder_complete = False

        report_rows.append([
            folder.name,
            "",  # Intentionally blank for manual validation.
            short_location(result),
            short_location(parent_result),
            folder.parent.name,
        ])
        own_complete[folder] = folder_complete

    if not DRY_RUN and CHECK_IMAGE_FILES:
        completed: dict[Path, bool] = {}
        for folder in sorted(folders, key=lambda path: len(path.parts), reverse=True):
            try:
                children = [path for path in folder.iterdir() if path.is_dir()]
            except OSError as error:
                print(f"WARNING: cannot verify child folders of {folder}: {error}", file=sys.stderr)
                completed[folder] = False
                continue
            descendants_complete = all(completed.get(child, has_tagged_marker(child)) for child in children)
            # Reaching this point means the folder was processed in the active
            # run. Mark it even when no location was found or no image needed
            # a change; its parent waits for every child to be processed too.
            completed[folder] = descendants_complete
            if completed[folder] and not has_tagged_marker(folder):
                try:
                    (folder / TAGGED_MARKER_NAME).write_text(
                        f"Completed by find_folder_locations.py on {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
                        encoding="utf-8",
                    )
                    print(f"MARKED  {folder}")
                except OSError as error:
                    completed[folder] = False
                    print(f"WARNING: could not create marker in {folder}: {error}", file=sys.stderr)
    write_excel_report(report_rows)
    if DRY_RUN:
        print(
            f"Done: {found}/{checked} location-like folder name(s) were resolved; "
            f"{tagged} folder(s) contain at least one image that would be geo-tagged."
        )
    else:
        print(f"Done: {found}/{checked} location-like folder name(s) were resolved; {tagged} image(s) were geo-tagged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
