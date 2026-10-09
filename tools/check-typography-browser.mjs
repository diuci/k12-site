#!/usr/bin/env node
/*
  字号一致性实测闸门（规范 §5）：真的开浏览器量，不只看源码。

  静态闸门（check-typography.mjs）盯的是生成结构；这一条盯的是渲染结果——
  同一首里前两句 16px、后两句 20.8px 这种事，只有量出来才算数。
  它跑在本地链（chain-site.ps1）里：CI 里没有 Chrome，跑不动就别假装跑过。

  每个规则都配坏例子（--selftest）；空过的检查比没有检查更危险。
*/
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'

const DIST = path.resolve('site/.vitepress/dist')
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' }
const BLOCKS = ['.poem-body', '.full-body']

function fail(msg) { console.error('[check-typography-browser] ' + msg); process.exit(1) }
function walkHtml(dir) {
  if (!fs.existsSync(dir)) return []
  const out = []
  for (const e of fs.readdirSync(dir)) {
    const p = path.join(dir, e)
    if (fs.statSync(p).isDirectory()) out.push(...walkHtml(p))
    else if (e.endsWith('.html')) out.push(p)
  }
  return out
}
function toUrl(file) {
  return '/' + path.relative(DIST, file).split(path.sep).map(encodeURIComponent).join('/')
}

/* 纯函数部分：坏例子直接喂给它，不需要浏览器 */
function inspectDom(html) {
  const problems = []
  for (const sel of BLOCKS) {
    const cls = sel.slice(1)
    let from = 0
    while (true) {
      const i = html.indexOf('class="' + cls + '"', from)
      if (i < 0) break
      const end = html.indexOf('</div>', i)
      if (end < 0) break
      const body = html.slice(i, end)
      from = end + 6
      // 内联字号：正文里给某一句开小灶
      const inline = body.match(/style="[^"]*font-size[^"]*"/)
      if (inline) problems.push(sel + ' 块里有内联 font-size：' + inline[0].slice(0, 60))
      // 块内直接子节点必须都是 <p>（其它标签会被 markdown-it 区别对待，字号容易分叉）
      const direct = body.slice(body.indexOf('>') + 1).match(/^\s*<(\/?[a-zA-Z][a-zA-Z0-9]*)/)
      if (direct && direct[1] !== 'p' && !direct[1].startsWith('/')) problems.push(sel + ' 块里第一个直接子标签是 <' + direct[1] + '>，不是 <p>')
    }
  }
  return problems
}

function selftest() {
  const good = '<div class="poem-body"><p>第一句</p><p>第二句</p></div>'
  const cases = [
    ['块里第一句是裸 <ruby>', '<div class="poem-body"><ruby>鹅<rt>e</rt></ruby><p>第二句</p></div>'],
    ['块里给某一句开了内联字号', '<div class="poem-body"><p style="font-size:22px">第一句</p><p>第二句</p></div>'],
    ['块里用 <div> 分行', '<div class="poem-body"><div>第一句</div><p>第二句</p></div>'],
  ]
  let tried = 0, caught = 0
  for (const [why, html] of cases) {
    tried++
    const probs = inspectDom(html)
    if (probs.length) caught++
    else console.error('  坏例子没抓住：' + why)
  }
  const goodProbs = inspectDom(good)
  if (goodProbs.length) { tried++; console.error('  好例子被误报 → ' + goodProbs[0]) }
  if (caught !== tried) { console.error('[check-typography-browser] --selftest 失败：试了 ' + tried + ' 例，抓住 ' + caught + ' 例'); process.exit(1) }
  console.log('[ok] check-typography-browser --selftest 通（当场数到 ' + tried + ' 个坏例子，全部试到）')
}

if (process.argv.includes('--selftest')) { selftest(); process.exit(0) }

if (!fs.existsSync(DIST)) fail('没有 ' + DIST + '：先 npm run build')
const pages = walkHtml(DIST).filter(f => /[/\\](poems|trad)[/\\]/.test(f))
if (!pages.length) fail('dist 里没找到诗文页')

let puppeteer
try {
  puppeteer = (await import('puppeteer-core')).default
} catch (e) { fail('本站没有 puppeteer-core：npm i -D puppeteer-core') }
const CHROME = ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'].find(c => fs.existsSync(c))
if (!CHROME) fail('找不到 Chrome/Edge')

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0])
  if (p.endsWith('/')) p += 'index.html'
  const f = path.join(DIST, p)
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('nope'); return }
  res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream' })
  res.end(fs.readFileSync(f))
})
await new Promise(r => server.listen(18791, r))

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox', '--disable-dev-shm-usage'] })
const page = await browser.newPage()
// 字体与本站字号无关，却会让每一页多等一次外网往返：拦掉，闸门只量该量的东西
await page.setRequestInterception(true)
page.on('request', req => {
  const u = req.url()
  if (u.includes('fonts.googleapis.com') || u.includes('fonts.gstatic.com')) req.abort()
  else req.continue()
})
const VIEWPORTS = [{ width: 1180, height: 900 }, { width: 390, height: 780 }]
const problems = []
let checked = 0, blocks = 0
for (const vp of VIEWPORTS) {
  await page.setViewport(vp)
  for (const f of pages) {
    const url = 'http://127.0.0.1:18791' + toUrl(f)
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
    if (resp.status() !== 200) { problems.push(toUrl(f) + ' HTTP ' + resp.status()); continue }
    const rel = path.relative(DIST, f).split(path.sep).join('/')
    const found = await inspectDom(await page.content())
    for (const p of found) problems.push(rel + '（' + vp.width + 'px）：' + p)
    const sizes = await page.evaluate((sels) => {
      const out = []
      for (const sel of sels) {
        for (const block of document.querySelectorAll(sel)) {
          const own = Array.from(block.children).filter(el => el.tagName === 'P')
          const map = new Map()
          for (const el of own) {
            const fsz = getComputedStyle(el).fontSize
            map.set(fsz, (map.get(fsz) || 0) + 1)
          }
          if (map.size) out.push({ sel, sizes: Array.from(map.entries()) })
        }
      }
      return out
    }, BLOCKS)
    for (const b of sizes) {
      blocks++
      if (b.sizes.length > 1) problems.push(rel + '（' + vp.width + 'px）：' + b.sel + ' 块里出现了 ' + b.sizes.length + ' 档字号 ' + JSON.stringify(b.sizes) + '——同一块内容只许一档')
    }
    checked++
    if (checked % 50 === 0) console.log('  …已量 ' + checked + ' 页（' + vp.width + 'px）')
  }
}
await browser.close()
server.close()

console.log('（量了 ' + checked + ' 个页面 × ' + VIEWPORTS.length + ' 种视口，数到 ' + blocks + ' 个正文块）')
if (problems.length) {
  for (const p of problems.slice(0, 20)) console.error('  ' + p)
  if (problems.length > 20) console.error('  …还有 ' + (problems.length - 20) + ' 处')
  console.error('[check-typography-browser] 失败：' + problems.length + ' 处不合规')
  process.exit(1)
}
console.log('[ok] check-typography-browser 通：每一块正文只有一档字号')
