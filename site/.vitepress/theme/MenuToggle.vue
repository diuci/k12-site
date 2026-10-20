<script setup>
/**
 * 顶栏菜单（PLAN-移动端导航 v4.1）：小屏（≤768px）点开全部八站。
 *
 * 月冕/大作战是全屏游戏，底栏六项不摆它们（见 MobileTabBar）——
 * 这个面板是它们在手机上的唯一入口，缺了就是死路。
 *
 * 与 core/chrome.css 的 .dc-menu-btn/.dc-menu DOM 契约同形（钮在明暗钮左边）；
 * 样式在 custom.css 里与 chrome.css 同值镜像（k12 与 zimi 谜书是两份各写、注释互指）。
 */
import { ref, onMounted, onUnmounted } from 'vue'

const open = ref(false)

const MENU = [
  { href: 'https://diuci.com/', label: '首页' },
  { href: '/', label: '学古诗', on: true },
  { href: 'https://jiagu.diuci.com/', label: '画甲骨' },
  { href: 'https://lian.diuci.com/', label: '连词' },
  { href: 'https://zimi.diuci.com/', label: '猜谜' },
  { href: 'https://handle.diuci.com/', label: '汉兜' },
  { href: 'https://moon.diuci.com/', label: '月冕' },
  { href: 'https://ink.diuci.com/', label: '大作战' },
]

function onDocClick(e) {
  const n = e.target
  if (open.value && n instanceof Element && !n.closest('.dc-menu') && !n.closest('.dc-menu-btn')) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <button class="dc-menu-btn" type="button" aria-label="全部乐园" title="全部乐园"
          :aria-expanded="open ? 'true' : 'false'" @click.stop="open = !open">
    <svg class="i-bars" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6.8h16M4 12h16M4 17.2h16"/></svg>
    <svg class="i-x" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
  </button>
  <nav class="dc-menu" :hidden="!open" aria-label="全部乐园">
    <div class="dc-menu-in">
      <a v-for="m in MENU" :key="m.label" :href="m.href" :class="{ on: m.on }"
         :aria-current="m.on ? 'page' : undefined">{{ m.label }}</a>
    </div>
  </nav>
</template>
