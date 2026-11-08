"""Refresh, validate and publish the static report (Python 3.11+)."""
import argparse
import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys

from fund_history_tool import (load_project_env, configured_data_dir, read_xlsx_rows,
    read_manual_fund_data, extract_funds_from_manual_data, atomic_write_text)


def main():
    load_project_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-dir', required=True, type=Path)
    parser.add_argument('--manual-data', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--overrides')
    parser.add_argument('--period', default='5y')
    parser.add_argument('--interval', default='1d')
    args = parser.parse_args()
    data = configured_data_dir()
    workbook = (args.manual_data or data / 'Input_Data/fund_manual_values.xlsx').resolve()
    output = (args.output_dir or data / 'Web_Report').resolve()
    if not workbook.is_file():
        raise ValueError(f'Missing workbook: {workbook}')
    lock = open(workbook.with_suffix('.lock'), 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0)
            if not lock.read(1):
                lock.write(b'0'); lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        funds = extract_funds_from_manual_data(read_manual_fund_data(workbook))
        if not funds:
            raise ValueError('Empty portfolio')
        backups = workbook.parent / 'backups'
        backups.mkdir(exist_ok=True)
        shutil.copy2(workbook, backups / f'fund-{dt.datetime.now():%Y%m%d-%H%M%S-%f}.xlsx')
        for old in sorted(backups.glob('fund-*.xlsx'), reverse=True)[30:]:
            old.unlink()
        scripts = Path(__file__).resolve().parent
        common = ['--manual-data', str(workbook), '--output-dir', str(output)]
        update = [sys.executable, str(scripts / 'fund_online_values.py'), *common,
                  '--refresh', '--period', args.period, '--interval', args.interval]
        if args.overrides:
            update += ['--overrides', args.overrides]
        subprocess.run(update, check=True, timeout=3600)
        subprocess.run([sys.executable, str(scripts / 'fund_history_tool.py'), *common, '--no-open'], check=True, timeout=3600)
        rows = read_xlsx_rows(workbook, 'OnlineValues')
        if any(not any(r.get('isin') == f.isin and r.get('date') and r.get('close') and not r.get('error') for r in rows) for f in funds):
            raise ValueError('Missing usable quotes')
        document = (output / 'fund_history_report.html').read_text(encoding='utf-8')
        if '<html' not in document or '<svg' not in document:
            raise ValueError('Invalid report')
        for name in ('fund_history_report.html', 'index.html'):
            atomic_write_text(args.publish_dir / name, document)
        print(f'Published report to {args.publish_dir}')
    finally:
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Update failed: {exc}', file=sys.stderr)
        sys.exit(1)
