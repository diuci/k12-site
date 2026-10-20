<script setup>
/**
 * 移动端底部标签栏（App 风格）。
 *
 * 只在窄屏出现：桌面端导航条已经够用，底部再挂一条会挤占阅读空间。
 * 用 CSS 控制显隐（见 custom.css 的 .dc-tabbar），JS 只负责标记当前项。
 *
 * 底栏六项（v4.1）：月冕/大作战是全屏游戏，不占拇指栏——它们在顶栏菜单（MenuToggle）里。
 *
 * 视觉参数（高度、毛玻璃、圆体 10.5px、朱砂高亮）也在 custom.css 里与主站逐值对齐。
 */
const TABS = [
  { href: 'https://diuci.com/', label: '首页', path: 'M3.6 10.4 12 3.8l8.4 6.6|M5.8 9.2V19a1.4 1.4 0 0 0 1.4 1.4h9.6a1.4 1.4 0 0 0 1.4-1.4V9.2|M10 20.4v-5.2h4v5.2' },
  { href: 'https://k12.diuci.com/', label: '学古诗', path: 'M4 5.2A1.4 1.4 0 0 1 5.4 3.8H11a2 2 0 0 1 2 2v13a1.6 1.6 0 0 0-1.6-1.4H4z|M20 5.2a1.4 1.4 0 0 0-1.4-1.4H15a2 2 0 0 0-2 2v13a1.6 1.6 0 0 1 1.6-1.4H20z', on: true },
  { href: 'https://jiagu.diuci.com/', label: '画甲骨', path: 'M6.2 4.6h11.6a1.6 1.6 0 0 1 1.6 1.6v11.6a1.6 1.6 0 0 1-1.6 1.6H6.2a1.6 1.6 0 0 1-1.6-1.6V6.2a1.6 1.6 0 0 1 1.6-1.6z|M12 8.4v7.2|M9.6 12h4.8' },
  { href: 'https://lian.diuci.com/', label: '连词', path: 'M5.4 6.6a2.3 2.3 0 1 0 0.01 0|M12 12a2.3 2.3 0 1 0 0.01 0|M18.6 17.4a2.3 2.3 0 1 0 0.01 0|M7.1 8.3l3.5 2.4M13.4 13.3l3.5 2.4' },
  { href: 'https://zimi.diuci.com/', label: '猜谜', path: 'M4.2 5.4h15.6|M7.2 5.4v13.2|M16.8 5.4v13.2|M9.4 18.6h5.2|M9.8 9.6a2.4 2.4 0 1 1 3.3 2.2c-.7.35-1.1.95-1.1 1.7v.5' },
  { href: 'https://handle.diuci.com/', label: '汉兜', path: 'M5.6 3.6h3.6a2 2 0 0 1 2 2v3.6a2 2 0 0 1-2 2H5.6a2 2 0 0 1-2-2V5.6a2 2 0 0 1 2-2z|M14.8 3.6h3.6a2 2 0 0 1 2 2v3.6a2 2 0 0 1-2 2h-3.6a2 2 0 0 1-2-2V5.6a2 2 0 0 1 2-2z|M5.6 12.8h3.6a2 2 0 0 1 2 2v3.6a2 2 0 0 1-2 2H5.6a2 2 0 0 1-2-2v-3.6a2 2 0 0 1 2-2z|M14.8 12.8h3.6a2 2 0 0 1 2 2v3.6a2 2 0 0 1-2 2h-3.6a2 2 0 0 1-2-2v-3.6a2 2 0 0 1 2-2z' },
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
