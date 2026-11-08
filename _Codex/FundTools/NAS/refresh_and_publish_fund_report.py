"""Refresh, validate and publish the static report (Python 3.11+)."""
import argparse
import datetime as dt
from html.parser import HTMLParser
from html import escape
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

# Support direct execution from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_fund_report import (load_project_env, configured_data_dir, read_xlsx_rows,
    read_manual_fund_data, extract_funds_from_manual_data, atomic_write_text,
    configured_date_filter, parse_excel_date, read_online_value_results)


class ReportStructure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = []
        self.tags = set()
        self.closed = set()
        self.heading = None

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        if tag in ('h1', 'h2'):
            self.heading = []

    def handle_data(self, data):
        if self.heading is not None:
            self.heading.append(data)

    def handle_endtag(self, tag):
        self.closed.add(tag)
        if tag in ('h1', 'h2') and self.heading is not None:
            self.headings.append(''.join(self.heading).strip())
            self.heading = None


def validate_report(workbook, funds, document):
    """Reject invalid quotes and incomplete portfolio reports before publishing."""
    if not funds:
        raise ValueError('Empty portfolio')
    start, end = configured_date_filter()
    dates = {fund.isin: set() for fund in funds}
    today = dt.date.today().isoformat()
    for row in read_xlsx_rows(workbook, 'OnlineValues'):
        isin = row.get('isin', '').strip().upper()
        if isin not in dates:
            continue
        if (not row.get('date', '').strip() and not row.get('close', '').strip()
                and row.get('error', '').strip()):
            continue
        date = parse_excel_date(row.get('date', ''))
        try:
            price = float(row.get('close', ''))
            valid_date = dt.date.fromisoformat(date).isoformat()
        except (ValueError, TypeError):
            raise ValueError(f'Invalid quote date or price for {isin}') from None
        error = row.get('error', '').strip()
        current_only = error == 'Only one current value found; no historical series available from configured sources.'
        if (error and not current_only) or not math.isfinite(price) or price <= 0 or valid_date > today:
            raise ValueError(f'Invalid quote for {isin} on {date}')
        if (start is None or date >= start) and (end is None or date <= end):
            dates[isin].add(date)
    for isin, points in dates.items():
        if len(points) < 2:
            print(f'Warning: insufficient historical quotes for {isin}; publishing with a data-availability note.')
    structure = ReportStructure()
    structure.feed(document)
    structure.close()
    required = {'html', 'head', 'body', 'svg', 'table'}
    if not any(len(points) >= 2 for points in dates.values()):
        required.discard('svg')
    if (not required <= structure.tags or not required <= structure.closed
            or 'Fund History' not in structure.headings
            or f'for {len(funds)} ISINs.' not in document):
        raise ValueError('Invalid or incomplete report structure')
    for fund in funds:
        if not any(h == fund.isin or h.startswith((fund.isin + ' /', fund.isin + ' -'))
                   for h in structure.headings):
            raise ValueError(f'Report is missing fund {fund.isin}')
    for fund, _, _, _, error in read_online_value_results(workbook, funds, start, end):
        if error and escape(error) not in document:
            raise ValueError(f'Report is missing the data-availability note for {fund.isin}')


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
        scripts = Path(__file__).resolve().parent.parent
        common = ['--manual-data', str(workbook), '--output-dir', str(output)]
        update = [sys.executable, str(scripts / 'update_fund_online_values.py'), *common,
                  '--refresh', '--period', args.period, '--interval', args.interval]
        if args.overrides:
            update += ['--overrides', args.overrides]
        subprocess.run(update, check=True, timeout=3600)
        subprocess.run([sys.executable, str(scripts / 'generate_fund_report.py'), *common, '--no-open'], check=True, timeout=3600)
        document = (output / 'fund_history_report.html').read_text(encoding='utf-8')
        validate_report(workbook, funds, document)
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
