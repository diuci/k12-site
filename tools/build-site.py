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
# 出处核对与台账：页底那句「这篇核对到什么程度」必须从这两份数据当场算，
# 写死在代码里的数字一定会过期——页脚那句「共 253 篇」就是这么烂掉的。
TSRC = ROOT / 'data' / 'text-sources.json'
LEDGER = ROOT / 'data' / 'ledger.json'
SRCHECK = ROOT / 'data' / 'source-check.json'

SITE_POEMS = SITE / 'poems'
# 册次列表页：site/vol/<学段>/<册次>.md
# 与单篇页面分开目录，侧栏分类项指向这里。
SITE_VOL = SITE / 'vol'

# 繁体版：正文与注释译文全部来自内容仓的派生产物 data/traditional.json。
# 站点不自己转繁简 —— 转繁简的引擎只有一份，在内容仓 tools/build-traditional.py，
# 那里有来源页证据、有裁定表、有闸门。在这里再写一台，就是允许两台给出不同答案。
TRAD = ROOT / 'data' / 'traditional.json'
SITE_TRAD = SITE / 'trad'
_TRAD_ROWS = None
_BT = None
_UI_CACHE = {}


def trad_rows():
    global _TRAD_ROWS
    if _TRAD_ROWS is None:
        if not TRAD.exists():
            die('缺少 %s：没有派生产物就不许生成繁体版' % TRAD)
        _TRAD_ROWS = {r['id']: r for r in json.loads(TRAD.read_text(encoding='utf-8')).get('rows', [])}
    return _TRAD_ROWS


def trad_engine():
    """把内容仓那台派生机载进来（文件名带连字符，只能按路径加载）。"""
    global _BT
    if _BT is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location('btrad', ROOT / 'tools' / 'build-traditional.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _BT = (m, m.read_table(m.STC), m.read_table(m.STP),
               m.read_table(m.TSC), m.read_table(m.TSP), m.load_rules())
    return _BT


def ui_trad(s):
    """界面词的繁体形：同一套表、同一张裁定表、同一道闸门。
    表给了多个候选而裁定表没说用哪个 —— 直接失败，界面词也不许静默择一。"""
    if s in _UI_CACHE:
        return _UI_CACHE[s]
    m, s2c, s2p, t2c, t2p, rules = trad_engine()
    tt, mm = m.convert(s, s2p, s2c, set(s))
    for x in mm:
        x['field'] = 'ui'
        x['line'] = 0
    m.apply_rules(mm, rules)
    m.vet_table_choices([tt], [s], mm, t2p, t2c, 'ui')
    if any(x.get('pick') for x in mm):
        tt = m.apply_picks(tt, mm)
    for x in mm:
        if x['decision'] == 'pending':
            die('界面词「%s」里的「%s」表给了 %s 几个写法，裁定表没说用哪个 —— '
                '界面词也不许静默择一' % (s, x['simp'], '/'.join(x['cands'])))
    for ch in tt:
        if ch in s2c and ch not in s2c[ch] and ch not in set(s):
            die('界面词「%s」的繁体形里留下简体字「%s」：表要求换成 %s' % (s, ch, s2c[ch][0]))
    _UI_CACHE[s] = tt
    return tt


def die(msg):
    print('[site] ERROR: ' + msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- 拼音
# 站点给孩子用，加拼音能显著降低阅读门槛。这里用「汉字 → 拼音」的小表，
# 只覆盖篇目里出现的字；查不到的留空（不报错），可后续补全。
#数据来源：GB/T 16159-2012《汉字拼音方案》常用字表
BT = chr(96)
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


def body_html(text):
    """正文每一行自己包进 <p>，行与行之间不留空行。

    markdown-it 只在空行处结束一段原始 HTML。`<div class="poem-body">` 后面到第一个空行
    为止是原始 HTML——那些行直接挂在 div 上，吃 VitePress 默认的 16px；空行之后的每一联
    被当成普通段落包进 <p>，吃本站的 1.3rem。于是同一首诗「上两句小、后两句大」。
    整块自己包成 <p>、中间不留空行，整块就都是同一种结构、同一种字号。
    以 > 开头的行是考证说明（出处 / 收录判断），剥掉 > 包成 .fq，样式统一、明显不是正文。
    """
    out = []
    for raw in text.split(chr(10)):
        line = raw.strip()
        if not line:
            continue
        if line.startswith('>'):
            out.append('<p class="fq">%s</p>' % line.lstrip('>').strip())
        else:
            out.append('<p>%s</p>' % line)
    if not out:
        die('正文包成 <p> 之后是空的——这一页会生成出一个没有内容的正文块')
    return chr(10).join(out)


# ---------------------------------------------------------------- 解析
def with_pinyin_pair(simp, trad, where=''):
    """繁体行的注音按位置取自简体行。
    派生是逐字对应的（繁简表里每一条左右长度都相同，无一例外），
    所以繁体第 k 个字就是简体第 k 个字的那个字，拼音照它给。
    按行配：md 里正文行之间夹着空行，派生出来的行没有空行，整段比长度必然对不上。"""
    if not PINYIN:
        return trad
    NL = chr(10)          # 换行符写死在这里，免得补丁把转义弄反
    sl = [x for x in simp.split(NL) if x.strip()]
    out, si = [], 0
    for line in trad.split(NL):
        if not line.strip():
            out.append(line)
            continue
        if si >= len(sl):
            die('繁体注音配不上：%s 繁体比简体多出内容行' % where)
        s = sl[si]
        si += 1
        if len(s) != len(line):
            die('繁体注音配不上：%s 简体行「%s」%d 字，繁体行「%s」%d 字'
                % (where, s, len(s), line, len(line)))
        out.append(''.join('<ruby>%s<rp>（</rp><rt>%s</rt><rp>）</rp></ruby>' % (b, PINYIN[a])
                           if a in PINYIN else b for a, b in zip(s, line)))
    if si != len(sl):
        die('繁体注音配不上：%s 简体还有 %d 行没配上' % (where, len(sl) - si))
    return NL.join(out)


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
    '统编教材收了一部分（课标要求更多）': '教材只收了一部分',
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
    '统编教材收了一部分（课标要求更多）': '统编教材收了这篇的一部分，课标要求的比教材收的多——缺的那部分照课标补，不许拿教材目录当「不用背」。',
}


