"""Offline checks using disposable workbooks and publication directories."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'NAS'))
import generate_fund_report as report
import refresh_and_publish_fund_report as publish
import update_fund_online_values as updater


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workbook = self.root / 'funds.xlsx'
        self.output = self.root / 'output'
        self.public = self.root / 'public'
        self.funds = [report.Fund('DE0000000001', 'Test fund')]
        self.rows = [dict(isin=self.funds[0].isin, source='test', symbol='TEST',
                          date=date, close='100', error='', updated_at='2024-01-03')
                     for date in ('2024-01-01', '2024-01-02')]
        report.write_xlsx(self.workbook, {
            'ScalarValues': [['isin', 'name'], [self.funds[0].isin, 'Test fund']],
            'DateValuePairs': [['isin', 'series', 'date', 'value'],
                               [self.funds[0].isin, 'invest', '2024-01-01', 100]],
            'QuantityDatePairs': [['isin', 'date', 'quantity'],
                                  [self.funds[0].isin, '2024-01-01', 1]],
        })
        updater.write_online_values(self.workbook, self.rows)
        self.env = patch.dict(os.environ, {'FUND_DATEFILTER_START': '', 'FUND_DATEFILTER_END': ''})
        self.env.start()
        self.addCleanup(self.env.stop)

    def generate(self):
        report.main(['--manual-data', str(self.workbook), '--output-dir', str(self.output), '--no-open'])
        return (self.output / 'fund_history_report.html').read_text(encoding='utf-8')

    def run_pipeline(self, child):
        args = ['publish', '--manual-data', str(self.workbook), '--output-dir', str(self.output),
                '--publish-dir', str(self.public)]
        with patch.object(sys, 'argv', args), patch.object(publish.subprocess, 'run', side_effect=child):
            publish.main()

    def test_real_headless_report_validates(self):
        publish.validate_report(self.workbook, self.funds, self.generate())

    def test_bad_prices_dates_and_errors_rejected(self):
        document = self.generate()
        for field, value in [('close', 'NaN'), ('close', 'inf'), ('close', '-1'),
                             ('close', 'bad'), ('date', 'bad'), ('date', '2999-01-01'),
                             ('error', 'provider failed')]:
            with self.subTest(field=field, value=value):
                rows = [dict(row) for row in self.rows]
                rows[0][field] = value
                updater.write_online_values(self.workbook, rows)
                with self.assertRaises(ValueError):
                    publish.validate_report(self.workbook, self.funds, document)

    def test_date_filter_requires_history(self):
        with patch.dict(os.environ, {'FUND_DATEFILTER_START': '2024-01-02'}):
            document = self.generate()
            publish.validate_report(self.workbook, self.funds, document)
            self.assertIn('Only one current value found', document)

    def test_truncated_or_wrong_portfolio_rejected(self):
        document = self.generate()
        for invalid in (document.split('</body>')[0],
                        document.replace(self.funds[0].isin, 'OTHER'),
                        document.replace('for 1 ISINs.', 'for 0 ISINs.')):
            with self.assertRaises(ValueError):
                publish.validate_report(self.workbook, self.funds, invalid)

    def test_atomic_failure_preserves_originals(self):
        for destination, write in (
            (self.root / 'report.html', lambda p: report.atomic_write_text(p, 'new')),
            (self.workbook, lambda p: report.write_xlsx(p, {'Test': [['new']]})),
        ):
            if not destination.exists():
                destination.write_text('original')
            before = destination.read_bytes()
            files = set(self.root.iterdir())
            with patch.object(report.os, 'replace', side_effect=OSError('simulated interruption')):
                with self.assertRaises(OSError):
                    write(destination)
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual(set(self.root.iterdir()), files)

    def test_successful_publication_and_backup(self):
        def child(command, **kwargs):
            self.assertTrue(kwargs['check'])
            self.assertEqual(kwargs['timeout'], 3600)
            if '--no-open' in command:
                self.generate()
            else:
                self.assertIn('--refresh', command)
        self.run_pipeline(child)
        self.assertEqual((self.public / 'index.html').read_bytes(),
                         (self.output / 'fund_history_report.html').read_bytes())
        self.assertEqual(len(list((self.root / 'backups').glob('*.xlsx'))), 1)

    def test_child_failure_preserves_publication(self):
        self.public.mkdir()
        for name in ('index.html', 'fund_history_report.html'):
            (self.public / name).write_text('old')
        def fail(*args, **kwargs):
            raise subprocess.CalledProcessError(1, 'simulated provider failure')
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_pipeline(fail)
        for path in self.public.iterdir():
            self.assertEqual(path.read_text(), 'old')

    def test_failed_refresh_preserves_prices(self):
        before = report.read_xlsx_rows(self.workbook, 'OnlineValues')
        with patch.object(updater, 'download_best_history', return_value=None):
            result = updater.main(['--manual-data', str(self.workbook), '--output-dir', str(self.output)])
        self.assertEqual(result, 0)
        self.assertEqual(report.read_xlsx_rows(self.workbook, 'OnlineValues'), before)

    def test_validation_failure_preserves_publication(self):
        self.public.mkdir()
        (self.public / 'index.html').write_text('old')
        self.output.mkdir()
        (self.output / 'fund_history_report.html').write_text('<html><svg>incomplete')
        with self.assertRaises(ValueError):
            self.run_pipeline(lambda *args, **kwargs: None)
        self.assertEqual((self.public / 'index.html').read_text(), 'old')

    def test_missing_and_empty_workbooks_fail_before_children(self):
        self.workbook.unlink()
        with self.assertRaises(ValueError):
            self.run_pipeline(lambda *a, **k: self.fail('Child must not run'))
        report.write_xlsx(self.workbook, {
            'ScalarValues': [['isin']], 'DateValuePairs': [['isin', 'series', 'date', 'value']],
        })
        with self.assertRaises(ValueError):
            self.run_pipeline(lambda *a, **k: self.fail('Child must not run'))
        self.assertFalse(self.public.exists())

    def test_overlapping_process_fails_without_workbook_changes(self):
        before = self.workbook.read_bytes()
        with self.workbook.with_suffix('.lock').open('a+b') as lock:
            if os.name == 'nt':
                import msvcrt
                lock.write(b'0')
                lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([
                sys.executable, '-B', publish.__file__, '--manual-data', str(self.workbook),
                '--publish-dir', str(self.public),
            ], capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Update failed:', result.stderr)
        self.assertEqual(self.workbook.read_bytes(), before)
        self.assertFalse(self.public.exists())

    def test_successful_refresh_preserves_old_history(self):
        fresh = report.HistoryResult('test', 'TEST', [report.Quote('2024-02-01', 110), report.Quote('2024-02-02', 120)])
        with patch.object(updater, 'download_best_history', return_value=fresh):
            self.assertEqual(updater.main(['--manual-data', str(self.workbook), '--output-dir', str(self.output)]), 0)
        self.assertEqual(len(report.read_xlsx_rows(self.workbook, 'OnlineValues')), 4)

    def test_first_publication_with_one_unavailable_fund(self):
        sheets = {}
        for sheet in ('ScalarValues', 'DateValuePairs', 'QuantityDatePairs', 'OnlineValues'):
            rows = report.read_xlsx_rows(self.workbook, sheet)
            sheets[sheet] = report.rows_from_dicts(list(rows[0]), rows)
        sheets['ScalarValues'].append(['DE0000000002', 'Unavailable fund'])
        report.write_xlsx(self.workbook, sheets)
        def child(command, **kwargs):
            if '--no-open' in command:
                self.generate()
            else:
                fresh = report.HistoryResult('test', 'TEST', [report.Quote('2024-02-01', 110), report.Quote('2024-02-02', 120)])
                with patch.object(updater, 'download_best_history', side_effect=lambda fund, *a: fresh if fund.isin == self.funds[0].isin else None):
                    self.assertEqual(updater.main(command[2:]), 0)
        self.run_pipeline(child)
        for name in ('index.html', 'fund_history_report.html'):
            document = (self.public / name).read_text(encoding='utf-8')
            self.assertIn('DE0000000002', document)
            self.assertIn('No Yahoo Finance, Onvista, or Deka data found', document)
            self.assertIn('Portfolio charts may be incomplete', document)

    def test_all_funds_unavailable_still_publishes(self):
        updater.write_online_values(self.workbook, [])
        def child(command, **kwargs):
            if '--no-open' in command:
                self.generate()
            else:
                with patch.object(updater, 'download_best_history', return_value=None):
                    self.assertEqual(updater.main(command[2:]), 0)
        self.run_pipeline(child)
        self.assertTrue((self.public / 'index.html').is_file())

    def test_missing_unavailability_note_rejected(self):
        updater.write_online_values(self.workbook, [])
        document = self.generate()
        document = document.replace('No online values found. Run update_fund_online_values.py to update the OnlineValues sheet.', '')
        with self.assertRaises(ValueError):
            publish.validate_report(self.workbook, self.funds, document)


if __name__ == '__main__':
    unittest.main()
