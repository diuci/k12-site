# -*- coding: utf-8 -*-
"""K12 站点产物体检：抓「生成出来是空的」这类静默故障。

起因：build-site.py 的正文节选择曾被一个空的占位节抢走，
253 篇里有 148 篇生成了空的 <div class="poem-body"></div>——
页面 HTTP 200、死链扫描 0 问题，唯独诗就是空的，肉眼不点开看不出来。

这类故障的共同点是**不报错**：构建成功、部署成功、链接全通。
所以必须有一条只看产物的断言。

用法：
    python tools/build-site.py && python tools/check-pages.py
"""
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
BODY = re.compile(r'<div class="poem-body">(.*?)</div>', re.S)
HREF = re.compile(r'href="[^"]*"')
CJK = re.compile(r'[\u4e00-\u9fff]')

# 标记只用 ASCII：Windows 控制台默认 GBK，U+2713 会直接抛 UnicodeEncodeError
OK, BAD, WARN = '[ok]', '[!!]', '[--]'

fail = []
warn = []

poem_files = sorted((SITE / 'poems').rglob('*.md')) if (SITE / 'poems').exists() else []
vol_files = sorted((SITE / 'vol').rglob('*.md')) if (SITE / 'vol').exists() else []

print('=== K12 artifact health check ===')
print('')

print('1) poem body is non-empty')
empty_body = []
no_pinyin = []
no_head = []
total_cjk = 0
for f in poem_files:
    t = f.read_text(encoding='utf-8')
    m = BODY.search(t)
    n_cjk = len(CJK.findall(m.group(1) if m else ''))
    total_cjk += n_cjk
    if n_cjk == 0:
        empty_body.append(f.relative_to(SITE))
    if '<ruby>' not in t:
        no_pinyin.append(f.relative_to(SITE))
    if 'poem-title' not in t or 'm-author' not in t:
        no_head.append(f.relative_to(SITE))
print('   %d poems, %d CJK chars total' % (len(poem_files), total_cjk))
if empty_body:
    fail.append('%d poems have an empty body, e.g. %s' % (len(empty_body), empty_body[0]))
    print('   %s empty body: %d  e.g. %s' % (BAD, len(empty_body), empty_body[0]))
else:
    print('   %s every poem body is non-empty' % OK)
if no_pinyin:
    warn.append('%d poems without pinyin (CONTENT_ROOT not set?)' % len(no_pinyin))
    print('   %s no pinyin: %d' % (WARN, len(no_pinyin)))
else:
    print('   %s every poem carries ruby pinyin' % OK)
if no_head:
    fail.append('%d poems missing title/author' % len(no_head))
    print('   %s missing title/author: %d' % (BAD, len(no_head)))
else:
    print('   %s title/author present' % OK)

print('')
print('2) volume pages')
empty_vol = []
for f in vol_files:
    t = f.read_text(encoding='utf-8')
    if len(t.strip()) < 200 or '/poems/' not in t:
        empty_vol.append(f.relative_to(SITE))
print('   %d volumes' % len(vol_files))
if empty_vol:
    fail.append('%d empty volume pages' % len(empty_vol))
    print('   %s empty: %d' % (BAD, len(empty_vol)))
else:
    print('   %s every volume page links its poems' % OK)

print('')
print('3) catalog.json')
cat = SITE / 'public' / 'catalog.json'
if not cat.exists():
    fail.append('catalog.json missing')
    print('   %s missing site/public/catalog.json' % BAD)
else:
    data = json.loads(cat.read_text(encoding='utf-8'))
    arr = data if isinstance(data, list) else (data.get('poems') or data.get('items') or [])
    if not isinstance(arr, list) or not arr:
        fail.append('catalog.json structure unexpected')
        print('   %s unexpected structure: %s' % (BAD, type(data)))
    else:
        print('   %d entries' % len(arr))
        if len(arr) != len(poem_files):
            warn.append('catalog %d entries vs %d poems' % (len(arr), len(poem_files)))
            print('   %s count mismatch (%d vs %d)' % (WARN, len(arr), len(poem_files)))
        else:
            print('   %s matches poem count' % OK)

print('')
print('4) placeholder sections (content gaps, not build bugs)')
pending = 0
for f in poem_files:
    if '正在编写中' in f.read_text(encoding='utf-8'):
        pending += 1
print('   %d of %d poems still have notes/translation/appreciation placeholders'
      % (pending, len(poem_files)))
if pending:
    warn.append('%d poems still lack notes/translation/appreciation' % pending)

print('')
print('5) traditional tree (繁體版)')
TR = SITE / 'trad'
tp = sorted((TR / 'poems').rglob('*.md')) if (TR / 'poems').exists() else []
tv = sorted((TR / 'vol').rglob('*.md')) if (TR / 'vol').exists() else []
if not tp:
    fail.append('no traditional poem pages at all')
    print('   %s site/trad/poems is empty' % BAD)
