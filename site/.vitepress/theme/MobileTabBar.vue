<script setup>
/**
 * 移动端底部标签栏（App 风格）。
 *
 * 只在窄屏出现：桌面端导航条已经够用，底部再挂一条会挤占阅读空间。
 * 用 CSS 控制显隐（见 custom.css 的 .dc-tabbar），JS 只负责高亮当前项。
 *
 * 为什么用固定定位而不是 VitePress 的 .VPNavScreen：
 * 后者是「汉堡菜单」全屏抽屉，属于 Web 导航习惯；
 * 底部标签栏是 App 习惯，拇指可达、单手切换更快，适合 kids 反复翻篇目。
 *
 * 四项而非五项：414px 宽下五项每项不足 70px，「打印」两字加图标会挤。
 * 打印版在桌面端导航里有入口，手机上不是高频功能，移到桌面即可。
 */
import { computed, onMounted, ref } from 'vue'

const TABS = [
  { href: '/', label: '总览', icon: 'home' },
  { href: '/vol/小学/一年级上册', label: '小学', icon: 'book' },
  { href: '/vol/初中/七年级上册', label: '初中', icon: 'book' },
  { href: '/vol/高中/必修上册', label: '高中', icon: 'book' },
]

const path = ref('/')

onMounted(() => {
  path.value = window.location.pathname
})

const active = computed(() => {
  const p = decodeURIComponent(path.value)
  if (p === '/' || p === '') return '/'
  // 册次页与单篇页都高亮所属学段
  for (const t of TABS) {
    if (t.href === '/') continue
    const seg = t.href.split('/')[2]
    if (p.includes('/' + seg + '/')) return t.href
  }
  return p
})
</script>

<template>
  <nav class="dc-tabbar" aria-label="主导航">
    <a
      v-for="t in TABS"
      :key="t.href"
      class="dc-tab"
      :class="{ on: active === t.href || (t.href === '/' && active === '/') }"
      :href="t.href"
    >
      <svg class="ic" viewBox="0 0 24 24" aria-hidden="true">
        <template v-if="t.icon === 'home'">
          <path d="M3.6 10.4 12 3.8l8.4 6.6" />
          <path d="M5.8 9.2V19a1.4 1.4 0 0 0 1.4 1.4h9.6a1.4 1.4 0 0 0 1.4-1.4V9.2" />
          <path d="M10 20.4v-5.2h4v5.2" />
        </template>
        <template v-else>
          <path d="M4 5.2A1.4 1.4 0 0 1 5.4 3.8H11a2 2 0 0 1 2 2v13a1.6 1.6 0 0 0-1.6-1.4H4z" />
          <path d="M20 5.2a1.4 1.4 0 0 0-1.4-1.4H15a2 2 0 0 0-2 2v13a1.6 1.6 0 0 1 1.6-1.4H20z" />
        </template>
      </svg>
      <span class="tx">{{ t.label }}</span>
    </a>
  </nav>
</template>