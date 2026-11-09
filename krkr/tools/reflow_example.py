# -*- coding: utf-8 -*-
"""Re-flow story .txt so no rendered line exceeds MAXSEG half-width chars.

A "block" = run of consecutive lines each ending in [r]/[e1]/[e2].  The block's
words are collected in order and greedily re-wrapped at word boundaries so every
segment is <= MAXSEG.  Each segment is emitted on its own source line ending in
[r]; the final segment ends in the block's original final tag (r/e1/e2).

Blocks whose combined text is already <= MAXSEG are left byte-identical (the
author's short breaks, e.g. a lone speaker label, are preserved).
"""
import sys, os, re
sys.path.insert(0, r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis')
from xp3_extract import Xp3Archive
from xp3_pack import build_xp3

# Always source from the clean pre-reflow backup (original long lines, correct
# menus, speaker labels intact) so the tool is idempotent and never re-wraps
# already-mangled text.
CUR   = r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis\patchwork\patch_backup_before_r_fix.xp3'
KSDIR = r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis\patchwork\ks_patch'
STAGE = r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis\patchwork\reflow_stage'
OUT_T = r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis\patchwork\patch_new.xp3'
KS_NAMES = ['first.ks','_title.ks','_cgmode.ks','_exLoad.ks','_gvolume.ks','_macro.ks']
UI_NAMES = ['Menus.tjs','MainWindow.tjs','HistoryLayer.tjs','YesNoDialog.tjs']
UIDIR = r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis\patchwork\ui_patch'

MAXSEG = 48
ENDTAG = re.compile(r'\[(r|e1|e2)\]$')
SPEAKER_PUNCT = set('.,!?:;-—…')


def seg_text(line):
    return ENDTAG.sub('', line)


def has_embedded_brackets(line):
    body = ENDTAG.sub('', line)
    return ('[' in body) or (']' in body)


def is_speaker_first(block):
    if len(block) < 2:
        return False
    l0 = seg_text(block[0]).strip()
    if not l0 or len(l0) > 25 or l0[-1] in SPEAKER_PUNCT:
        return False
    nxt = block[1].lstrip()
    return nxt.startswith('"') or nxt.startswith('(')


# Editorial / translation fixes, applied to the source text before re-flow.
# Each (old, new) is a single-line substring; order: most specific first.
FIXES = [
    ('The Onlookers[r]', 'Onlookers[r]'),
    ('She shook her head yes over and over', 'She nodded yes over and over'),
    ("You're still coming out", "It's still coming out"),
    ("You're coming out", "It's coming out"),
    ('so much of it is coming at me', 'so much of it is coming out'),
]


def apply_fixes(text):
    for old, new in FIXES:
        text = text.replace(old, new)
    return text


def greedy(words, maxw):
    segs, cur = [], ''
    for w in words:
        cand = w if not cur else cur + ' ' + w
        if (not cur) or len(cand) <= maxw:
            cur = cand
        else:
            segs.append(cur); cur = w
    if cur:
        segs.append(cur)
    return segs


def reflow_block(block_lines, final):
    words = []
    for l in block_lines:
        words.extend(seg_text(l).split())
    segs = greedy(words, MAXSEG)
    out = []
    for k, s in enumerate(segs):
        tag = final if k == len(segs) - 1 else 'r'
        out.append(s + '[' + tag + ']')
    return out


def reflow_scene(text, report=None):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    out = []
    i, n = 0, len(lines)
    changed = 0
    while i < n:
        if ENDTAG.search(lines[i]):
            start = i; final = None
            while i < n and ENDTAG.search(lines[i]):
                final = ENDTAG.search(lines[i]).group(1); i += 1
            block = lines[start:i]
            # (1) never touch special-syntax blocks ([link], [endlink], inline cmds)
            if any(has_embedded_brackets(l) for l in block):
                out.extend(block); continue
            # (2) preserve a leading speaker label (Me / Girl / ...) on its own line
            prefix = []; rest = block
            if is_speaker_first(block):
                prefix = [block[0]]; rest = block[1:]
            maxraw = max((len(seg_text(l).rstrip()) for l in rest), default=0)
            if maxraw > MAXSEG:
                newrest = reflow_block(rest, final)
                if report is not None:
                    report.append((start + 1, i, block, prefix + newrest))
                out.extend(prefix); out.extend(newrest); changed += 1
            else:
                out.extend(prefix); out.extend(rest)
        else:
            out.append(lines[i]); i += 1
    return '\r\n'.join(out) + '\r\n', changed


def main(which):
    os.makedirs(STAGE, exist_ok=True)
    arc = Xp3Archive(CUR)
    pb = {f['name']: f for f in arc.files}
    story = sorted([f['name'] for f in arc.files if f['name'].endswith('.txt')])
    assert len(story) == 14
    if which is None:
        which = set(story)

    files = []
    total_changed = 0
    for name in story:
        raw = arc.extract_file(pb[name])
        text = apply_fixes(raw.decode('cp932'))
        lp = os.path.join(STAGE, name)
        if name in which:
            newtext, ch = reflow_scene(text)
            total_changed += ch
            print('%s : re-flowed %d block(s)' % (name, ch))
        else:
            newtext = text
        blob = newtext.encode('cp932')  # must be CP932-encodable
        with open(lp, 'wb') as fh:
            fh.write(blob)
        files.append((name, lp))

    for ks in KS_NAMES:
        lp = os.path.join(KSDIR, ks)
        assert os.path.isfile(lp), 'missing ' + lp
        files.append((ks, lp))

    for ui in UI_NAMES:
        lp = os.path.join(UIDIR, ui)
        assert os.path.isfile(lp), 'missing ' + lp
        files.append((ui, lp))

    assert len(files) == 24
    ents = build_xp3(files, OUT_T)
    print('built', OUT_T, 'entries=%d' % len(ents))

    # verify: names, CP932 decode, no segment over MAXSEG, final tags preserved
    v = Xp3Archive(OUT_T)
    vn = sorted(f['name'] for f in v.files)
    assert vn == sorted(story + KS_NAMES + UI_NAMES), 'entry mismatch'
    for f in v.files:
        v.extract_file(f).decode('cp932')  # every entry must be valid CP932
    for f in v.files:
        if not f['name'].endswith('.txt'):
            continue
        t = v.extract_file(f).decode('cp932')  # CP932 decode check
        ls = t.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        if ls and ls[-1] == '':
            ls.pop()
        enforce = f['name'] in which
        for l in ls:
            m = ENDTAG.search(l)
            if m and enforce:
                if has_embedded_brackets(l):   # [link]/[endlink]/cmds: not rendered prose
                    continue
                seg = seg_text(l).rstrip()
                assert len(seg) <= MAXSEG, '%s segment over %d: %r' % (f['name'], MAXSEG, seg[:60])
    print('VERIFIED: 24 entries (14 txt + 6 ks + 4 tjs), all CP932 ok; re-flowed scenes all segments <= %d' % MAXSEG)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'ALL':
        which = None
    elif len(sys.argv) > 1:
        which = set(sys.argv[1].split(','))
    else:
        which = set()
    main(which)
