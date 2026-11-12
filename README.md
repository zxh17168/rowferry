# Fixstride

CSV cleanup and automation by Nathan at Fixstride. This repository is a reproducible **synthetic demonstration**, with source, examples and automated checks.

## Run the checks

Python 3, standard library only. No paid API or third-party packages are required.

```sh
python3 -m unittest -v
```

## Try the catalog example

```sh
python3 csv_service.py examples/catalog/input.csv examples/catalog/rules.json delivery-catalog
```

The new directory contains `cleaned.csv` and `validation.json`. Existing delivery directories are never overwritten.

| Example | Input rows | Output rows | Exact duplicates removed |
|---|---:|---:|---:|
| Synthetic catalog | 3 | 2 | 1 |
| Synthetic directory | 2 | 2 | 0 |

All values stay strings. Leading zeros, Unicode and blank cells are preserved unless an explicit rule changes them. The report reconciles row counts and records input/output SHA-256 hashes. Exact duplicate removal compares original full rows before normalization. Dates and missing values are never inferred. Formula-like strings are flagged for review before opening in spreadsheet software.

Explicit operations: trim, lowercase, uppercase and exact value mapping; at most five rules per input, with a 10 MB input limit.

## Service

Contact Nathan at [hello.fixstride@gmail.com](mailto:hello.fixstride@gmail.com) for a redacted sample review and a scoped quote.

For configured cleanup and a verified handover, discuss a redacted sample and requirements first: [service details](https://ko-fi.com/c/9826f3697f), or [message Nathan on Ko-fi](https://ko-fi.com/rowferry).

The examples are fictional and are not customer work or testimonials. This code is supplied under the MIT license; inspect it before using it with your data.
