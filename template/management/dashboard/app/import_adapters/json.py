"""JSON import adapter.

Accepts either a list of row objects or {lines|rows|entries: [...]}.
Row objects may use canonical keys (line_id/raw/mtl/tr/ed/speaker/note)
or the same aliases as CSV headers.
"""
import json as _json
from . import ALIASES


def parse(path):
    rows, errors = [], []
    with open(path, "r", encoding="utf-8-sig") as f:
        try:
            data = _json.load(f)
        except Exception as e:
            return rows, [f"invalid JSON: {e}"]
    if isinstance(data, dict):
        for key in ("lines", "rows", "entries", "items"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            return rows, ["JSON object must contain a 'lines' (or rows/entries) array"]
    if not isinstance(data, list):
        return rows, ["expected a JSON array of row objects"]
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(f"row {i}: not an object")
            continue
        row = {}
        for k, v in item.items():
            key = str(k).strip().lower()
            canon = ALIASES.get(key)
            if canon is None:
                continue
            if v is None:
                continue
            v = v.strip() if isinstance(v, str) else str(v)
            if v != "":
                row[canon] = v
        if any(row.values()):
            rows.append({"_line_no": i, **row})
    return rows, errors