def ts_label_problems(statuses):
    """每一种教材收录状态都必须有标签和说明。
    配不上的那一篇，页面上什么都不显示——学生看到的是一片空白，比说错更难发现。"""
    out = []
    for st in statuses:
        if not st or st == '统编教材收录':
            continue
        if st not in TS_LABEL:
            out.append('状态「%s」没有标签（这一档在页面上等于不说）' % st)
        if st not in TS_NOTE:
            out.append('状态「%s」没有说明' % st)
    return out


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
        # 只在句末标点之后断，会把「惠子曰：『子非鱼，安知鱼之乐？』」整段一起标粗——
        # 「惠子曰」不是要背的内容，却被标成要背。引号开头也断一刀，说话人留在粗段外面。
        for part in re.split(r'(?<=[。！？；])(?!」|』)|(?<=[。！？；][」』])|(?=「)', s):
            # 【端正好】【滚绣毬】这类是曲牌名：是要背的内容之外的标签。
            # 连着正文一起算键，「【端正好】碧云天。」就对不上「碧云天，黄花地」，必背句会被漏标。
            k = re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', re.sub(r'【[^】]*】', '', part))
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


def render_page(fm, sections, title_line, catalog_entry, trow=None, simp_sections=None):
    """生成单篇站点页面。trow 给了就是繁体版：正文与注释译文来自派生产物，
    界面词过同一台派生机；sections 传繁体文本，simp_sections 传对应的简体文本（只为注音）。"""
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

    T = trow is not None
    lab = (trow.get('labels_trad') or {}) if T else {}

    def u(s):
        return ui_trad(s) if T else s

    def lg(k, d=None):
        v = lab.get(k)
        return v if v is not None else (d if d is not None else fm.get(k))

    theme_show = lab.get('theme') or theme
    tech_show = lab.get('technique') or tech
    ptitle = lg('title', title)

    L = []
    L.append('---')
    L.append('title: %s' % ptitle)
    L.append('description: %s · %s · %s' % (lg('author', author), lg('dynasty', dyn), ptitle))
    L.append('outline: [2, 3]')
    L.append('---')
    L.append('')

    # ---- 题头信息卡
    L.append('<div class="poem-head">')
    L.append('  <h1 class="poem-title">%s</h1>' % ptitle)
    L.append('  <div class="poem-meta">')
    L.append('    <span class="m-author">%s</span>' % lg('author', author))
    L.append('    <span class="m-dyn">%s</span>' % lg('dynasty', dyn))
    L.append('    <span class="m-form">%s</span>' % lg('form', form))
    L.append('    <span class="m-stage">%s</span>' % lg('stage', stage))
    L.append('    <span class="m-vol">%s</span>' % lg('volume', volume))
    L.append('  </div>')
    ts = fm.get('textbookStatus')
    # 标签区：背诵要求（若有）+ 教材收录状态 + 主题 + 手法，任一存在就渲染
    if recite or theme or tech or TS_LABEL.get(ts):
        L.append('  <div class="poem-tags">')
        if recite:
            L.append('    <span class="tag tag-recite">%s</span>'
                     % u(RECITE_LABEL.get(recite, recite)))
        for t in theme_show:
            L.append('    <span class="tag">%s</span>' % t)
        for t in tech_show:
            L.append('    <span class="tag tag-tech">%s</span>' % t)
        if TS_LABEL.get(ts):
            L.append('    <span class="tag tag-tb">%s</span>' % u(TS_LABEL[ts]))
        L.append('  </div>')
    L.append('</div>')
    L.append('')

    # ---- 繁简切换：每一篇都双向可达，切换不换内容，只换字形 ----
    other = catalog_entry.get('url') if T else catalog_entry.get('urlTrad')
    if other:
        L.append('<div class="script-switch">')
        L.append('  <a class="ss-link" href="%s">%s</a>'
                 % (other, u('繁體版') if not T else u('简体版')))
        L.append('  <span class="ss-note">%s</span>' % (u('同一份内容，另一种字形') if not T else '同一份內容，另一種字形'))
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
        if T:
            L.append(body_html(with_pinyin_pair((simp_sections or {}).get(main_key, ''), sections[main_key],
                                      '%s·正文' % title)))
        else:
            L.append(body_html(with_pinyin(sections[main_key])))
        L.append('</div>')
        L.append('')

    # ---- 全文：仓里收全了的篇目，把整篇也放出来，并标出其中要背的那几句
    full_txt = (sections.get('全文') or sections.get('必背全文') or '').strip()
    if full_txt and main_key and full_txt != sections.get(main_key, '').strip():
        recite_lines = [x.strip() for x in sections.get(main_key, '').split('\n') if x.strip()]
        L.append('<div class="poem-full">')
        L.append('  <h2 class="full-h">%s<span class="full-sub">%s</span></h2>'
                 % (u('全文'), u('加粗的是要背的部分')))
        L.append('  <div class="full-body">')
        L.append(body_html(highlight_recite(full_txt, recite_lines)))
        L.append('  </div>')
        L.append('</div>')
        L.append('')

    # ---- 教材收录状态说明
    if TS_NOTE.get(ts):
        covered = fm.get('textbookCoveredBy')
        note = u(TS_NOTE[ts])
        if covered:
            note += u('它在教材里的这些课：') + (u(covered) if T else covered) + u('。')
        L.append('<p class="tb-note">%s</p>' % note)
        L.append('')

    # ---- 高考默写范围：属不属于默写范围、属哪一组、哪一年开始考
    cross = STAGE_CROSS.get(sid)
    gk_group = catalog_entry.get('gaokaoGroup') or (cross or {}).get('group')
    if gk_group:
        gk_no = catalog_entry.get('gaokaoNo') or (cross or {}).get('no')
        gk_since = catalog_entry.get('gaokaoSince') or 2023
        gk_name = {g: n for g, n, _ in GK_GROUPS}.get(gk_group, gk_group)
        L.append('<p class="gk-note">%s</p>'
                 % (u('高考默写范围 · {g} · 第 {n} 篇 · {y} 年起考')
                    .format(g=u(gk_name), n=gk_no, y=gk_since)))
        L.append('')
    if cross:
        L.append('<p class="tb-note">%s</p>'
                 % (u(cross['note'])
                    + u(' 仓里只有一份，挂在教材实际所在的那一册，不重复挂到高中。')))
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
        L.append('## %s' % u(sec))
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
        L.append('## %s' % u(sec))
        L.append('')
        if sec == '异文':
            # 默认口径要写在页面上，不能只在文档里：237 条异文没有「取舍」，不是漏写，
            # 是默认就不改正文。（这个默认有护栏核对：内容仓 check-variant-defaults.py。）
            L.append('> %s' % u('默认：下面只登记别的版本怎么写，**仓内正文不改**，用字以统编教材与来源页主文为准。'))
            L.append('> %s' % u('写了「取舍」的条目，才是这一处真做过选择。'))
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
        L.append('## %s' % u(sec))
        L.append('')
        L.append(body)
        L.append('</div>')
        L.append('')

    # ---- 玩法数据
    game = sections.get('玩法数据', '')
    if game and not T:        # 玩法数据是给游戏用的机器数据，不在页面上摆两份
        L.append('<div class="poem-game">')
        L.append('## 玩法数据')
        L.append('')
        L.append(game)
        L.append('</div>')

    # ---- 出处核对：没对上的句子逐句写明页里怎么写的、差在哪（内容仓生成，站点只搬）
    sc = _sc_map().get(sid)
    if sc and sc.get('items'):
        L.append('<div class="poem-sourcecheck">')
        L.append('## %s' % u('出处核对'))
        L.append('')
        L.append(u('正文 {l} 句里 {h} 句逐句对上了独立来源页。没对上的 {m} 句，逐句写明页里怎么写的、差在哪：')
                 .format(l=sc['lines'], h=sc['hit'], m=len(sc['items'])))
        if T:
            L.append('')
            L.append('> %s' % u('下面的引文保持简体：这一节比的是简体正文与来源页，不是繁体排版。'))
        L.append('')
        for it in sc['items']:
            L.append('- %s%s%s —— **%s** %s' % (BT, it['line'], BT, it['grade'], it['note']))
        L.append('')
        L.append(u('来源页：{p}').format(p=sc['page']))
        L.append('')
        L.append(u('（A 只差写法：同一个字的另一种写法；B 页里写作别的样子：版本差异；C 页里没找到。）'))
        L.append('</div>')
        L.append('')

    # ---- 页底核对状态：这一句是「我们核对到什么程度」，不是装饰
    L.append('<div class="poem-check">')
    L.append('  <span class="pc-text">%s</span>' % check_note(sid, trad=T))
    L.append('  <a class="pc-link" href="%s">%s</a>'
             % ('/trad/' if T else '/accuracy', u('我们是怎么核对的、可能错在哪')))
    L.append('</div>')

    L.append('<div class="poem-foot">')
    L.append('  <a class="back" href="%s">%s</a>' % ('/trad/' if T else '/', u('← 返回总览')))
    L.append('  <span class="src">%s%s ｜ %s%s</span>'
             % (u('来源：'), u(fm.get('source', '')), u('许可：'), u(fm.get('license', ''))))
    L.append('</div>')

    return '\n'.join(L) + '\n'


