"""Import adapters: turn an incoming file into normalized rows.

A normalized row is a dict with these optional keys:
    line_id   str or None
    raw       str or None   (source JP text)
    mtl       str or None   (machine baseline)
    tr        str or None   (translation)
    ed        str or None   (edited final)
    speaker   str or None
    note      str or None

Adapters are format-only: they parse and normalise, they never decide
workflow consequences. Matching against the project store and workflow
effects are computed by the server's import preview step.
"""

import os

# Column aliases -> canonical field (shared by csv/tsv/json adapters)
ALIASES = {
    "line_id": "line_id", "linid": "line_id", "id": "line_id",
    "raw": "raw", "jp": "raw", "source": "raw", "source_text": "raw", "jp_text": "raw",
    "mtl": "mtl", "machine": "mtl", "baseline": "mtl",
    "tr": "tr", "tl": "tr", "translation": "tr", "translated": "tr",
    "ed": "ed", "final": "ed", "en": "ed", "en_final": "ed", "edited": "ed",
    "speaker": "speaker", "spk": "speaker",
    "note": "note", "notes": "note", "comment": "note",
}


def map_header(header):
    out = {}
    for col in header:
        key = (col or "").strip().lower().lstrip("\ufeff")
        if key in ALIASES:
            out[col] = ALIASES[key]
    return out


def parse_any(path):
    from . import csv as _csv_mod, tsv as _tsv_mod, json as _json_mod
    ext = os.path.splitext(str(path))[1].lower()
    if ext == ".csv":
        return _csv_mod.parse(path)
    if ext == ".tsv":
        return _tsv_mod.parse(path)
    if ext == ".json":
        return _json_mod.parse(path)
    return [], [f"unsupported file type '{ext}' (use .csv/.tsv/.json)"]
