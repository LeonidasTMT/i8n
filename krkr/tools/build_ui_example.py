# -*- coding: utf-8 -*-
"""Build root-level engine-UI .tjs overrides (English) from data.xp3.

For each target file we read the original CP932 bytes, replace ONLY the
user-visible string literals listed in PAIRS, and re-encode to CP932.  Every
byte not part of a replaced literal is preserved exactly (Japanese comments
kept, indentation tabs kept, the literal \\t in Console/Controller kept, line
endings kept).  A per-file report prints each replacement's match count and a
line-by-line diff so only intended lines changed.

Scope: player-facing normal-play UI.  Error/debug/internal strings left as-is.
"""
import sys, os
sys.path.insert(0, r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis')
from xp3_extract import Xp3Archive

SRC = r'C:\Users\User\Desktop\Games\tenshi_chijo\game\data.xp3'
OUTDIR = r'C:\Users\User\Desktop\Games\tenshi_chijo\analysis\patchwork\ui_patch'
os.makedirs(OUTDIR, exist_ok=True)

MENUS = [
    ('"システム(&S)"', '"System(&S)"'),
    ('"画面(&V)"', '"Display(&V)"'),
    ('"ウィンドウ表示(&W)"', '"Windowed(&W)"'),
    ('"フルスクリーン(&F)"', '"Fullscreen(&F)"'),
    ('"前に戻る(&B)"', '"Back(&B)"'),
    ('"タイトルに戻る(&R)"', '"Return to Title(&R)"'),
    ('"終了(&X)"', '"Exit(&X)"'),
    ('"次の選択肢/未読まで進む(&F)"', '"Skip to Choice/Unread(&F)"'),
    ('"次の選択肢まで進む(&F)"', '"Skip to Choice(&F)"'),
    ('"文章スキップ(&F)"', '"Skip Text(&F)"'),
    ('"セーブ(&U)"', '"Save(&U)"'),
    ('"ロード(&D)"', '"Load(&D)"'),
    ('"テキスト(&T)"', '"Text(&T)"'),
    ('"テキスト窓消去(&E)"', '"Clear Text Window(&E)"'),
    ('"バックログ表示(&H)"', '"Show History(&H)"'),
    ('"表示速度(&C)"', '"Text Speed(&C)"'),
    ('"ノーウェイト(&W)"', '"No Wait(&W)"'),
    ('"速い(&A)"', '"Fastest(&A)"'),
    ('"やや速い(&F)"', '"Faster(&F)"'),
    ('"普通(&N)"', '"Normal(&N)"'),
    ('"やや遅い(&S)"', '"Slower(&S)"'),
    ('"遅い(&Z)"', '"Slowest(&Z)"'),
    ('"ページ末まで一気に(&P)"', '"Skip to End of Page(&P)"'),
    ('"一度読んだところは(&I)"', '"Already Read(&I)"'),
    ('"変えない(&M)"', '"No Change(&M)"'),
    ('"自動的に読み進む(&A)"', '"Auto Mode(&A)"'),
    ('"自動的に読み進むウェイト(&D)"', '"Auto Mode Wait(&D)"'),
    ('"1秒(&1)"', '"1 Second(&1)"'),
    ('"2秒(&2)"', '"2 Seconds(&2)"'),
    ('"3秒(&3)"', '"3 Seconds(&3)"'),
    ('"4秒(&4)"', '"4 Seconds(&4)"'),
    ('"5秒(&5)"', '"5 Seconds(&5)"'),
    ('"アンチエイリアス(&A)"', '"Font Smoothing(&A)"'),
    ('"フォント(&D) ..."', '"Font(&D) ..."'),
    ('"ヘルプ(&H)"', '"Help(&H)"'),
    ('"目次(&I) ..."', '"Contents(&I) ..."'),
    ('"このソフトについて(&A) ..."', '"About This Software(&A) ..."'),
    ('"デバッグ(&D)"', '"Debug(&D)"'),
    ('"シナリオの再読込み(&R)"', '"Reload Scenario(&R)"'),
    ('"コンソール(&C)\\tShift+F4"', '"Console(&C)\\tShift+F4"'),
    ('"コントローラ(&S)\\tShift+F1"', '"Controller(&S)\\tShift+F1"'),
]

MAINWINDOW = [
    # Save/Load slot placeholder rows (keep fullwidth dash framing)
    ('"－クイックセーブ用－"', '"－For Quick Save－"'),
    ('"－未使用－"', '"－Unused－"'),
    ('"(未設定)"', '"(Not Set)"'),
    # bookmark-name brackets -> ASCII (only the 5 prompt lines use them)
    ('"\u300c"', '"["'),
    ('"\u300d"', '"]"'),
    ('"\u306b\u300c"', '" to ["'),
    ('"\u300dまで戻りますか?"', '"] Return? "'),
    ('"\u300dを上書きしますか\uff1f"', '"] overwrite? "'),
    ('"\u300dをセーブしますか\uff1f"', '"] save? "'),
    ('"\u300dをロードしますか\uff1f"', '"] load? "'),
    # Slot prefix in save/load prompts
    ('"スロット "', '"Slot "'),
    # Exit + return-to-title confirmations
    ('"終了しますか\uff1f"', '"Are you sure you want to quit?"'),
    ('"タイトルに戻ります\u3002よろしいですか ?"', '"Return to the title screen? Are you sure?"'),
    # Bookmark file dialogs (keep functional filter spec exactly)
    ('"栞をはさむ"', '"Insert Bookmark"'),
    ('"栞をたどる"', '"Open Bookmark"'),
    ('"サムネイル画像付き栞データ(*.bmp)|*.bmp"', '"Bookmark with thumbnail(*.bmp)|*.bmp"'),
    ('"栞データ(*.kdt)|*.kdt"', '"Bookmark data(*.kdt)|*.kdt"'),
    # Font selection dialog (leave glyph sample text as-is)
    ('"フォントの選択"', '"Select Font"'),
    ('"フォントを選択してください"', '"Please select a font"'),
]

HISTORY = [
    ('"≪ 次ページ "', '"≪ Next Page "'),
    ('" 前ページ ≫"', '" Prev Page ≫"'),
    ('"≪ 前ページ "', '"≪ Prev Page "'),
    ('" 次ページ ≫"', '" Next Page ≫"'),
    ('"メッセージ履歴を閉じる"', '"Close message history"'),
]

YESNO = [
    ('"\u306f\u3044"', '"Yes"'),
    ('"\u3044\u3044\u3048"', '"No"'),
    ('"\u78ba\u8a8d"', '"Confirm"'),
]

FILES = [
    ('system/Menus.tjs', 'Menus.tjs', MENUS),
    ('system/MainWindow.tjs', 'MainWindow.tjs', MAINWINDOW),
    ('system/HistoryLayer.tjs', 'HistoryLayer.tjs', HISTORY),
    ('system/YesNoDialog.tjs', 'YesNoDialog.tjs', YESNO),
]

arc = Xp3Archive(SRC)
bn = {f['name']: f for f in arc.files}

def build(fname, base, pairs):
    raw = arc.extract_file(bn[fname])
    text = raw.decode('cp932')
    lines_old = text.split('\r\n')
    report = []
    for old, new in pairs:
        n = text.count(old)
        if n == 0:
            raise SystemExit('NO MATCH in %s: %r' % (fname, old))
        text = text.replace(old, new)
        report.append((old, n))
    lines_new = text.split('\r\n')
    diffs = []
    for i in range(max(len(lines_old), len(lines_new))):
        a = lines_old[i] if i < len(lines_old) else '<gone>'
        b = lines_new[i] if i < len(lines_new) else '<new>'
        if a != b:
            diffs.append((i + 1, a.rstrip(), b.rstrip()))
    open(os.path.join(OUTDIR, base), 'wb').write(text.encode('cp932'))
    return report, diffs

out_lines = []
for fname, base, pairs in FILES:
    report, diffs = build(fname, base, pairs)
    out_lines.append('=' * 70)
    out_lines.append('%s -> %s   (%d replacements, %d lines changed)' % (fname, base, len(report), len(diffs)))
    for old, n in report:
        out_lines.append('  x%d  %r' % (n, old))
    out_lines.append('-- changed lines --')
    for ln, a, b in diffs:
        out_lines.append('L%04d:' % ln)
        out_lines.append('   - %s' % a)
        out_lines.append('   + %s' % b)

open(os.path.join(OUTDIR, '_report_utf8.txt'), 'w', encoding='utf-8').write('\n'.join(out_lines) + '\n')
for l in out_lines:
    try:
        l.encode('ascii'); print(l)
    except Exception:
        pass
print('DONE. full report -> %s' % os.path.join(OUTDIR, '_report_utf8.txt'))