# ---------------------------------------------------------------- 出处核对状态
_SRC = None
_LED = None


def _src_map():
    global _SRC
    if _SRC is None:
        _SRC = {}
        if TSRC.exists():
            for r in json.loads(TSRC.read_text(encoding='utf-8')).get('results', []):
                _SRC[r['id']] = r
    return _SRC


def _led_map():
    global _LED
    if _LED is None:
        _LED = {}
        if LEDGER.exists():
            for r in json.loads(LEDGER.read_text(encoding='utf-8')).get('rows', []):
                _LED[r['id']] = r
    return _LED


def check_status(pid):
    """这篇的出处核对落在哪一档：full / partial / none / nopage / norec。

    nopage 与 norec 是两回事：前者是内容仓搜过、这本集子在维基文库确实没有正文页，
    后者是我们压根没核。混成一档，页底就会把「没核」写成「核过没有」。"""
    r = _src_map().get(pid)
    if not r:
        return 'norec', 0, 0
    if r.get('no_page'):
        return 'nopage', 0, int(r.get('lines') or 0)
    if not r.get('page'):
        return 'norec', 0, 0
    lines, hit = int(r.get('lines') or 0), int(r.get('hit') or 0)
    if lines and hit == lines:
        return 'full', hit, lines
    if hit:
        return 'partial', hit, lines
    return 'none', hit, lines


def check_note(pid, trad=False):
    """页底那一句：本篇核对到什么程度。诚实优先——没核到就说没核到。"""
    u = ui_trad if trad else (lambda s: s)
    kind, hit, lines = check_status(pid)
    if kind == 'full':
        head = u('正文 {l} 句逐句对上了独立来源页').format(l=lines)
    elif kind == 'partial':
        head = u('正文 {l} 句里 {h} 句对上了独立来源页，差的那几句本页「出处核对」一节逐句写了原因').format(l=lines, h=hit)
    elif kind == 'none':
        head = u('正文没能在独立来源页里对上，本页「出处核对」一节逐句写了原因')
    elif kind == 'nopage':
        head = u('仓内核过：这本集子在维基文库没有正文页，本页「出处核对」一节写明了搜过哪些句子')
    else:
        head = u('这篇没有出处核对记录')
    row = _led_map().get(pid) or {}
    ve, vs = int(row.get('variantEntries') or 0), int(row.get('variantWithSource') or 0)
    if ve:
        head += u('；异文 {v} 处，其中 {s} 处写了出处').format(v=ve, s=vs)
    return head + u('。背诵与用字以教材和老师的要求为准。')


