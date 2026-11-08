#!/usr/bin/env python3
"""Copy the NAS runtime and create missing folders under an accessible NAS base."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile

from generate_fund_report import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_FILES = (
    'FundTools/generate_fund_report.py',
    'FundTools/update_fund_online_values.py',
    'FundTools/NAS/refresh_and_publish_fund_report.py',
    'FundTools/tests/test_publication.py',
    'docs/nas-setup.md',
    'docs/code-adjustments.md',
    'docs/open_issues.md',
    'docs/fund_history_calculations.md',
    'FundTools/NAS/common.sh',
    'FundTools/NAS/run_update.sh',
    'FundTools/NAS/verify_runtime.sh',
    'FundTools/NAS/README.md',
)


def copy_file(source: Path, destination: Path, *, overwrite: bool) -> None:
    """Stage a complete file; never overwrite existing NAS input data."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        # Exclusive creation also protects against files created after planning.
        with source.open('rb') as incoming, destination.open('xb') as outgoing:
            try:
                shutil.copyfileobj(incoming, outgoing)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            except BaseException:
                outgoing.close()
                destination.unlink(missing_ok=True)
                raise
        return
    fd, name = tempfile.mkstemp(prefix='.release-', dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as outgoing, source.open('rb') as incoming:
            if source.suffix.lower() == '.sh':
                outgoing.write(incoming.read().replace(b'\r\n', b'\n'))
            else:
                shutil.copyfileobj(incoming, outgoing)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        if os.name != 'nt':
            temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def release(destination: Path, *, include_input_data=False, dry_run=False,
            source_root: Path = REPO_ROOT, publication_dir: Path | None = None) -> None:
    source_root = source_root.resolve()
    destination = destination.expanduser().resolve()
    if destination.exists() and not destination.is_dir():
        raise ValueError(f'Project destination is not a folder: {destination}')
    if (destination == source_root or source_root in destination.parents
            or destination in source_root.parents):
        raise ValueError('Destination must be separate from the local repository')
    files = [(source_root / name, destination / name, True) for name in RELEASE_FILES]
    if include_input_data:
        inputs = source_root / 'Data' / 'Input_Data'
        workbook = inputs / 'fund_manual_values.xlsx'
        if not workbook.is_file():
            raise ValueError(f'Missing initial portfolio workbook: {workbook}')
        files.extend((path, destination / 'Data' / 'Input_Data' / path.relative_to(inputs), False)
                     for path in sorted(inputs.rglob('*'))
                     if path.is_file() and path.suffix.lower() in {'.xlsx', '.csv'}
                     and not path.name.startswith('~$')
                     and not any(part.lower() in {'backups', 'cache', '_old'}
                                 for part in path.relative_to(inputs).parts[:-1])
                     and '.bak.' not in path.name.lower())
    # Check all sources before changing the destination.
    for source, target, overwrite in files:
        if not source.is_file():
            raise ValueError(f'Missing release file: {source}')
        if source.is_symlink() or any(parent.is_symlink() for parent in source.parents):
            raise ValueError(f'Symlink source is not supported: {source}')
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
            raise ValueError(f'Symlink destination is not supported: {target}')
        if target.exists() and not target.is_file():
            raise ValueError(f'File destination is not a regular file: {target}')
    directories = [destination, destination / 'Data/Input_Data',
                   destination / 'Data/Web_Report', destination / 'logs']
    directories.extend(target.parent for _, target, _ in files)
    if publication_dir is not None:
        directories.append(publication_dir.expanduser().resolve())
    directories = list(dict.fromkeys(directories))
    for folder in directories:
        for candidate in (folder, *folder.parents):
            if candidate.is_symlink():
                raise ValueError(f'Symlink directory is not supported: {candidate}')
            if candidate.exists() and not candidate.is_dir():
                raise ValueError(f'Directory path is occupied by a file: {candidate}')
    for folder in directories:
        if not folder.exists():
            print(f'{"WOULD CREATE" if dry_run else "CREATE"}: {folder}')
            if not dry_run:
                folder.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    for source, target, overwrite in files:
        if not overwrite and target.exists():
            print(f'SKIP existing input: {target}')
            skipped += 1
            continue
        print(f'{"WOULD COPY" if dry_run else "COPY"}: {source.relative_to(source_root)} -> {target}')
        if not dry_run:
            try:
                copy_file(source, target, overwrite=overwrite)
            except FileExistsError:
                if overwrite:
                    raise
                print(f'SKIP input created during release: {target}')
                skipped += 1
                continue
        copied += 1
    print(f'{"Planned" if dry_run else "Released"}: {copied} files; skipped: {skipped}.')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, nargs='?',
                        help='Override the NAS base directory (NAS_PROJECT_PATH); releases go into docker/fund-report.')
    parser.add_argument('--include-input-data', action='store_true',
                        help='Also seed CSV/XLSX inputs, skipping existing NAS files.')
    parser.add_argument('--dry-run', action='store_true', help='List planned copies without writing.')
    args = parser.parse_args(argv)
    try:
        load_dotenv(REPO_ROOT / '.env')
        configured = (os.environ.get('NAS_PROJECT_PATH') or '').strip()
        base = args.destination or (Path(configured) if configured else None)
        if base is None:
            raise ValueError('Set NAS_PROJECT_PATH in the repository .env or provide a destination argument.')
        base = base.expanduser().resolve()
        if not base.is_dir():
            raise ValueError(f'NAS base directory is not accessible: {base}. Check the share path, network connection and Windows login.')
        destination = base / 'docker' / 'fund-report'
        public_setting = (os.environ.get('NAS_PUBLIC_PATH') or '').strip()
        publication_dir = Path(public_setting) if public_setting else None
        if publication_dir is not None:
            publication_dir = publication_dir.expanduser().resolve()
            if not publication_dir.parent.is_dir():
                raise ValueError(f'Public parent folder is not accessible: {publication_dir.parent}')
        release(destination, include_input_data=args.include_input_data, dry_run=args.dry_run,
                publication_dir=publication_dir)
        if publication_dir is None:
            print('NAS_PUBLIC_PATH is not set; create /volume1/web/fund-report on the NAS before running updates.')
    except (OSError, ValueError) as exc:
        print(f'Release failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
