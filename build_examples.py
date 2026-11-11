"""Build two explicitly synthetic, reproducible service demonstrations."""
import json
import zipfile
from pathlib import Path
from csv_service import transform

ROOT = Path(__file__).resolve().parent
EXAMPLES = [
    ('catalog', 'sku,name,category\n0007,  Blue mug  ,cups\n0007,  Blue mug  ,cups\n0012, Café cup ,mugs\n',
     {'rules': [{'column': 'name', 'op': 'trim'}, {'column': 'category', 'op': 'replace', 'values': {'cups': 'Drinkware', 'mugs': 'Drinkware'}}], 'deduplicate_exact': True}),
    ('directory', 'id,name,email,region\n0001,  李明  ,HELLO@EXAMPLE.INVALID,CA\n0002, Anaïs , TEAM@EXAMPLE.INVALID ,Unknown\n',
     {'rules': [{'column': 'name', 'op': 'trim'}, {'column': 'email', 'op': 'trim'}, {'column': 'email', 'op': 'lower'}, {'column': 'region', 'op': 'replace', 'values': {'CA': 'California'}}]}),
]


def main():
    summaries = []
    for name, text, rules in EXAMPLES:
        folder = ROOT / 'examples' / name
        folder.mkdir(parents=True, exist_ok=True)
        source = text.encode('utf-8')
        cleaned, report = transform(source, rules)
        (folder / 'input.csv').write_bytes(source)
        (folder / 'cleaned.csv').write_bytes(cleaned)
        (folder / 'rules.json').write_text(json.dumps(rules, indent=2) + '\n')
        (folder / 'validation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        (folder / 'SYNTHETIC.txt').write_text('Synthetic demonstration data, not customer work. All example.invalid addresses are fictional.\n')
        assert report['row_reconciliation_passed']
        summaries.append({'example': name, **{key: report[key] for key in ('input_rows', 'output_rows', 'duplicate_rows_removed', 'changed_cells')}})
    delivery = ROOT / 'dist'
    delivery.mkdir(exist_ok=True)
    with zipfile.ZipFile(delivery / 'synthetic-service-examples.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / 'examples').rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT))
        archive.write(ROOT / 'csv_service.py', 'csv_service.py')
        archive.writestr('READ_ME.txt', 'SYNTHETIC EXAMPLES ONLY. Python 3, standard library only.\nRun: python3 csv_service.py examples/catalog/input.csv examples/catalog/rules.json new-delivery\nAll values remain strings; output is a separate new directory. Dates and missing values are never guessed.\n')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