def _sc_map():
    """内容仓的逐句核对明细：id -> 没对上的句子清单。站点只搬这份，不自己判。"""
    if not SRCHECK.exists():
        return {}
    d = json.loads(SRCHECK.read_text(encoding='utf-8'))
    return {r['id']: r for r in d.get('rows', [])}


def src_generated():
    """这一轮核对是哪天跑的、覆盖到哪一步——从数据文件本身读，不写死。"""
    try:
        d = json.loads(TSRC.read_text(encoding='utf-8'))
    except Exception:
        return '（读不到核对记录）'
    return str(d.get('generated') or '（没有日期）')


def source_check_body():
    """内容仓 tools/build-source-check.py 生成的逐句明细，原样搬进站点。
       站点不重写这份内容，也不自己数——只搬运，搬不到就明说搬不到。"""
    f = ROOT / 'docs' / 'source-check.md'
    if not f.exists():
        return '（这一份明细没生成：内容仓缺 docs/source-check.md）'
    out = []
    for line in f.read_text(encoding='utf-8').split('\n'):
        if line.startswith('# 出处核对') or line.startswith('> 这一页由') or line.startswith('> 数据来自'):
            continue
        out.append(line)
    return '\n'.join(out).strip()


# 档名与台账共用一份：台账加一档（比如「核过没有正文页」），这边必须跟着多一档。
# 写死四档的写法，会在台账加档后少算一档——然后这道检查一直「通过」。
CHECK_BUCKETS = [('full', '逐句全对上'), ('partial', '部分对上'), ('none', '一句都对不上'),
                 ('nopage', '核过没有正文页'), ('norec', '没有核对记录')]


def check_counts():
    """全站各档计数——必须和台账逐档一致，不一致就直接报错，不许静默显示旧数字。"""
    c = {k: 0 for k, _ in CHECK_BUCKETS}
    for pid in _src_map():
        kind = check_status(pid)[0]
        if kind not in c:
            die('站点算出了台账里没有的核对档「%s」：%s' % (kind, pid))
        c[kind] += 1
    g = {}
    if LEDGER.exists():
        g = json.loads(LEDGER.read_text(encoding='utf-8')).get('summary', {}).get('gapCounts', {})
    # 台账里有什么档就比什么档：台账加一档这边不认、或者台账少一档（旧的），都必须对不上。
    led = {k.split('·', 1)[1]: g[k] for k in g if k.startswith('出处核对·')}
    if led:
        mine = {name: c[k] for k, name in CHECK_BUCKETS}
        if mine != led:
            die('站点算出的出处核对 %s 与台账 %s 对不上——台账没重建，或者台账加了一档这边不认？'
                % (sorted(mine.items()), sorted(led.items())))
    return c, g


