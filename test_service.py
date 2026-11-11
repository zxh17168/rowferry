import unittest
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from csv_service import transform, MAX_BYTES


class TransformTests(unittest.TestCase):
    def test_preserves_ids_unicode_dates_money_and_blanks(self):
        source = 'id,name,date,amount,empty\n0007,李明,01/02/26,001.20,\n'.encode()
        output, report = transform(source, {})
        self.assertEqual(output, source)
        self.assertEqual(report['changed_cells'], 0)
        self.assertTrue(report['row_reconciliation_passed'])

    def test_exact_deduplication_is_before_normalization(self):
        source = b'id,name\n01, A \n01, A \n01,A\n'
        output, report = transform(source, {'deduplicate_exact': True, 'rules': [{'column': 'name', 'op': 'trim'}]})
        self.assertEqual(output, b'id,name\n01,A\n01,A\n')
        self.assertEqual((report['input_rows'], report['output_rows'], report['duplicate_rows_removed']), (3, 2, 1))

    def test_only_explicit_replacements(self):
        output, report = transform(b'state\nCA\nUnknown\n', {'rules': [{'column': 'state', 'op': 'replace', 'values': {'CA': 'California'}}]})
        self.assertEqual(output, b'state\nCalifornia\nUnknown\n')

    def test_quoted_multiline_bom_and_formula_warning(self):
        output, report = transform('\ufeffid,note\r\n001,"two\nlines"\r\n002,=1+1\r\n'.encode(), {})
        self.assertIn(b'001,"two\nlines"', output)
        self.assertEqual(report['potential_spreadsheet_formula_cells'], [{'source_row': 3, 'column': 'note'}])

    def test_invalid_inputs_fail_closed(self):
        for source in (b'a,a\n1,2\n', b'a,b\n1\n', b'', b'a\n"unclosed', b'\xff'):
            with self.subTest(source=source), self.assertRaises((ValueError, UnicodeError, csv.Error)):
                transform(source, {})

    def test_oversize_and_invalid_config(self):
        with self.assertRaises(ValueError):
            transform(b'x' * (MAX_BYTES + 1), {})
        for config in ({'deduplicate_exact': 'false'}, {'rules': [{'column': 'missing', 'op': 'trim'}]}, {'rules': [{'column': 'id', 'op': 'replace', 'values': {'1': 2}}]}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                transform(b'id\n1\n', config)

    def test_large_valid_cell(self):
        source = b'note\n' + b'x' * 150000 + b'\n'
        self.assertEqual(transform(source, {})[0], source)

    def test_cli_preserves_input_and_existing_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.csv'
            source.write_bytes(b'id,name\n001, A \n')
            config = root / 'rules.json'
            config.write_text(json.dumps({'rules': [{'column': 'name', 'op': 'trim'}]}))
            destination = root / 'delivery'
            command = [sys.executable, str(Path(__file__).with_name('csv_service.py')), str(source), str(config), str(destination)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(source.read_bytes(), b'id,name\n001, A \n')
            expected = (destination / 'cleaned.csv').read_bytes()
            self.assertEqual(expected, b'id,name\n001,A\n')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((destination / 'cleaned.csv').read_bytes(), expected)


if __name__ == '__main__':
    unittest.main()
