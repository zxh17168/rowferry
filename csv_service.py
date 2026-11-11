"""Deterministic, explicit CSV transformations. Python 3 standard library only."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
OPERATIONS = {'trim', 'lower', 'upper', 'replace'}


def transform(source, config):
    if not isinstance(config, dict):
        raise ValueError('Configuration must be a JSON object')
    if len(source) > MAX_BYTES:
        raise ValueError('Input exceeds the 10 MB service limit')
    csv.field_size_limit(MAX_BYTES)
    if set(config) - {'rules', 'deduplicate_exact'}:
        raise ValueError('Unknown configuration field')
    if not isinstance(config.get('deduplicate_exact', False), bool):
        raise ValueError('deduplicate_exact must be a boolean')
    rules = config.get('rules', [])
    if not isinstance(rules, list) or len(rules) > 5:
        raise ValueError('Provide at most five explicit transformation rules')
    reader = csv.reader(io.StringIO(source.decode('utf-8-sig'), newline=''), strict=True)
    header = next(reader, None)
    if not header or len(set(header)) != len(header) or any(not x for x in header):
        raise ValueError('Input needs nonempty, unique column headers')
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) - {'column', 'op', 'values'}:
            raise ValueError('Invalid rule fields')
        if rule.get('column') not in header or rule.get('op') not in OPERATIONS:
            raise ValueError('Unknown column or operation')
        if rule['op'] == 'replace':
            values = rule.get('values')
            if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
                raise ValueError('Replacement values must be explicit string mappings')
        elif 'values' in rule:
            raise ValueError('values is only supported for replace rules')
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(header)
    seen = set()
    counts = {'input_rows': 0, 'output_rows': 0, 'duplicate_rows_removed': 0, 'changed_cells': 0}
    formula_cells = []
    for line, original in enumerate(reader, 2):
        if len(original) != len(header):
            raise ValueError(f'Row {line} has {len(original)} columns; expected {len(header)}')
        counts['input_rows'] += 1
        if config.get('deduplicate_exact', False) and tuple(original) in seen:
            counts['duplicate_rows_removed'] += 1
            continue
        seen.add(tuple(original))
        row = original.copy()
        for rule in rules:
            idx = header.index(rule['column'])
            old = row[idx]
            op = rule['op']
            row[idx] = old.strip() if op == 'trim' else old.lower() if op == 'lower' else old.upper() if op == 'upper' else rule['values'].get(old, old)
        counts['changed_cells'] += sum(a != b for a, b in zip(row, original))
        for index, cell in enumerate(row):
            if cell.lstrip().startswith(('=', '+', '-', '@')):
                formula_cells.append({'source_row': line, 'column': header[index]})
        writer.writerow(row)
        counts['output_rows'] += 1
    encoded = output.getvalue().encode('utf-8')
    report = {
        'source_sha256': hashlib.sha256(source).hexdigest(),
        'output_sha256': hashlib.sha256(encoded).hexdigest(),
        **counts,
        'row_reconciliation_passed': counts['input_rows'] == counts['output_rows'] + counts['duplicate_rows_removed'],
        'config': config,
        'potential_spreadsheet_formula_cells': formula_cells,
        'notes': [
            'All values remain strings: no inferred dates, numbers, missing values, or guessed replacements.',
            'Exact duplicate removal compares original full rows, before normalization.',
            'Formula-like values are flagged, not modified. Review before opening in spreadsheet software.',
        ],
    }
    return encoded, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('destination', type=Path, help='New directory; never overwrites an existing delivery')
    args = parser.parse_args()
    if args.source.stat().st_size > MAX_BYTES:
        parser.error('Input exceeds the 10 MB service limit')
    try:
        output, report = transform(args.source.read_bytes(), json.loads(args.config.read_text()))
        args.destination.mkdir(parents=True, exist_ok=False)
        (args.destination / 'cleaned.csv').write_bytes(output)
        (args.destination / 'validation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    except (ValueError, UnicodeError, csv.Error, OSError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
