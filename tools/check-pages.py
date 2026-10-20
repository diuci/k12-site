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
CJK = re.compile(r'[\u4e00-\u9fff]')

# 标记只用 ASCII：Windows 控制台默认 GBK，U+2713 会直接抛 UnicodeEncodeError
OK, BAD, WARN = '[ok]', '[!!]', '[--]'

fail = []
warn = []


# ---- 判定逻辑做成纯函数：喂一段 HTML 字符串就能测，坏例子不必先构建整站 ----
def body_cjk_count(text):
    """poem-body 那一块里有多少个汉字。没有这个 div 也算 0——「没生成」和「生成了空的」必须同样被抓出来。"""
    m = BODY.search(text)
    return len(CJK.findall(m.group(1) if m else ''))


def poem_page_problems(text):
    """这一页缺什么。返回标签列表，空列表 = 没问题。"""
    out = []
    if body_cjk_count(text) == 0:
        out.append('empty_body')
    if '<ruby>' not in text:
        out.append('no_pinyin')
    if 'poem-title' not in text or 'm-author' not in text:
        out.append('no_head')
    return out


def volume_page_problems(text):
    """册次页：短到不像一页、或者根本没链到诗，都算空。"""
    out = []
    if len(text.strip()) < 200:
        out.append('too_short')
    if '/poems/' not in text:
        out.append('no_poem_links')
    return out


def selftest():
    """这条体检自己也得有坏例子：它存在的理由就是「148 篇空页全都照样绿」。
    判定逻辑做成纯函数之后，坏例子不必先构建整站，喂字符串就能测。"""
    tried = [0]

    def must(cond, msg):
        tried[0] += 1
        assert cond, msg

    good = ('<h1 class="poem-title">靜夜思</h1><p class="m-author">李白</p>'
            '<div class="poem-body"><p><ruby>床<rt>chuáng</rt></ruby>前明月光</p></div>')
    must(poem_page_problems(good) == [], '坏例1：正常的页被报了')

    # 坏例2：当年的真事故——页面 200、链接全通，诗却是空的
    empty = '<h1 class="poem-title">靜夜思</h1><p class="m-author">李白</p><div class="poem-body"></div>'
    must('empty_body' in poem_page_problems(empty), '坏例2：空的 poem-body 没被抓出来')
    # 坏例3：连 div 都没生成，必须同样抓出来（「没生成」不许长得像「没问题」）
    no_div = '<h1 class="poem-title">靜夜思</h1><p class="m-author">李白</p>'
    must('empty_body' in poem_page_problems(no_div), '坏例3：没有 poem-body 却没被抓出来')
    # 坏例4：div 里只有标点没有汉字，也算空
    punct = '<div class="poem-body">，。！</div>'
    must(body_cjk_count(punct) == 0, '坏例4：只有标点的正文被当成有内容')

    # 坏例5：没注音 / 缺标题作者，各自必须单独抓出来
    must('no_pinyin' in poem_page_problems(good.replace('<ruby>', '')), '坏例5：没注音没被抓出来')
    must('no_head' in poem_page_problems(good.replace('m-author', 'x-author')), '坏例5b：缺作者没被抓出来')
    must('no_head' in poem_page_problems(good.replace('poem-title', 'x-title')), '坏例5c：缺标题没被抓出来')

    # 坏例6：册次页——短到不像一页 / 没链到诗，都必须抓出来；正常的不许误报
    vol_good = ('# 七年级上册\n\n' + '\n'.join('[诗%d](/poems/初中/七年级上册/诗%d.html)' % (i, i) for i in range(30)))
    must(volume_page_problems(vol_good) == [], '坏例6：正常的册次页被报了')
    must('too_short' in volume_page_problems('# 七年级上册\n\n（空）'), '坏例6b：短到不像一页却没被抓出来')
    must('no_poem_links' in volume_page_problems(vol_good.replace('/poems/', '/other/')),
         '坏例6c：册次页没链到任何诗却没被抓出来')

    # 繁体侧检查已随 v4 退役（全站仅简体，/trad/ 页下线）：
    # simp_only_from_table / residual_simplified 及坏例 7~12 一并删除。

    print('[ok] check-pages --selftest 通（当场数到 %d 个坏例子，全部试到）' % tried[0])
    return 0


if '--selftest' in sys.argv:
    sys.exit(selftest())



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
    total_cjk += body_cjk_count(t)
    probs = poem_page_problems(t)
    if 'empty_body' in probs:
        empty_body.append(f.relative_to(SITE))
    if 'no_pinyin' in probs:
        no_pinyin.append(f.relative_to(SITE))
    if 'no_head' in probs:
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
    if volume_page_problems(f.read_text(encoding='utf-8')):
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
