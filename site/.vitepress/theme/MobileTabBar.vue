<script setup>
/**
 * 移动端底部标签栏（App 风格）。
 *
 * 只在窄屏出现：桌面端导航条已经够用，底部再挂一条会挤占阅读空间。
 * 用 CSS 控制显隐（见 custom.css 的 .dc-tabbar），JS 只负责标记当前项。
 *
 * 六个乐园入口，与主站 diuci.com、汉兜、连词成句完全同一组、同一顺序、同一图标。
 * 之前这里是「首页 + 总览 + 三个学段」：学段切换在侧栏抽屉（目录）里都有，
 * 而乐园入口在手机上反而一个都够不着——四站四套底部栏，孩子每换一个站都要重新认一遍。
 *
 * 视觉参数（高度、毛玻璃、圆体 10.5px、朱砂高亮）也在 custom.css 里与主站逐值对齐。
 */
const TABS = [
  { href: 'https://diuci.com/', label: '首页', path: 'M3.6 10.4 12 3.8l8.4 6.6|M5.8 9.2V19a1.4 1.4 0 0 0 1.4 1.4h9.6a1.4 1.4 0 0 0 1.4-1.4V9.2|M10 20.4v-5.2h4v5.2' },
  { href: 'https://k12.diuci.com/', label: '古诗文', path: 'M4 5.2A1.4 1.4 0 0 1 5.4 3.8H11a2 2 0 0 1 2 2v13a1.6 1.6 0 0 0-1.6-1.4H4z|M20 5.2a1.4 1.4 0 0 0-1.4-1.4H15a2 2 0 0 0-2 2v13a1.6 1.6 0 0 1 1.6-1.4H20z', on: true },
  { href: 'https://lian.diuci.com/', label: '连句', path: 'M4 7h6l3 5 3-5h4|M4 17h6l3-5|M13 17h7' },
  { href: 'https://ink.diuci.com/', label: '对战', path: 'M14.2 3.6H20a.4.4 0 0 1 .4.4v5.8|M20.4 3.6 11.2 12.8a2 2 0 0 0-.5 1l-.8 3.4a.5.5 0 0 0 .6.6l3.4-.8a2 2 0 0 0 1-.5l9.2-9.2' },
  { href: 'https://moon.diuci.com/', label: '月光', path: 'M20.5 14.3A8.6 8.6 0 0 1 9.7 3.5a8.6 8.6 0 1 0 10.8 10.8z' },
  { href: 'https://handle.diuci.com/', label: '汉兜', path: 'M3.6 3.6h7.6v7.6H3.6z|M12.8 3.6h7.6v7.6h-7.6z|M3.6 12.8h7.6v7.6H3.6z|M12.8 12.8h7.6v7.6h-7.6z' },
]
</script>

<template>
  <nav class="dc-tabbar" aria-label="快捷导航">
    <a
      v-for="t in TABS"
      :key="t.href"
      class="dc-tab"
      :class="{ on: t.on }"
      :href="t.href"
      :aria-current="t.on ? 'page' : undefined"
    >
      <svg class="ic" viewBox="0 0 24 24" aria-hidden="true">
        <path v-for="(d, i) in t.path.split('|')" :key="i" :d="d" />
      </svg>
      <span class="tx">{{ t.label }}</span>
    </a>
  </nav>
</template>
