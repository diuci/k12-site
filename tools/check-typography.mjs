#!/usr/bin/env node
/*
  字号一致性闸门（规范 §5）：一首诗里不许前两句小字、后两句大字。

  根因记在这里，免得下次再踩：markdown-it 的 html_block 规则是「空行结束 html_block」。
  <div> 是块级标签，所以 <div class="poem-body"> 后面第一段保持原样（裸 <ruby> → VitePress 默认 16px），
  而空行之后的段落以 <ruby> 开头 → 被包进 <p> → 1.3rem（20.8px）。同一首诗两种字号就是这么来的。

  修法：生成器把正文每一行都写成 <p>，块内不留空行。这条闸门盯的就是这两件事，
  外加「本站 CSS 必须显式给正文字号」——不显式给，VitePress 一改默认值我们就跟着变。

  存在但没接进链的检查等同于没有检查：本文件被 chain-site.ps1 与 CI 各调用一次。
  每个规则都配了坏例子（--selftest）；空过的检查比没有检查更危险。
*/
import fs from 'node:fs'
import path from 'node:path'

const MD_DIRS = ['site/poems', 'site/trad/poems']
const MD_EXTRA = ['site/print.md']
const CSS = 'site/.vitepress/theme/custom.css'
const BLOCKS = ['poem-body', 'full-body']

function fail(msg) { console.error('[check-typography] ' + msg); process.exit(1) }
function walkMd(dir) {
  if (!fs.existsSync(dir)) return []
  const out = []
  for (const e of fs.readdirSync(dir)) {
    const p = path.join(dir, e)
    if (fs.statSync(p).isDirectory()) out.push(...walkMd(p))
    else if (e.endsWith('.md')) out.push(p)
  }
  return out
}
function blocksIn(text) {
  const found = []
  for (const cls of BLOCKS) {
    let from = 0
    while (true) {
      const i = text.indexOf('<div class="' + cls + '">', from)
      if (i < 0) break
      const open = text.indexOf('{', i) // 不适用：HTML 用 </div> 收尾
      const end = text.indexOf('</div>', i)
      if (end < 0) break
      found.push({ cls, body: text.slice(i + '<div class="'.length + cls.length + '">'.length, end) })
      from = end + 6
    }
  }
  return found
}
const RULES = []
function rule(id, title, fn) { RULES.push({ id, title, fn }) }

rule('T1', '正文块里每一行必须是 <p>，块内不许有空行', (files) => {
  const problems = []
  for (const f of files.md) {
    for (const b of blocksIn(f.text)) {
      // 开标签后紧跟的那一个换行不算内容空行：切出来的头尾空串要丢掉
      const lines = b.body.replace(/^\r?\n/, '').replace(/\s+$/, '').split(/\r?\n/)  // 收尾那行只是 </div> 的缩进，不算内容空行
      lines.forEach((ln, n) => {
        const t = ln.trim()
        if (t === '') { problems.push(f.rel + ' 的 .' + b.cls + ' 里第 ' + (n + 1) + ' 行是空行：空行结束 html_block，后面那段会被包进 <p>，同一首诗就出现两种字号') ; return }
        if (!/^<p\b/.test(t)) problems.push(f.rel + ' 的 .' + b.cls + ' 里第 ' + (n + 1) + ' 行不是 <p>（是「' + t.slice(0, 24) + '」）：裸标签会被 markdown-it 区别对待，字号跟着变')
      })
    }
  }
  return problems
})

rule('T2', '正文块里不许写死字号（style=font-size、<font>）', (files) => {
  const problems = []
  for (const f of files.md) {
    for (const b of blocksIn(f.text)) {
      if (/font-size\s*:/i.test(b.body)) problems.push(f.rel + ' 的 .' + b.cls + ' 里出现了 font-size：字号归 CSS 管，写在正文里就是给这一句开小灶')
      if (/<font\b/i.test(b.body)) problems.push(f.rel + ' 的 .' + b.cls + ' 里有 <font>：老标签，绕开整套字号阶梯')
    }
  }
  return problems
})

rule('T3', 'CSS 必须显式给每一类正文块定字号', (files) => {
  const problems = []
  const css = files.css
  for (const cls of BLOCKS) {
    const re = new RegExp('\\.' + cls + '\\s+p\\s*\\{[^}]*font-size\\s*:', 'm')
    if (!re.test(css)) problems.push('custom.css 里没有 .' + cls + ' p { font-size: … }：不显式给字号，VitePress 一改默认值本站就跟着变')
  }
  return problems
})

