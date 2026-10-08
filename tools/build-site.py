#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 poems/*.md 转成 VitePress 站点页面。

单篇 .md 已经是「人读的文章」，但它缺少站点需要的东西：拼音、玩法标签、
面包屑导航。本脚本在不改动 poems/ 的前提下，生成 site/ 下的站点副本。

产出：
  site/.vitepress/catalog.json      篇目总目录（供筛选/搜索用）
  site/.vitepress/theme/*.css       样式（诗词排版、打印版）
  site/poems/<学段>/<册次>/<篇名>.md ← 站点页面
  site/index.md                首页（自动生成，含三轴筛选数据）
  site/print.md                    A4 打印版（全部篇目纯文本）

用法：
    python tools/build-site.py
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get('CONTENT_ROOT') or Path(__file__).resolve().parent.parent)
POEMS = ROOT / 'poems'
SITE = Path(__file__).resolve().parent.parent / 'site'
DATA = ROOT / 'data' / 'poems.json'

SITE_POEMS = SITE / 'poems'
# 册次列表页：site/vol/<学段>/<册次>.md
# 与单篇页面分开目录，侧栏分类项指向这里。
SITE_VOL = SITE / 'vol'


def die(msg):
    print('[site] ERROR: ' + msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- 拼音
# 站点给孩子用，加拼音能显著降低阅读门槛。这里用「汉字 → 拼音」的小表，
# 只覆盖篇目里出现的字；查不到的留空（不报错），可后续补全。
#数据来源：GB/T 16159-2012《汉字拼音方案》常用字表
PINYIN = {}


def load_pinyin():
    """从 data/pinyin.txt 读「汉字 拼音」对照表（每行一个），缺失则跳过。"""
    p = ROOT / 'data' / 'pinyin.txt'
    if not p.exists():
        return 0
    n = 0
    for line in p.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 1:
            PINYIN[parts[0]] = parts[1]
            n += 1
    return n


def with_pinyin(text):
    """给一行汉字加拼音（HTML ruby 注音）。查不到的字不注，留原样。"""
    if not PINYIN:
        return text
    out = []
    for ch in text:
        if ch in PINYIN:
            out.append('<ruby>%s<rp>（</rp><rt>%s</rt><rp>）</rp></ruby>'
                       % (ch, PINYIN[ch]))
        else:
            out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------- 解析
def parse_poem(md_path):
    """读单篇 md，拆出 frontmatter 各字段与正文各节。"""
    text = md_path.read_text(encoding='utf-8')
    parts = text.split('---', 2)
    if len(parts) < 3:
        die('%s: frontmatter 未闭合' % md_path.name)
    fm_text, body = parts[1], parts[2]

    fm = {}
    key = None
    for raw in fm_text.splitlines():
        if not raw.strip():
            continue
        m = re.match(r'^(\w+):\s*(.*)$', raw)
        if m:
            key = m.group(1)
            v = m.group(2).strip()
            fm[key] = parse_scalar(v)
        elif raw.lstrip().startswith('- ') and key:
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(raw.lstrip()[2:].strip())

    # 正文按 H2 分节。注意两种结构：
    #   小学：H1 之后**没有** H2 包裹，正文直接跟在元信息引用行后
    #   初中/高中：正文包在「## 必背全文」/「## 必背名句」里
    # 所以 H1 之后、首个 H2 之前的内容也要收集，作为无标题的正文段。
    sections = {}
    cur = None
    buf = []
    seen_h1 = False

    def flush():
        # 必须判 strip() 之后的结果，不能只判 buf 非空。
        # 初中/高中结构里，H1 与首个 H2 之间隔着空行，于是 buf=['',''] 是「非空的」，
        # 但拼出来是空串——如果照样存进去，sections 里就会多出一个空的 '正文'。
        # 后面挑正文节时按插入顺序遍历，空的 '正文' 排在 '必背名句' 前面就被选中了，
        # 结果整页正文渲染成空 div（253 篇里有 148 篇中招）。
        if cur is not None and buf:
            t = '\n'.join(buf).strip()
            if t:
                sections[cur] = t

    for raw in body.splitlines():
        s = raw.strip()
        if s.startswith('# '):
            flush()
            cur, buf = None, []
            seen_h1 = True
            continue
        if not seen_h1:
            continue
        if s.startswith('## '):
            flush()
            cur = s[3:].strip()
            buf = []
            continue
        if s.startswith('>'):
            continue                    # 元信息引用行
        if cur is None:
            # 首个 H2 之前的内容 = 正文（小学结构）
            cur = '正文'
        buf.append(raw)
    flush()

    title_line = ''
    m = re.search(r'^#\s+(.+)$', body, re.M)
    if m:
        title_line = m.group(1).strip()

    return fm, sections, title_line


def parse_scalar(v):
    if v in ('null', '~', ''):
        return None
    if v == 'true':
        return True
    if v == 'false':
        return False
    if v.startswith('[') and v.endswith(']'):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip('\'"') for x in inner.split(',')]
    if re.match(r'^-?\d+$', v):
        return int(v)
    if re.match(r'^-?\d+\.\d+$', v):
        return float(v)
    if v.startswith('{') and v.endswith('}'):
        out = {}
        for part in re.findall(r'(\w+):\s*([^,}]+)', v[1:-1]):
            out[part[0]] = part[1].strip().strip('\'"')
        return out
    return v


# ---------------------------------------------------------------- 渲染
RECITE_LABEL = {
    'full': '全文背诵',
    'section': '背诵段落',
    'line': '背诵名句',
    'none': '理解为主',
}

# 教材收录状态：内容仓 data/volume-findings.json 算出来的事实，站点必须显示出来。
# 「课标要背但教材没有这一课」是学生会踩的坑，藏着不说是坑学生。
TS_LABEL = {
    '统编教材未收（课标要求）': '教材未收 · 课标要背',
    '统编教材收的是同名另一篇': '教材同名不同篇',
    '统编教材收在别的课里': '教材收在别的课里',
}
# 课标把它列在高中 40 首里，统编教材却把它放在小学/初中某一册。
# 仓里只有一份（挂在教材实际所在的那一册），站点必须在高考默写表里也列出来，并写明实际在哪一册。
STAGE_CROSS = {
    'shanjuqiuming': {
        'group': '诗词曲', 'no': 9,
        'note': '课标高中 40 首里的第 9 首；统编教材实际把它放在五年级上册第 21 课《古诗三首》。'
    },
}

GK_GROUPS = [
    ('必修', '文言文 · 必修部分', '2023 年起'),
    ('选择性必修', '文言文 · 选择性必修部分', '2023 年起'),
    ('选修', '文言文 · 选修部分', '2026 年起新增'),
    ('诗词曲', '诗词曲', '2023 年起'),
]

TS_NOTE = {
    '统编教材未收（课标要求）': '课标要求背诵，但统编教材的课文目录里没有这一篇——按教材上课要自己补。',
    '统编教材收的是同名另一篇': '教材里有一篇同名课文，但那是另一篇内容；这一篇按课标收录。',
    '统编教材收在别的课里': '这一篇统编教材收了，只是篇名和课标不一样——按标题在目录里找不到，但课确实有。',
}


def highlight_recite(text, recite_lines):
    """全文里，把要背的那几句标出来。

    按句子切，不按整行切：一篇文言文的整行里往往既有必背句也有不背的部分，
    整行标粗等于告诉学生「这段全背」，那是错的。
    """
    keys = []
    for ln in recite_lines:
        for part in re.split(r'[。！？；]', ln):
            k = re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', part)
            if len(k) >= 4:
                keys.append(k)
    if not keys:
        return text
    out = []
    for line in text.split('\n'):
        s = line.strip()
        if not s or s.startswith('>'):
            out.append(line)
            continue
        segs = []
        for part in re.split(r'(?<=[。！？；])', s):
            k = re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', part)
            # 三个方向都要试。只试 key in k 会漏一种写法：全文按句读断行（客至把「舍南舍北皆春水，」单独成行），
            # 这时整行的键比必背句的键短，它是必背句的一部分。
            if k and any(k == key or key in k or k in key for key in keys):
                segs.append('<b class="rh">%s</b>' % part)
            else:
                segs.append(part)
        out.append(''.join(segs))
    return '\n'.join(out)

STAGE_ORDER = ['小学', '初中', '高中']


# 这些节在别处已经渲染过了，通用块不能再渲染一遍。
RENDERED_ELSEWHERE = {'必背名句', '必背全文', '全文', '正文', '注释', '译文', '赏析', '玩法数据'}


def render_page(fm, sections, title_line, catalog_entry):
    """生成单篇站点页面。"""
    sid = fm.get('id')
    title = fm.get('title')
    author = fm.get('author')
    dyn = fm.get('dynasty')
    form = fm.get('form')
    stage = fm.get('stage')
    volume = fm.get('volume')
    theme = fm.get('theme') or []
    tech = fm.get('technique') or []
    recite = fm.get('recite')

    L = []
    L.append('---')
    L.append('title: %s' % title)
    L.append('description: %s · %s · %s' % (author, dyn, title))
    L.append('outline: [2, 3]')
    L.append('---')
    L.append('')

    # ---- 题头信息卡
    L.append('<div class="poem-head">')
    L.append('  <h1 class="poem-title">%s</h1>' % title)
    L.append('  <div class="poem-meta">')
    L.append('    <span class="m-author">%s</span>' % author)
    L.append('    <span class="m-dyn">%s</span>' % dyn)
    L.append('    <span class="m-form">%s</span>' % form)
    L.append('    <span class="m-stage">%s</span>' % stage)
    L.append('    <span class="m-vol">%s</span>' % volume)
    L.append('  </div>')
    ts = fm.get('textbookStatus')
    # 标签区：背诵要求（若有）+ 教材收录状态 + 主题 + 手法，任一存在就渲染
    if recite or theme or tech or TS_LABEL.get(ts):
        L.append('  <div class="poem-tags">')
        if recite:
            L.append('    <span class="tag tag-recite">%s</span>'
                     % RECITE_LABEL.get(recite, recite))
        for t in theme:
            L.append('    <span class="tag">%s</span>' % t)
        for t in tech:
            L.append('    <span class="tag tag-tech">%s</span>' % t)
        if TS_LABEL.get(ts):
            L.append('    <span class="tag tag-tb">%s</span>' % TS_LABEL[ts])
        L.append('  </div>')
    L.append('</div>')
    L.append('')

    # ---- 正文（必背全文/名句，或小学的无标题正文）
    main_key = None
    for k in sections:
        # 顺带再挡一次：宁可挑一个真有内容的节，也不要挑到空节。
        if (k.startswith('必背') or k == '正文') and sections.get(k, '').strip():
            main_key = k
            break
    if main_key is None:
        # 兜底：小学以外偶尔有不叫「必背*」的正文节名，宁可取第一个有内容的节
        for k, v in sections.items():
            if v.strip() and k not in ('注释', '译文', '赏析', '玩法数据'):
                main_key = k
                break
    if main_key and not sections[main_key].strip():
        raise SystemExit('[build-site] %s：正文节「%s」是空的，生成出来会是一个空 div' % (rel, main_key))
    if main_key:
        L.append('<div class="poem-body">')
        L.append(with_pinyin(sections[main_key]))
        L.append('</div>')
        L.append('')

    # ---- 全文：仓里收全了的篇目，把整篇也放出来，并标出其中要背的那几句
    full_txt = (sections.get('全文') or sections.get('必背全文') or '').strip()
    if full_txt and main_key and full_txt != sections.get(main_key, '').strip():
        recite_lines = [x.strip() for x in sections.get(main_key, '').split('\n') if x.strip()]
        L.append('<div class="poem-full">')
        L.append('  <h2 class="full-h">全文<span class="full-sub">加粗的是要背的部分</span></h2>')
        L.append('  <div class="full-body">')
        L.append(highlight_recite(full_txt, recite_lines))
        L.append('  </div>')
        L.append('</div>')
        L.append('')

    # ---- 教材收录状态说明
    if TS_NOTE.get(ts):
        covered = fm.get('textbookCoveredBy')
        note = TS_NOTE[ts]
        if covered:
            note += '它在教材里的这些课：' + covered + '。'
        L.append('<p class="tb-note">%s</p>' % note)
        L.append('')

    # ---- 高考默写范围：属不属于默写范围、属哪一组、哪一年开始考
    cross = STAGE_CROSS.get(sid)
    gk_group = catalog_entry.get('gaokaoGroup') or (cross or {}).get('group')
    if gk_group:
        gk_no = catalog_entry.get('gaokaoNo') or (cross or {}).get('no')
        gk_since = catalog_entry.get('gaokaoSince') or 2023
        gk_name = {g: n for g, n, _ in GK_GROUPS}.get(gk_group, gk_group)
        L.append('<p class="gk-note">高考默写范围 · %s · 第 %s 篇 · %d 年起考</p>' % (gk_name, gk_no, gk_since))
        L.append('')
    if cross:
        L.append('<p class="tb-note">%s 仓里只有一份，挂在教材实际所在的那一册，不重复挂到高中。</p>' % cross['note'])
        L.append('')

    # ---- 注释 / 译文 / 赏析
    plain = {
        '注释': 'note', '译文': 'trans', '赏析': 'appr',
    }
    for sec, css in plain.items():
        body_txt = sections.get(sec, '')
        if not body_txt:
            continue
        if '待补' in body_txt and len(body_txt.strip()) < 40:
            L.append('<div class="pending">')
            L.append('  <h2>%s</h2>' % sec)
            L.append('  <p class="pending-note">%s 正在编写中</p>' % sec)
            L.append('</div>')
            continue
        L.append('<div class="poem-%s">' % css)
        L.append('## %s' % sec)
        L.append('')

        L.append(body_txt)
        L.append('</div>')
        L.append('')
    # ---- 收录范围 / 异文：版本与教材差异的考证，必须让学生看得到
    shown = set()
    for sec, css in (('收录范围', 'scope'), ('异文', 'variant')):
        body_txt = sections.get(sec, '')
        if not body_txt.strip():
            continue
        shown.add(sec)
        L.append('<div class="poem-%s">' % css)
        L.append('## %s' % sec)
        L.append('')
        if sec == '异文':
            # 默认口径要写在页面上，不能只在文档里：237 条异文没有「取舍」，不是漏写，
            # 是默认就不改正文。（这个默认有护栏核对：内容仓 check-variant-defaults.py。）
            L.append('> 默认：下面只登记别的版本怎么写，**仓内正文不改**，用字以统编教材与来源页主文为准。')
            L.append('> 写了「取舍」的条目，才是这一处真做过选择。')
            L.append('')
        L.append(body_txt)
        L.append('</div>')
        L.append('')
    # 仓里写了的小节，站点一个都不许漏。之前「考点 / 旧文本裁定 / 出处核对 / 教材所选四章 /
    # 收录范围（第六段…）」这些节在仓里存在、页面上却完全看不见——考证写在只有 git 里能看到的
    # 文件里，等于没写。剩下的节一律按通用块渲染，不再靠一份名单去猜。
    for sec, body in sections.items():
        if sec in shown or sec in RENDERED_ELSEWHERE or not body.strip():
            continue
        shown.add(sec)
        L.append('<div class="poem-note">')
        L.append('## %s' % sec)
        L.append('')
        L.append(body)
        L.append('</div>')
        L.append('')

    # ---- 玩法数据
    game = sections.get('玩法数据', '')
    if game:
        L.append('<div class="poem-game">')
        L.append('## 玩法数据')
        L.append('')
        L.append(game)
        L.append('</div>')

    L.append('<div class="poem-foot">')
    L.append('  <a class="back" href="/">← 返回总览</a>')
    L.append('  <span class="src">来源：%s ｜ 许可：%s</span>'
             % (fm.get('source', ''), fm.get('license', '')))
    L.append('</div>')

    return '\n'.join(L) + '\n'


# ---------------------------------------------------------------- 主流程
def esc(s):
    return (str(s if s is not None else '')
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def render_volume_page(stage, volume, entries):
    """生成册次列表页：列出该册全部篇目。

    侧栏的「小学 / 一年级上册」这类分类必须先落到列表页，
    再由用户挑具体篇目；否则点进去直接就是一首诗。
    """
    L = ['---',
         'title: %s · %s' % (volume, stage),
         'description: %s%s 全部 %d 篇古诗文，含原文、注释、译文与赏析。'
                    % (stage, volume, len(entries)),
         'sidebar: false',
         'aside: false',
         '---',
         '']

    L.append('<div class="hero vol-hero">')
    L.append('  <div class="wrap-alt">')
    L.append('    <nav class="crumbs" aria-label="面包屑">')
    L.append('      <a href="/">总览</a>')
    L.append('      <span class="sep">/</span>')
    L.append('      <span class="cur">%s</span>' % volume)
    L.append('    </nav>')
    L.append('    <span class="eyebrow"><span class="dot"></span>%s · 全部 %d 篇</span>'
             % (stage, len(entries)))
    L.append('    <h1>%s</h1>' % volume)
    L.append('    <p class="hero-sub">这一册的<b>%d 篇</b>都在下面，按教材顺序排。</p>'
             % len(entries))
    L.append('  </div>')
    L.append('</div>')
    L.append('')
    L.append('<div class="wrap-alt">')
    L.append('  <div class="grid vol-grid" id="vol-grid">')
    for e in entries:
        badge = (RECITE_LABEL.get(e['recite'], '')
                 if e.get('recite') and e['recite'] != 'none' else '')
        badge_html = ('<span class="badge badge-recite">%s</span>' % badge) if badge else ''
        L.append('    <a class="card" href="%s">' % e['url'])
        L.append('      <div class="card-t">%s%s</div>' % (e['title'], badge_html))
        L.append('      <div class="card-a">%s · %s</div>'
                 % (e.get('author') or '', e.get('dynasty') or ''))
        if e.get('lines'):
            L.append('      <div class="card-l">%s</div>' % e['lines'])
        L.append('      <div class="card-g">%s</div>' % volume)
        L.append('    </a>')
    L.append('  </div>')
    L.append('  <p class="count" style="margin-top:24px">')
    L.append('    共 %d 篇 · <a href="/">返回总览</a>' % len(entries))
    L.append('  </p>')
    L.append('</div>')
    L.append('')
    return '\n'.join(L)


def render_gaokao_page(catalog):
    """高考默写范围一页：72 篇按课标的四组排出来。

    这张表必须存在，因为「2025 及以前考 60 篇、2026 起考 72 篇」这件事
    只写在内容仓的 docs 里，学生看不到；看不到就会按错的篇数准备。
    """
    items = [e for e in catalog if e.get('gaokaoGroup')]
    if not items:
        die('没有任何一篇带高考默写分组，gaokao 页会是空的')
    L = ['---', 'title: 高考默写范围', 'description: 课标要求的 72 篇默写范围，按四组排列', '---', '']
    L.append('')
    L.append('<div class="hero vol-hero">')
    L.append('  <div class="wrap-alt">')
    L.append('    <nav class="crumbs" aria-label="面包屑">')
    L.append('      <a href="/">总览</a><span class="sep">/</span><span class="cur">高考默写范围</span>')
    L.append('    </nav>')
    L.append('    <span class="eyebrow"><span class="dot"></span>课标 2017 · 默写篇目</span>')
    L.append('    <h1>高考默写范围</h1>')
    L.append('    <p class="hero-sub">文言文 <b>32</b> 篇 + 诗词曲 <b>40</b> 首，共 <b>72</b> 篇。</p>')
    L.append('  </div>')
    L.append('</div>')
    L.append('')
    L.append('<div class="wrap-alt">')
    L.append('  <div class="gk-rule">')
    L.append('    <p><b>2025 及以前：60 篇。</b>必修 10 + 选择性必修 10 + 诗词曲 40。</p>')
    L.append('    <p><b>2026 年起：72 篇。</b>在这 60 篇之外，新增文言文选修部分 12 篇。</p>')
    L.append('    <p>每一篇都标了哪一年开始考。按 60 篇准备、却考到 2026 新增的 12 篇，是这一页要防的错。</p>')
    L.append('  </div>')
    L.append('')
    for group, label, since_note in GK_GROUPS:
        rows = sorted([e for e in items if e['gaokaoGroup'] == group],
                      key=lambda x: (x.get('gaokaoNo') or 999, x['title']))
        if not rows:
            continue
        L.append('  <h2 class="gk-h">%s<span class="gk-sub">%d 篇 · %s</span></h2>' % (label, len(rows), since_note))
        L.append('  <ol class="gk-list">')
        for e in rows:
            L.append('    <li class="gk-item">')
            L.append('      <span class="gk-no">%s</span>' % (e.get('gaokaoNo') or '—'))
            L.append('      <a class="gk-t" href="%s">%s</a>' % (e['url'], esc(e['title'])))
            L.append('      <span class="gk-a">%s · %s</span>' % (esc(e.get('author') or ''), esc(e.get('dynasty') or '')))
            L.append('      <span class="gk-v">%s</span>' % esc(e.get('volume') or ''))
            if e.get('gaokaoSince') and e['gaokaoSince'] > 2023:
                L.append('      <span class="gk-since">%d 起</span>' % e['gaokaoSince'])
            if e['id'] in STAGE_CROSS:
                L.append('      <span class="gk-cross">%s</span>' % esc(STAGE_CROSS[e['id']]['note']))
            L.append('    </li>')
        L.append('  </ol>')
    L.append('')
    L.append('  <p class="count">共 %d 篇 · <a href="/">返回总览</a></p>' % len(items))
    L.append('</div>')
    L.append('')
    return '\n'.join(L)


def render_print(catalog):
    """生成 A4 打印版：全部篇目纯文本，按学段分页。"""
    L = ['---', 'title: 打印版', '---', '']
    L.append('# 学古诗 · 丢词夺理 · 打印版')
    L.append('')
    L.append('全部 %d 篇，按学段与册次排列。适合打印装订成册。' % len(catalog))
    L.append('')
    L.append('> 打印建议用 A4 纸。篇目页与本打印版都已适配打印样式。')
    L.append('')

    by_stage = {}
    for e in catalog:
        by_stage.setdefault(e['stage'], []).append(e)

    for stage in STAGE_ORDER:
        items = by_stage.get(stage)
        if not items:
            continue
        L.append('<div class="page-break"></div>')
        L.append('## %s（%d 篇）' % (stage, len(items)))
        L.append('')

        by_vol = {}
        for e in items:
            by_vol.setdefault(e['volume'], []).append(e)

        for vol in sorted(by_vol):
            L.append('### %s' % vol)
            L.append('')
            for e in sorted(by_vol[vol], key=lambda x: x['title']):
                L.append('<div class="print-item">')
                L.append('  <div class="p-title">%s<span class="p-author">%s · %s</span></div>'
                         % (esc(e['title']), esc(e['author']), esc(e['dynasty'])))
                if e.get('lines'):
                    L.append('  <div class="p-line">%s</div>' % esc(e['lines']))
                L.append('</div>')
                L.append('')
    return '\n'.join(L) + '\n'


def main():
    if not DATA.exists():
        die('缺少 data/poems.json，请先跑 python tools/build.py')

    # 高考默写分组是内容仓 build.py 算出来的（课标 2017 的四组 + 2026 起新增的选修 12 篇），
    # 它只写在 data/poems.json 里，不在篇的 frontmatter 里。站点要显示，就得从这份事实源读。
    gk_src = json.loads(DATA.read_text(encoding='utf-8')).get('poems', [])
    gk_map = {x.get('id'): x for x in gk_src}
    if not gk_map:
        die('data/poems.json 里没有篇目，高考默写页会是空的')
    n_pinyin = load_pinyin()

    # 清空旧的站点篇目（保留 .vitepress 与手写页面）
    if SITE_POEMS.exists():
        shutil.rmtree(SITE_POEMS)

    catalog = []
    for md in sorted(POEMS.rglob('*.md')):
        if md.name == '索引.md':
            continue
        fm, sections, title_line = parse_poem(md)
        rel = md.relative_to(POEMS)
        # 站点路径：保留 学段/册次 层级，但去掉可能含 Windows 保留名的目录
        parts = list(rel.parts[:-1]) + [md.stem + '.md']
        out = SITE_POEMS.joinpath(*parts)
        out.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            'id': fm.get('id'),
            'title': fm.get('title'),
            'subtitle': fm.get('subtitle'),
            'author': fm.get('author'),
            'dynasty': fm.get('dynasty'),
            # 公有领域证据：作者卒年（公元前为负）或佚名类的年代上限。
            # 站点公开这份数据，就该同时公开「凭什么说它是公有领域」。
            'authorDied': fm.get('authorDied'),
            'authorEraEnd': fm.get('authorEraEnd'),
            'form': fm.get('form'),
            'stage': fm.get('stage'),
            'grade': fm.get('grade'),
            'volume': fm.get('volume'),
            'theme': fm.get('theme') or [],
            'tech': fm.get('technique') or [],
            'recite': fm.get('recite'),
            'textbookStatus': fm.get('textbookStatus'),
            'textbookCoveredBy': fm.get('textbookCoveredBy'),
            'gaokaoGroup': (gk_map.get(fm.get('id')) or {}).get('gaokaoGroup')
                or (STAGE_CROSS.get(fm.get('id')) or {}).get('group'),
            'gaokaoNo': (gk_map.get(fm.get('id')) or {}).get('gaokaoNo')
                or (STAGE_CROSS.get(fm.get('id')) or {}).get('no'),
            'gaokaoSince': (gk_map.get(fm.get('id')) or {}).get('gaokaoSince')
                or ((STAGE_CROSS.get(fm.get('id')) or {}).get('group') and 2023),

            'freq': fm.get('exam_freq'),
            'difficulty': fm.get('difficulty'),
            'pairs': fm.get('pairs') or [],
            'lines': None,
            # 干净 URL，不带 .md：VitePress 产物是 .html，
            # 直接把源文件名当 href 会 404。首页卡片与各分类页都读这个字段。
            'url': '/poems/' + '/'.join(
                list(rel.parts[:-1]) + [md.stem]).replace('\\', '/'),
        }
        # 原文首句，供列表页展示
        main_key = next((k for k in sections
                         if k.startswith('必背') or k == '正文'), None)
        if main_key:
            first = next((x.strip() for x in sections[main_key].splitlines()
                          if x.strip()), '')
            entry['lines'] = re.sub(r'<[^>]+>', '', first)[:40]
        catalog.append(entry)

        out.write_text(render_page(fm, sections, title_line, entry),
                       encoding='utf-8')

    # ---- 册次列表页：每个 学段/册次 一页，列出该册全部篇目。
    # 侧栏分类项指向这里，避免「点分类直接出一首诗」。
    if SITE_VOL.exists():
        shutil.rmtree(SITE_VOL)
    by_vol = {}
    for e in catalog:
        by_vol.setdefault((e['stage'], e['volume']), []).append(e)

    vol_pages = 0
    for stage in STAGE_ORDER:
        for (st, vol), items in sorted(by_vol.items()):
            if st != stage:
                continue
            out = SITE_VOL / stage / (vol + '.md')
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_volume_page(stage, vol, items), encoding='utf-8')
            vol_pages += 1

    # ---- 目录 json（给首页筛选/搜索用）
    # 必须放site/public/ —— VitePress 会把 public 下的文件原样复制到输出，
    # 而 .vitepress/ 是配置目录，其中的静态文件不会被拷贝（会404）。
    pub = SITE / 'public'
    pub.mkdir(parents=True, exist_ok=True)
    (pub / 'catalog.json').write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1), encoding='utf-8')

    # ---- 打印版
    (SITE / 'print.md').write_text(render_print(catalog), encoding='utf-8')

    # ---- 高考默写范围一页
    (SITE / 'gaokao.md').write_text(render_gaokao_page(catalog), encoding='utf-8')

    print('[site] 生成 %d 个篇目页面%s'
          % (len(catalog),
             '（拼音表 %d 字）' % n_pinyin if n_pinyin else '（无拼音表）'))
    print('[site] 册次列表页：%d 个' % vol_pages)
    print('[site] 目录：site/public/catalog.json')
    print('[site] 打印版：site/print.md')
    print('[site] 高考默写范围：site/gaokao.md')
    print('[site] 下一步：npm run dev 预览，npm run build 构建')


if __name__ == '__main__':
    main()