else:
    print('   %d traditional poems, %d traditional volumes' % (len(tp), len(tv)))
    if len(tp) != len(poem_files):
        fail.append('traditional %d vs simplified %d' % (len(tp), len(poem_files)))
        print('   %s count mismatch (%d vs %d)' % (BAD, len(tp), len(poem_files)))
    else:
        print('   %s same count as simplified tree' % OK)
    if len(tv) != len(vol_files):
        fail.append('traditional volumes %d vs simplified %d' % (len(tv), len(vol_files)))

    # 只有简体才用的字：繁简表里凡是「这个简体字能转成别的字」的，都不许出现在繁体页上。
    # 出处核对一节引的是简体正文与来源页的比对，那一块按设计保留简体，扫描时剥掉。
    content_root = pathlib.Path(os.environ.get('CONTENT_ROOT') or (ROOT.parent / 'k12-chinese-poetry'))
    s2c = {}
    for name in ('STCharacters.txt', 'STPhrases.txt'):
        f_ = content_root / 'data' / 'opencc' / name
        if not f_.exists():
            continue
        for ln in f_.read_text(encoding='utf-8').splitlines():
            if '\t' in ln:
                k, v = ln.split('\t', 1)
                s2c.setdefault(k.strip(), set()).update(v.split())
    simp_only = {k for k, v in s2c.items() if k not in v}
    if not simp_only:
        fail.append('cannot load simplified-only chars from %s' % content_root)
        print('   %s cannot load the s2t table' % BAD)
    else:
        src_block = re.compile(r'<div class="poem-sourcecheck">.*?</div>', re.S)
        # 每一篇允许残留哪些字，来自派生产物里那一行写着的依据
        allowed = {}
        led_p = content_root / 'data' / 'ledger.json'
        tr_p = content_root / 'data' / 'traditional.json'
        if led_p.exists() and tr_p.exists():
            rows_t = {r.get('id'): r for r in json.loads(tr_p.read_text(encoding='utf-8')).get('rows', [])}
            for lr in json.loads(led_p.read_text(encoding='utf-8')).get('rows', []):
                r_t = rows_t.get(lr.get('id'))
                if not r_t:
                    continue
                key = str(lr.get('path') or '').replace('poems/', '', 1).replace('\\', '/')
                allowed[key] = {x.get('char') for x in (r_t.get('left_behind') or [])
                                if isinstance(x, dict) and (x.get('why') or '').strip()}
        hits, no_switch, no_ruby, empty_t = [], [], [], []
        for f in tp:
            raw = f.read_text(encoding='utf-8')
            t_body = BODY.search(raw)
            if not t_body or not CJK.findall(t_body.group(1)):
                empty_t.append(f.relative_to(TR))
            if '<ruby>' not in raw:
                no_ruby.append(f.relative_to(TR))
            if 'href="/poems/' not in raw:
                no_switch.append(f.relative_to(TR))
            # href 里的中文是网址本身（我们的 URL 就是简体拼音之外的中文路径），不是页面上给读者看的字形
            rel_key = str(f.relative_to(TR / 'poems')).replace('\\', '/')
            ok_chars = allowed.get(rel_key, set())
            bad_chars = sorted({ch for ch in HREF.sub('href=""', src_block.sub('', raw))
                                if ch in simp_only and ch not in ok_chars})
            if bad_chars:
                hits.append((f.relative_to(TR), ''.join(bad_chars[:8])))
        if empty_t:
            fail.append('%d traditional poems have an empty body' % len(empty_t))
            print('   %s empty traditional body: %d e.g. %s' % (BAD, len(empty_t), empty_t[0]))
        else:
            print('   %s every traditional body is non-empty' % OK)
        if no_ruby:
            fail.append('%d traditional poems carry no pinyin' % len(no_ruby))
            print('   %s no ruby: %d' % (BAD, len(no_ruby)))
        else:
            print('   %s traditional lines carry ruby from the aligned simplified lines' % OK)
        if no_switch:
            fail.append('%d traditional poems have no link back to the simplified page' % len(no_switch))
            print('   %s no switch link: %d' % (BAD, len(no_switch)))
        else:
            print('   %s every traditional page links back to 简体版' % OK)
        if hits:
            fail.append('%d traditional pages still contain simplified-only chars, e.g. %s: %s'
                        % (len(hits), hits[0][0], hits[0][1]))
            print('   %s simplified-only chars left: %d e.g. %s → %s'
                  % (BAD, len(hits), hits[0][0], hits[0][1]))
        else:
            print('   %s no simplified-only characters outside the source-check quotes' % OK)
        back = [f for f in poem_files if 'href="/trad/poems/' not in f.read_text(encoding='utf-8')]
        if back:
            fail.append('%d simplified poems have no link to the traditional page' % len(back))
            print('   %s no switch link: %d' % (BAD, len(back)))
        else:
            print('   %s every simplified page links to 繁體版' % OK)
        if not (TR / 'index.md').exists():
            fail.append('site/trad/index.md missing')
        else:
            print('   %s 繁體版说明页在' % OK)

print('')
for w in warn:
    print('%s warn: %s' % (WARN, w))
for e in fail:
    print('%s FAIL: %s' % (BAD, e))
if not fail:
    print('%s OK  (%d poems / %d volumes)' % (OK, len(poem_files), len(vol_files)))
sys.exit(1 if fail else 0)
