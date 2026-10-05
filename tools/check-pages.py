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
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
BODY = re.compile(r'<div class="poem-body">(.*?)</div>', re.S)
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
for w in warn:
    print('%s warn: %s' % (WARN, w))
for e in fail:
    print('%s FAIL: %s' % (BAD, e))
if not fail:
    print('%s OK  (%d poems / %d volumes)' % (OK, len(poem_files), len(vol_files)))
sys.exit(1 if fail else 0)
