"""TSV import adapter."""
import csv as _csv
from . import map_header


def parse(path):
    """Parse a TSV file into normalized rows. Returns (rows, errors)."""
    _csv.field_size_limit(10 * 1024 * 1024)
    rows, errors = [], []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = _csv.DictReader(f, delimiter="\t")
        fields = reader.fieldnames or []
        mapping = map_header(fields)
        if not mapping:
            errors.append("no recognizable columns (need line_id and/or raw/tr/ed)")
            return rows, errors
        for i, rec in enumerate(reader, start=2):
            row = {}
            for col, canon in mapping.items():
                v = rec.get(col)
                if v is None:
                    continue
                v = v.strip()
                if v != "":
                    row[canon] = v
            if any(row.values()):
                rows.append({"_line_no": i, **row})
    return rows, errors