/* ── 坏例子：每条规则都得被自己的坏例子绊倒一次 ── */
function selftest() {
  const goodMd = '<div class="poem-body">\n<p>鹅，鹅，鹅，</p>\n<p>曲项向天歌。</p>\n</div>\n'
  const goodCss = '.poem-body p{font-size:1.3rem}\n.full-body p{font-size:1.15rem}\n'
  const files = (md) => ({ md: [{ rel: 'a.md', text: md }], css: goodCss })
  const cases = []
  cases.push(['T1', '正文块里留了空行', files('<div class="poem-body">\n<p>第一句</p>\n\n<p>第二句</p>\n</div>\n')])
  cases.push(['T1', '正文块里有一行是裸 <ruby>', files('<div class="poem-body">\n<p>第一句</p>\n<ruby>鹅<rt>e</rt></ruby>\n</div>\n')])
  cases.push(['T1', '正文块里用了 <div> 分行', files('<div class="poem-body">\n<div>第一句</div>\n<p>第二句</p>\n</div>\n')])
  cases.push(['T2', '正文里写死 font-size', files('<div class="poem-body">\n<p style="font-size:22px">第一句</p>\n<p>第二句</p>\n</div>\n')])
  cases.push(['T2', '正文里用 <font>', files('<div class="poem-body">\n<p><font size="5">第一句</font></p>\n<p>第二句</p>\n</div>\n')])
  cases.push(['T3', 'CSS 少了 .poem-body p 的字号', { md: [{ rel: 'a.md', text: goodMd }], css: '.full-body p{font-size:1.15rem}\n' }])
  cases.push(['T3', 'CSS 只给了 .poem-body 没给 p', { md: [{ rel: 'a.md', text: goodMd }], css: '.poem-body{font-size:1.3rem}\n.full-body p{font-size:1.15rem}\n' }])
  let tried = 0, caught = 0
  for (const [id, why, f] of cases) {
    tried++
    const probs = RULES.find(r => r.id === id).fn(f)
    if (probs.length) caught++
    else console.error('  坏例子没抓住：' + id + ' ' + why)
  }
  const goodFiles = { md: [{ rel: 'a.md', text: goodMd }], css: goodCss }
  for (const r of RULES) {
    const probs = r.fn(goodFiles)
    if (probs.length) { tried++; console.error('  好例子被误报：' + r.id + ' ' + r.title + ' → ' + probs[0]) }
  }
  if (caught !== tried) { console.error('[check-typography] --selftest 失败：试了 ' + tried + ' 例，抓住 ' + caught + ' 例'); process.exit(1) }
  console.log('[ok] check-typography --selftest 通（当场数到 ' + tried + ' 个坏例子，全部试到）')
}

if (process.argv.includes('--selftest')) { selftest(); process.exit(0) }

const mdFiles = []
for (const d of MD_DIRS) for (const p of walkMd(path.resolve(d))) mdFiles.push({ rel: path.relative(process.cwd(), p).replace(/\\/g, '/'), text: fs.readFileSync(p, 'utf8') })
for (const p of MD_EXTRA) {
  const abs = path.resolve(p)
  if (!fs.existsSync(abs)) fail('找不到 ' + p + '：先生成站点再跑这条检查')
  mdFiles.push({ rel: p, text: fs.readFileSync(abs, 'utf8') })
}
if (!mdFiles.length) fail('一个 md 都没找到：先跑 python tools/build-site.py')
const cssPath = path.resolve(CSS)
if (!fs.existsSync(cssPath)) fail('找不到 ' + CSS)
const files = { md: mdFiles, css: fs.readFileSync(cssPath, 'utf8') }

let bad = 0, blocks = 0
for (const f of mdFiles) blocks += blocksIn(f.text).length
for (const r of RULES) {
  const probs = r.fn(files)
  if (!probs.length) { console.log('  ' + r.id + ' ' + r.title + '：过'); continue }
  bad += probs.length
  for (const p of probs.slice(0, 12)) console.error('  ' + r.id + ' ' + r.title + '：' + p)
  if (probs.length > 12) console.error('  ' + r.id + ' …还有 ' + (probs.length - 12) + ' 处')
}
console.log('（数到 ' + mdFiles.length + ' 个 md、' + blocks + ' 个正文块）')
if (bad) { console.error('[check-typography] 失败：' + bad + ' 处不合规'); process.exit(1) }
console.log('[ok] check-typography 通（' + RULES.length + ' 条规则）')
