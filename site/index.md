---
layout: page
title: 总览
description: 小学到高中必背古诗文 253 篇，按学段、主题、体裁筛选。
sidebar: false
aside: false
---

<div class="hero">
  <div class="hero-grid">
    <div>
      <span class="eyebrow"><span class="dot"></span>课标 207 篇 + 教材拓展 46 篇 · 小学到高中</span>
      <h1>读古诗<br>记古诗<span class="accent">也玩古诗</span></h1>
      <p class="hero-sub">原文、注释、译文、赏析，<b>253 篇一篇都不少</b>。</p>
      <p class="hero-p">这里的每一篇都对着人教社统编教材来的——逐句拼音、背诵范围、考点标注都清清楚楚。读完背不动了，去<a class="hl" href="https://lian.diuci.com/">连词成句</a> 把这段课文连出来、排回顺序；或者去<a class="hl" href="https://ink.diuci.com/">丢词大作战</a> 把字涂一地。</p>
      <div class="hero-btns">
        <a class="btn btn-p" href="#all">开始阅读 <span>→</span></a>
        <a class="btn btn-s" href="/print">打印整册</a>
      </div>
      <div class="hero-stats">
        <div class="stat"><b>253</b><span>课文篇目</span></div>
        <div class="stat"><b>110</b><span>小学</span></div>
        <div class="stat"><b>71</b><span>初中</span></div>
        <div class="stat"><b>72</b><span>高中</span></div>
      </div>
    </div>
    <div class="hero-art">
      <span class="ink-splat sp-1"></span>
      <span class="ink-splat sp-2"></span>
      <article class="hcard card-1">
        <div class="card-t">静夜思</div>
        <div class="card-a">唐 · 李白</div>
        <div class="card-l">床前明月光<br>疑是地上霜</div>
        <div class="card-g">小学 一年级下册</div>
      </article>
      <article class="hcard card-2">
        <div class="card-t">春晓</div>
        <div class="card-a">唐 · 孟浩然</div>
        <div class="card-l">春眠不觉晓<br>处处闻啼鸟</div>
        <div class="card-g">小学 一年级下册</div>
      </article>
      <article class="hcard card-3">
        <div class="card-t">江雪</div>
        <div class="card-a">唐 · 柳宗元</div>
        <div class="card-l">千山鸟飞绝<br>万径人踪灭</div>
        <div class="card-g">小学 二年级上册</div>
      </article>
    </div>
  </div>
</div>

<div class="wrap-alt" id="all">
  <div class="sec-head">
    <span class="sec-k">全 部 篇 目</span>
    <h2>253 篇，按学段主题筛</h2>
    <p class="sec-p">课文用字以人教社统编教材为准。诗文原文属公有领域；注释、译文、赏析与选篇编排采用 CC BY 4.0。</p>
  </div>
</div>

<div class="wrap-alt">
  <div class="filters">
    <h3>学段 / 年级</h3>
    <div class="chips" id="f-stage"></div>
    <h3>主题</h3>
    <div class="chips" id="f-theme"></div>
    <h3>体裁</h3>
    <div class="chips" id="f-form"></div>
    <p class="count" id="count"></p>
  </div>
  <div class="grid" id="grid"></div>
  <p class="count" style="margin-top:20px">
    提示：按 <kbd>Ctrl</kbd>+<kbd>K</kbd>（macOS <kbd>⌘</kbd>+<kbd>K</kbd>）可全文搜索篇名、作者、诗句。
  </p>
</div>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useData } from 'vitepress'

// 用 siteData.base 拼路径：部署到 /<repo>/ 子路径时，
// 绝对路径 /catalog.json 会 404
const { site } = useData()
const RECITE = { full: '全文背', section: '背段落', line: '背名句', none: '理解' }

const all = ref([])
const fStage = ref('')
const fTheme = ref('')
const fForm = ref('')

const STAGES = ['小学', '初中', '高中']

onMounted(async () => {
  const res = await fetch(site.value.base + 'catalog.json')
  all.value = await res.json()

  // 筛选器：学段按固定顺序，主题与体裁按出现频次
  buildChips('f-stage', STAGES, () => fStage.value, v => (fStage.value = v))
  const themes = countBy(p => p.theme)
  const forms = countBy(p => [p.form])
  buildChips('f-theme', themes, () => fTheme.value, v => (fTheme.value = v))
  buildChips('f-form', forms, () => fForm.value, v => (fForm.value = v))
  render()
})

function countBy(fn) {
  const m = new Map()
  for (const p of all.value) {
    for (const k of [].concat(fn(p))) {
      if (k) m.set(k, (m.get(k) || 0) + 1)
    }
  }
  return [...m.entries()].sort((a, b) => b[1] - a[1]).map(([k]) => k)
}

function buildChips(id, keys, get, set) {
  const box = document.getElementById(id)
  if (!box) return
  const mk = (label, val, on) => {
    const s = document.createElement('span')
    s.className = 'chip' + (on ? ' on' : '')
    s.textContent = label
    s.onclick = () => {
      set(val)
      ;[...box.children].forEach(c => c.classList.remove('on'))
      if (val) s.classList.add('on')
      render()
    }
    return s
  }
  box.appendChild(mk('全部', '', false))
  for (const k of keys) box.appendChild(mk(k, k, false))
}

const shown = computed(() =>
  all.value.filter(
    p =>
      (!fStage.value || p.stage === fStage.value) &&
      (!fForm.value || p.form === fForm.value) &&
      (!fTheme.value || (p.theme || []).includes(fTheme.value))
  )
)

function render() {
  const grid = document.getElementById('grid')
  const cnt = document.getElementById('count')
  if (!grid) return
  grid.innerHTML = ''
  for (const p of shown.value) {
    const a = document.createElement('a')
    a.className = 'card'
    a.href = p.url
    const badge = p.recite && RECITE[p.recite] && p.recite !== 'none'
      ? `<span class="badge badge-recite">${RECITE[p.recite]}</span>` : ''
    a.innerHTML =
      `<div class="card-t">${esc(p.title)}${badge}</div>` +
      `<div class="card-a">${esc(p.author)} · ${esc(p.dynasty || '')}</div>` +
      (p.lines ? `<div class="card-l">${esc(p.lines)}</div>` : '') +
      `<div class="card-g">${esc(p.stage)} ${esc(p.volume || '')}</div>`
    grid.appendChild(a)
  }
  if (cnt) {
    cnt.textContent = shown.value.length === all.value.length
      ? `共 ${all.value.length} 篇`
      : `筛选出 ${shown.value.length} / ${all.value.length} 篇`
  }
}

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])
}
</script>