# ---------------------------------------------------------------- 主流程
def esc(s):
    return (str(s if s is not None else '')
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def render_volume_page(stage, volume, entries, trad=False):
    """生成册次列表页：列出该册全部篇目。

    侧栏的「小学 / 一年级上册」这类分类必须先落到列表页，
    再由用户挑具体篇目；否则点进去直接就是一首诗。
    """
    T = trad
    rows = trad_rows() if T else {}

    def u(s):
        return ui_trad(s) if T else s

    def lab(eid, k, d):
        if not T:
            return d
        return ((rows.get(eid) or {}).get('labels_trad') or {}).get(k) or d

    L = ['---',
         'title: %s · %s' % (lab(entries[0]['id'], 'volume', volume),
                             lab(entries[0]['id'], 'stage', stage)),
         'description: %s' % u('{a}{b} 全部 {n} 篇古诗文，含原文、注释、译文与赏析。').format(
             a=lab(entries[0]['id'], 'stage', stage), b=lab(entries[0]['id'], 'volume', volume), n=len(entries)),
         'sidebar: false',
         'aside: false',
         '---',
         '']

    L.append('<div class="hero vol-hero">')
    L.append('  <div class="wrap-alt">')
    L.append('    <nav class="crumbs" aria-label="%s">' % u('面包屑'))
    L.append('      <a href="%s">%s</a>' % ('/trad/' if T else '/', u('总览')))
    L.append('      <span class="sep">/</span>')
    L.append('      <span class="cur">%s</span>' % lab(entries[0]['id'], 'volume', volume))
    L.append('    </nav>')
    L.append('    <span class="eyebrow"><span class="dot"></span>%s · %s %d %s</span>'
             % (lab(entries[0]['id'], 'stage', stage), u('全部'), len(entries), u('篇')))
    L.append('    <h1>%s</h1>' % lab(entries[0]['id'], 'volume', volume))
    L.append('    <p class="hero-sub">%s</p>'
             % u('这一册的{n} 篇都在下面，按教材顺序排。').format(n=len(entries)))
    L.append('    <p class="hero-sub"><a class="ss-link" href="%s">%s</a> '
             '<span class="ss-note">%s</span></p>'
             % ('/vol/' + stage + '/' + volume if T else '/trad/vol/' + stage + '/' + volume,
                u('简体版') if T else u('繁體版'),
                u('同一份內容，另一種字形') if T else u('同一份内容，另一种字形')))
    L.append('  </div>')
    L.append('</div>')
    L.append('')
    L.append('<div class="wrap-alt">')
    L.append('  <div class="grid vol-grid" id="vol-grid">')
    for e in entries:
        badge = (RECITE_LABEL.get(e['recite'], '')
                 if e.get('recite') and e['recite'] != 'none' else '')
        badge_html = ('<span class="badge badge-recite">%s</span>' % u(badge)) if badge else ''
        L.append('    <a class="card" href="%s">' % (e.get('urlTrad') if T else e['url']))
        L.append('      <div class="card-t">%s%s</div>'
                 % (lab(e['id'], 'title', e['title']), badge_html))
        L.append('      <div class="card-a">%s · %s</div>'
                 % (lab(e['id'], 'author', e.get('author') or ''),
                    lab(e['id'], 'dynasty', e.get('dynasty') or '')))
        card_line = e.get('lines')
        if T:
            tl = (rows.get(e['id']) or {}).get('lines_trad') or []
            card_line = re.sub(r'<[^>]+>', '', tl[0])[:40] if tl else ''
        if card_line:
            L.append('      <div class="card-l">%s</div>' % card_line)
        L.append('      <div class="card-g">%s</div>' % lab(e['id'], 'volume', volume))
        L.append('    </a>')
    L.append('  </div>')
    L.append('  <p class="count" style="margin-top:24px">')
    L.append('    %s %d %s · <a href="%s">%s</a>'
             % (u('共'), len(entries), u('篇'), '/trad/' if T else '/', u('返回总览')))
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


# ---------------------------------------------------------------- 准确性与免责一页
def render_accuracy_page():
    """整页说明：核对到什么程度、可能错在哪、错了怎么办。
    每一个数字都是从内容仓当场读的——这份页面不许有写死的统计。"""
    c, g = check_counts()
    total = sum(c.values())
    ve = g.get('异文条目总数', 0)
    vs = g.get('异文条目带出处', 0)
    vc = g.get('异文条目带取舍', 0)
    vm = g.get('异文条目缺出处', 0)
    L = []
    L.append('---')
    L.append('title: 内容准确性与免责')
    L.append('description: 学古诗的内容核对到什么程度、可能错在哪、发现错了怎么办')
    L.append('---')
    L.append('')
    L.append('# 内容准确性与免责')
    L.append('')
    L.append('> 这一页存在的理由：我们没法保证百分之百没错。'
             '与其等别人发现，不如自己先把核对到的程度、没核对到的地方、和出错后怎么办写清楚。')
    L.append('')
    L.append('## 一句话结论')
    L.append('')
    L.append('站内共 **%d** 篇古诗文。**%d 篇的正文逐句对上了独立来源页**，'
             '**%d 篇大部分对上**（差的那几句页内写了原因），**%d 篇没能在独立来源里对上**（页内也写了原因）。'
             % (total, c['full'], c['partial'], c['none']))
    L.append('')
    L.append('注释、译文、赏析是我们自己写的，不是教材里的，也不是教研结论。')
    L.append('')
    L.append('## 我们是怎么核对的')
    L.append('')
    L.append('| 要定什么 | 认哪个来源 | 为什么是它 |')
    L.append('| --- | --- | --- |')
    L.append('| 收哪些篇 | 教育部《义务教育语文课程标准》《普通高中语文课程标准》 | 考什么我们收什么 |')
    L.append('| 哪一册第几课、教材用哪个字 | 人民教育出版社公开页面 | 教材是考试依据；我们不是人教社，只是核对 |')
    L.append('| 古籍原文与异文 | 维基文库（公有领域）+ 中国哲学书电子化计划 | 有可查的页面与结构化校勘夹注 |')
    L.append('| 原文字句初稿 | chinese-poetry（MIT） | 起点，不是终点：每一句都要另找来源核 |')
    L.append('')
    L.append('具体做法：把仓里每一篇按句剥掉标点，拿去来源页里逐句找；'
             '来源页繁体先过一遍繁简转换表再比；来源页把「一作某」夹注剥出来单独登记成异文。'
             '**搜到一句话不等于找到了来源**——来源页必须装得下这篇正文才算。')
    L.append('')
    L.append('## 当前核对到的程度')
    L.append('')
    L.append('| 项目 | 数字 |')
    L.append('| --- | --- |')
    L.append('| 收录篇数 | %d |' % total)
    L.append('| 正文逐句全对上来源页 | %d |' % c['full'])
    L.append('| 部分对上 | %d |' % c['partial'])
    L.append('| 一句都对不上 | %d |' % c['none'])
    L.append('| 搜过、集子没有正文页 | %d |' % c['nopage'])
    L.append('| 没有核对记录 | %d |' % c['norec'])
    L.append('| 异文条目 | %d（写了出处 %d / 写了取舍 %d / 没核到出处 %d） |' % (ve, vs, vc, vm))
    L.append('| 课标要求但仓内缺失 | %d |' % g.get('课标要求但仓内缺失', 0))
    L.append('| 来源不明 | %d |' % g.get('来源不明', 0))
    L.append('')
    L.append('**这一轮数字覆盖的是哪一部分**：上表来自内容仓的核对记录，最后一次全仓重跑是 **%s**。'
             '核对单位在 2026-10-09 从「每篇的必背名句」扩到了「每篇全文的每一句」（以前长诗只核那几句，'
             '离骚核的是 4 句、答司马谏议书核的是 6 句，全文另有 26 联、4 段从没进过这道核对）。'
             '扩围之后的全仓重跑已经跑完：每一篇都有核对记录，没有一篇是「跑挂了」或「没跑」。'
             '核对时还认「同一个字的另一种写法」（页里写作「未甞」我们写作「未尝」）——'
             '每一对都过了「两边读音必须相同」那道自检，读音不同的（彊/强）一律不认，留在没对上里。'
             '没对上的句子逐句列在本页下面。' % src_generated())
    L.append('')
    L.append('「没核到出处」的 %d 条异文，页内一律写明「出处：仓内没核到」。'
             '它们出自我们仓里没有的书（《唐文粹》、《古文观止》评点本、各家别集别本）。'
             '**把「没核到」写成「有出处」就是编造，我们不做这件事。**' % vm)
    L.append('')
    L.append('')
    L.append('## 没全对上的那几句，逐句写明差在哪')
    L.append('')
    L.append('三档口径，不含糊：**A 只差写法**（同一个字的另一种写法）、'
             '**B 页里写作别的样子**（版本差异）、**C 页里没找到**。')
    L.append('')
    L.append(source_check_body())
    L.append('')
    L.append('## 可能错在哪四类')
    L.append('')
    L.append('1. **用字**。我们按统编教材定用字，但可能抄错、漏校；各地教材本身也有异文。'
             '已核准但缺第二条独立来源的改动，只登记、不改正文——所以某一篇的正文可能仍是你老师不认的那个字。')
    L.append('2. **读音**。古诗文里不少字有异读、通假、破音。我们给的读音是教学常用的一种读法，'
             '**不是唯一正确答案**，考试以老师给的为准。')
    L.append('3. **注释、译文、赏析**。那是我们写给孩子的白话解释，是我们的理解，不是学术定论也不是教研结论。')
    L.append('4. **篇目归属与背诵范围**。课标与教材会修订，我们的标注可能滞后；'
             '教材是版权作品，我们只登记「哪一册第几课」这类事实，不复制教材的注释、译文、赏析、活动设计。')
    L.append('')
    L.append('## 不担保（AS IS）')
    L.append('')
    L.append('本站按「原样提供」发布。我们**不担保**内容没有错误、没有遗漏、适合你的教材或你的考试。'
             '**备考请以教材、老师和学校的要求为准，不要把本站当成唯一依据。**'
             '如果你按本站的内容去考试而出了错，这个责任我们承担不了，也请你别把本站当官方材料。')
    L.append('')
    L.append('## 发现错了怎么办')
    L.append('')
    L.append('写信到 **hi@diuci.com**，写清是哪一篇、哪一句、你认为应该是什么、依据是什么。'
             '我们核实后会改，并且把这次更正写进公开提交记录——'
             '任何人都能看到我们改了什么、为什么改。已登记的已知问题列在内容仓 `data/known-defects.json`。')
    L.append('')
    L.append('## 版权口径')
    L.append('')
    L.append('原文只收**作者卒年 + 50 年已经届满**的（我国《著作权法》对自然人作品的保护期）。'
             '这条不是文档里的说法，是脚本在跑的规则：不满足就构建失败。'
             '注释、译文、赏析是我们原创，用 CC BY 4.0，转载必须署名。详见[版权与免责](/legal)。')
    L.append('')
    L.append('---')
    L.append('')
    L.append('这一页由 `tools/build-site.py` 从内容仓的台账与核对记录生成，数字不会写死过期。'
             '内容仓的完整审计见 `docs/audit.md`。')
    L.append('')
    return '\n'.join(L)


def render_trad_index(catalog):
    """繁体版首页：说清这份繁体是从哪来、依据在哪能查、哪些东西还没有繁体版。"""
    d = json.loads(TRAD.read_text(encoding='utf-8'))
    c = d.get('counts') or {}
    ca = d.get('counts_apparatus') or {}
    rev = d.get('reversal') or []
    L = ['---',
         'title: 繁體版',
         'description: 學古詩的繁體版是怎麼來的、依據在哪裡可以查',
         'sidebar: false',
         'aside: false',
         '---',
         '']
    L.append('<div class="hero vol-hero">')
    L.append('  <div class="wrap-alt">')
    L.append('    <span class="eyebrow"><span class="dot"></span>%s</span>' % ui_trad('学古诗 · 繁体版'))
    L.append('    <h1>%s</h1>' % ui_trad('繁体版'))
    L.append('    <p class="hero-sub">%s</p>'
             % ui_trad('同一份内容，另一种字形。正文、注释、译文、赏析都有繁体，逐篇可切换。'))
    L.append('    <p class="hero-sub"><a class="ss-link" href="/">%s</a></p>' % ui_trad('回到简体版总览'))
    L.append('  </div>')
    L.append('</div>')
    L.append('')
    L.append('<div class="wrap-alt">')
    L.append('## %s' % ui_trad('这份繁体是怎么来的'))
    L.append('')
    L.append(ui_trad('简体正文是唯一事实源，繁体是派生物。每一处「一简对多繁」都要落到某一档，优先级不可颠倒：'))
    L.append('')
    L.append('1. %s' % ui_trad('来源页亲眼写作那个字'))
    L.append('2. %s' % ui_trad('裁定表（每一条都写了理由）'))
    L.append('3. %s' % ui_trad('繁简表的首选项'))
    L.append('')
    L.append(ui_trad('都没依据的不许静默择一。当前待定 {p} 处。').format(p=c.get('pending', -1)))
    L.append('')
    L.append('## %s' % ui_trad('当前数字'))
    L.append('')
    L.append('| %s | %s |' % (ui_trad('项目'), ui_trad('数字')))
    L.append('| --- | --- |')
    L.append('| %s | %d |' % (ui_trad('繁体篇页'), len(catalog)))
    L.append('| %s | %d |' % (ui_trad('正文由来源页定写法'), c.get('page', 0)))
    L.append('| %s | %d |' % (ui_trad('正文照表'), c.get('table', 0)))
    L.append('| %s | %d |' % (ui_trad('正文照裁定表'), c.get('rule', 0)))
    L.append('| %s | %d |' % (ui_trad('正文本来就写作那个字'), c.get('identity', 0)))
    L.append('| %s | %d |' % (ui_trad('页写作另一个字（异文，照我们的用字）'), c.get('variant', 0)))
    L.append('| %s | %d |' % (ui_trad('待定'), c.get('pending', -1)))
    L.append('| %s | %d |' % (ui_trad('注释译文等各节待定'), ca.get('pending', -1)))
    L.append('| %s | %d |' % (ui_trad('转回简体与原字不一致处（每一处都标了依据）'), len(rev)))
    L.append('')
    L.append(ui_trad('每一处的依据列在内容仓 docs/traditional.md，可以逐条查。'))
    L.append('')
    L.append('## %s' % ui_trad('哪些东西还没有繁体版'))
    L.append('')
    L.append(ui_trad('篇页与册次列表页有繁体版。高考默写范围、打印版、内容准确性、家长指南、数据来源与版权、版权与免责这几页目前只有简体版——它们是给我们核对用的工具页，不是给学生读的古文。'))
    L.append('')
    L.append(ui_trad('繁体版不额外担保：核对到什么程度，看简体版的「内容准确性与免责」。'))
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
    ts_problems = ts_label_problems([x.get('textbookStatus') for x in gk_src])
    if not gk_map:
        die('data/poems.json 里没有篇目，高考默写页会是空的')
    n_pinyin = load_pinyin()

    # 清空旧的站点篇目（保留 .vitepress 与手写页面）
    if ts_problems:
        for x in ts_problems[:8]:
            print('  !! ' + x)
        die('%d 种教材收录状态在站点这边没有标签/说明——内容仓加了一档，站点没跟上' % len(ts_problems))
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
            # 繁体版与简体版同路径同文件名，只是挂在 /trad 下面：
            # 切换就是换前缀，不另造一套地址。
            'urlTrad': '/trad/poems/' + '/'.join(
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

    # ---- 繁体版：同一棵树，另一种字形 ----
    rows = trad_rows()
    _no_trad = [e['id'] for e in catalog if e['id'] not in rows]
    if _no_trad:
        die('繁体派生产物里没有这几篇：%s —— 先跑内容仓 tools/build-traditional.py'
            % '、'.join(_no_trad[:8]))
    if SITE_TRAD.exists():
        shutil.rmtree(SITE_TRAD)
    trad_pages = 0
    for md in sorted(POEMS.rglob('*.md')):
        if md.name == '索引.md':
            continue
        fm, sections, title_line = parse_poem(md)
        rel = md.relative_to(POEMS)
        parts = list(rel.parts[:-1]) + [md.stem + '.md']
        out = SITE_TRAD.joinpath('poems', *parts)
        out.parent.mkdir(parents=True, exist_ok=True)
        entry = next(e for e in catalog if e['id'] == fm.get('id'))
        trow = rows[fm.get('id')]
        tsecs = {k: '\n'.join(v) for k, v in (trow.get('sections_trad') or {}).items()}
        for k, v in sections.items():
            if k not in tsecs and k not in ('玩法数据', '出处核对'):
                die('%s：简体页有「%s」这一节，繁体派生里却没有' % (fm.get('title'), k))
        out.write_text(render_page(fm, tsecs, title_line, entry,
                                   trow=trow, simp_sections=sections),
                       encoding='utf-8')
        trad_pages += 1

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
            out2 = SITE_TRAD / 'vol' / stage / (vol + '.md')
            out2.parent.mkdir(parents=True, exist_ok=True)
            out2.write_text(render_volume_page(stage, vol, items, trad=True), encoding='utf-8')
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

    # 页底那句核对状态要有数据可读；内容仓没跑核对与台账就直接失败，不许显示空话
    if not TSRC.exists():
        die('缺少 %s：先跑 python tools/check-text-sources.py' % TSRC)
    if not LEDGER.exists():
        die('缺少 %s：先跑 python tools/build-ledger.py' % LEDGER)
    if not SRCHECK.exists():
        die('缺少 %s：先跑 python tools/build-source-check.py' % SRCHECK)
    # 页底写「差的那几句写了原因」，明细就必须真有那几句；对不上就当场失败，
    # 不许让读者读到一句没有证据支撑的话。
    _sc = _sc_map()
    _cc, _ = check_counts()
    if len(_sc) != _cc['partial'] + _cc['none']:
        die('逐句明细覆盖 %d 篇，核对记录里却有 %d 篇没全对上：明细是旧的，重跑 build-source-check.py'
            % (len(_sc), _cc['partial'] + _cc['none']))
    _bad = [e['id'] for e in catalog
            if check_status(e['id'])[0] in ('partial', 'none') and not (_sc.get(e['id']) or {}).get('items')]
    if _bad:
        die('这几篇页底说「差的那几句写了原因」，明细却一条都没有：%s' % '、'.join(_bad[:8]))

    print('[site] 生成 %d 个篇目页面%s'
          % (len(catalog),
             '（拼音表 %d 字）' % n_pinyin if n_pinyin else '（无拼音表）'))
    (SITE_TRAD / 'index.md').write_text(render_trad_index(catalog), encoding='utf-8')
    print('[site] 繁体版：%d 个篇目页面、%d 个册次列表页、1 个说明页：site/trad/'
          % (trad_pages, vol_pages))
    print('[site] 册次列表页：%d 个' % vol_pages)
    print('[site] 目录：site/public/catalog.json')
    print('[site] 打印版：site/print.md')
    print('[site] 高考默写范围：site/gaokao.md')

    # ---- 准确性与免责一页（数字当场读，不写死）
    (SITE / 'accuracy.md').write_text(render_accuracy_page(), encoding='utf-8')
    cc, _ = check_counts()
    print('[site] 准确性与免责：site/accuracy.md（全对上 %d / 部分 %d / 都对不上 %d / 没有正文页 %d / 无记录 %d）'
          % (cc['full'], cc['partial'], cc['none'], cc['nopage'], cc['norec']))
    print('[site] 下一步：npm run dev 预览，npm run build 构建')


def selftest():
    """加粗护栏的坏例子：不试这些，护栏就是空过的。"""
    # 1) 说话人不许被标成要背的内容
    line = '惠子曰：「子非鱼，安知鱼之乐？」庄子曰：「子非我，安知我不知鱼之乐？」'
    out = highlight_recite(line, ['子非鱼，安知鱼之乐？'])
    assert '<b class="rh">「子非鱼，安知鱼之乐？」</b>' in out, '坏例1：必背句没被标出来'
    assert '<b class="rh">惠子曰' not in out, '坏例1：说话人「惠子曰」被标成了要背的内容'
    # 2) 整行就是必背句时，不许把行拆开漏标
    out2 = highlight_recite('舍南舍北皆春水，但见群鸥日日来。', ['舍南舍北皆春水，但见群鸥日日来。'])
    assert out2.count('<b class="rh">') == 1 and '舍南舍北皆春水' in out2.split('<b class="rh">')[1], '坏例2：整行必背句被拆坏'
    # 3) 不是必背句的段落不许被标粗
    out3 = highlight_recite('庄子与惠子游于濠梁之上。', ['子非鱼，安知鱼之乐？'])
    assert '<b' not in out3, '坏例3：不是必背句的被标粗了'
    # 4) 引号开头的必背句，粗段必须从引号内侧开始，不能把前一句的收尾括号卷进来
    out4 = highlight_recite('庄子曰：「鯈鱼出游从容，是鱼乐也。」惠子曰：「子非鱼，安知鱼之乐？」',
                          ['子非鱼，安知鱼之乐？'])
    assert '」<b class="rh">' not in out4, '坏例4：前一句的收尾引号被卷进粗段'
    # 5) 曲牌名不许把必背句挤成对不上：标签是内容之外的东西
    out5 = highlight_recite('【端正好】碧云天。黄花地。西风紧北雁南飞。', ['碧云天，黄花地，西风紧，北雁南飞。'])
    assert '<b class="rh">【端正好】碧云天。</b>' in out5, '坏例5：曲牌名连着正文，把必背句挤成了对不上'
    out6 = highlight_recite('【滚绣毬】此恨谁知。', ['碧云天，黄花地。'])
    assert '<b' not in out6, '坏例5：不是必背句的被标粗了'
    # 6) 出处核对各档必须与台账逐档对上。台账加一档而这边不认，检查就会少算一档还一直「通过」。
    global _SRC, _LED, LEDGER
    saved = (_SRC, _LED, LEDGER)
    try:
        import tempfile
        _SRC = {'a': {'id': 'a', 'page': '甲', 'lines': 2, 'hit': 2},
                'b': {'id': 'b', 'page': None, 'no_page': True, 'lines': 2, 'hit': 0},
                'c': {'id': 'c', 'page': '丙', 'lines': 3, 'hit': 1}}
        _LED = {}
        tmp = Path(tempfile.mkdtemp()) / 'ledger.json'
        tmp.write_text(json.dumps({'summary': {'gapCounts': {
            '出处核对·逐句全对上': 1, '出处核对·部分对上': 1, '出处核对·一句都对不上': 0,
            '出处核对·核过没有正文页': 1, '出处核对·没有核对记录': 0}}}), encoding='utf-8')
        LEDGER = tmp
        c6, _ = check_counts()
        assert c6['nopage'] == 1 and c6['full'] == 1 and c6['partial'] == 1, '坏例6：搜过没有正文页没单独计'
        # 台账把那一档并进「没有核对记录」：站点算 1/0、台账算 0/1，必须当场失败
        tmp.write_text(json.dumps({'summary': {'gapCounts': {
            '出处核对·逐句全对上': 1, '出处核对·部分对上': 1, '出处核对·一句都对不上': 0,
            '出处核对·没有核对记录': 1}}}), encoding='utf-8')
        try:
            check_counts()
            assert False, '坏例6b：台账与站点各档数字对不上却没报错'
        except SystemExit:
            pass
        # 台账加了一档这边不认的：不许静默少算
        tmp.write_text(json.dumps({'summary': {'gapCounts': {
            '出处核对·逐句全对上': 1, '出处核对·部分对上': 1, '出处核对·一句都对不上': 0,
            '出处核对·核过没有正文页': 1, '出处核对·没有核对记录': 0, '出处核对·新加的一档': 7}}}),
            encoding='utf-8')
        try:
            check_counts()
            assert False, '坏例6c：台账加了这边不认的一档却没报错'
        except SystemExit:
            pass
    finally:
        _SRC, _LED, LEDGER = saved
    # 坏例7：教材收录状态加了新档、站点这边没配标签——这一篇页面上就什么都不显示
    _p = ts_label_problems(['统编教材新加的一档'])
    assert len(_p) == 2 and '没有标签' in _p[0] and '没有说明' in _p[1], '坏例7：没配标签的状态没被抓到（%s）' % _p
    # 坏例7b：只有标签没有说明，也算没接上
    assert len(ts_label_problems(['统编教材收在别的课里'])) == 0, '坏例7b：配齐了的状态被误伤'
    # 坏例7c：「统编教材收录」是默认档，页面上不打标签，不许被当成漏配
    assert ts_label_problems(['统编教材收录', None, '']) == [], '坏例7c：默认档/空值被误伤'
    # 坏例7d：内容仓新加的「收了一部分」这一档，站点必须配齐（配不上就是空白）
    assert ts_label_problems(['统编教材收了一部分（课标要求更多）']) == [], '坏例7d：「收了一部分」这一档站点没配标签/说明'
    # 真产物：data/poems.json 里出现过的每一种状态都必须配齐
    if DATA.exists():
        _real = ts_label_problems({x.get('textbookStatus') for x in json.loads(DATA.read_text(encoding='utf-8')).get('poems', [])})
        assert not _real, '坏例7e：真产物里有状态没配标签/说明：%s' % _real
    else:
        print('     （data/poems.json 不在，真产物那一条没跑）')

    import ast, inspect
    # 坏例子的个数当场从这份源码数出来（数 assert 语句本身），
    # 先前数的是源码里 'assert ' 这个字符串出现几次——把计数那一行自己也数了进去，多报一个。
    _n = sum(1 for _x in ast.walk(ast.parse(inspect.getsource(selftest))) if isinstance(_x, ast.Assert))
    print('[ok] build-site --selftest 通（当场数到 %d 个坏例子，全部试到）' % _n)
    return 0


if __name__ == '__main__':
    import sys
    if '--selftest' in sys.argv:
        sys.exit(selftest())
    main()