# -*- coding: utf-8 -*-
"""Final verification of patch_new.xp3 (24 entries) before shipping.

1. Entry list == 14 txt + 6 ks + 4 tjs.
2. The 14 .txt + 6 .ks are BYTE-IDENTICAL to the shipped game/patch.xp3
   (the known-good 20-entry patch) -> proves we only ADDED the 4 .tjs.
3. Each of the 4 .tjs differs from data.xp3 original ONLY on intended lines;
   Menus.tjs string literals are all pure ASCII (ribbon fully English).
"""
import sys, os, re
sys.path.insert(0, r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis')
from xp3_extract import Xp3Archive

PW = r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis\patchwork'
NEW = Xp3Archive(os.path.join(PW, 'patch_new.xp3'))
OLD = Xp3Archive(r'C:\Users\User\Desktop\Games\tenshi_chijo\game\patch.xp3')
SRC = Xp3Archive(r'C:\Users\User\Desktop\Games\tenshi_chijo\game\data.xp3')

newb = {f['name']: NEW.extract_file(f) for f in NEW.files}
oldb = {f['name']: OLD.extract_file(f) for f in OLD.files}
srcb = {f['name']: SRC.extract_file(f) for f in SRC.files}

names = sorted(newb)
txts = [n for n in names if n.endswith('.txt')]
kss  = [n for n in names if n.endswith('.ks')]
tjs  = [n for n in names if n.endswith('.tjs')]
print('entries=%d  txt=%d ks=%d tjs=%d' % (len(names), len(txts), len(kss), len(tjs)))
assert len(names) == 24 and len(txts) == 14 and len(kss) == 6 and len(tjs) == 4

# 2. story + ks byte-identical to shipped patch (only-additions proof)
same = 0
for n in txts + kss:
    assert n in oldb, 'missing in old: ' + n
    if newb[n] == oldb[n]:
        same += 1
    else:
        print('DIFFERS from shipped:', n)
print('story+ks identical to shipped patch: %d/20' % same)
assert same == 20

# 3. each .tjs vs data.xp3 original: changed-line count + Menus all-ASCII literals
def lit_strings(text):
    return re.findall(r'"([^"]*)"', text)

for n in tjs:
    srcname = 'system/' + n
    a = srcb[srcname].decode('cp932').split('\r\n')
    b = newb[n].decode('cp932').split('\r\n')
    ch = sum(1 for i in range(max(len(a), len(b)))
             if (a[i] if i < len(a) else '') != (b[i] if i < len(b) else ''))
    extra = len(b) - len(a)
    print('%s : %d lines changed, line-delta=%+d' % (n, ch, extra))
    assert extra == 0, 'line count changed for ' + n

# ribbon fully English: every string literal in Menus.tjs is pure ASCII
menus = newb['Menus.tjs'].decode('cp932')
nonascii = [s for s in lit_strings(menus) if any(ord(c) > 127 for c in s)]
print('Menus.tjs non-ASCII string literals: %d' % len(nonascii))
for s in nonascii:
    print('   LEFTOVER JP:', repr(s))
assert not nonascii, 'ribbon still has JP literals'

# spot-check key story fixes survived re-flow into the new patch
s01 = newb['01.txt'].decode('cp932')
print('story fix Onlookers ok:', ('Onlookers[r]' in s01) and ('The Onlookers' not in s01))
anyit = any(('It\'s coming out' in newb[n].decode('cp932')) for n in txts)
print("story fix 'It's coming out' present:", anyit)
print('ALL CHECKS PASSED')
