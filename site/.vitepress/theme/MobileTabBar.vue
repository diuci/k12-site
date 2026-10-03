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
 * 视觉与主站 diuci.com 的底部栏同一套参数（高度 58px、毛玻璃、
 * 圆体 10.5px 字号、朱砂高亮），两站观感一致。
 * 菜单项不同：主站是四个乐园入口，这里是学段切换 +
 * 首个「首页」项作为返回主站的跳板，形成双向互跳。
 */
import { computed, onMounted, ref } from 'vue'

const HOME = 'https://diuci.com/'

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
  <nav class="dc-tabbar" aria-label="快捷导航">
    <a class="dc-tab" :href="HOME">
      <svg class="ic" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3.6 10.4 12 3.8l8.4 6.6" />
        <path d="M5.8 9.2V19a1.4 1.4 0 0 0 1.4 1.4h9.6a1.4 1.4 0 0 0 1.4-1.4V9.2" />
        <path d="M10 20.4v-5.2h4v5.2" />
      </svg>
      <span class="tx">首页</span>
    </a>
    <a
      v-for="t in TABS"
      :key="t.href"
      class="dc-tab"
      :class="{ on: active === t.href }"
      :href="t.href"
    >
      <svg v-if="t.icon === 'home'" class="ic" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 4.4h6.2l1.6 2.2H20a.4.4 0 0 1 .4.4v11.4a.4.4 0 0 1-.4.4H4a.4.4 0 0 1-.4-.4V4.8a.4.4 0 0 1 .4-.4z" />
        <path d="M9.4 12.6l5.4 3.2-5.4 3.2z" />
      </svg>
      <svg v-else class="ic" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5.2A1.4 1.4 0 0 1 5.4 3.8H11a2 2 0 0 1 2 2v13a1.6 1.6 0 0 0-1.6-1.4H4z" />
        <path d="M20 5.2a1.4 1.4 0 0 0-1.4-1.4H15a2 2 0 0 0-2 2v13a1.6 1.6 0 0 1 1.6-1.4H20z" />
      </svg>
      <span class="tx">{{ t.label }}</span>
    </a>
  </nav>
</template>