<script setup>
/**
 * 明暗切换：与主站 diuci.com 完全同一套机制。
 *
 * 为什么不用 VitePress 自带的 VPSwitchAppearance：
 * 那个开关只在 >=1280px 显示（VPNavBarAppearance.vue 里的 min-width 媒体查询），
 * 窄屏根本看不到；且它的 isDark 依赖 useData() 的 appearance 配置，
 * 未显式声明时会退化成常量，点了没反应。
 * 这里改用 data-theme 属性 + localStorage，与主站逐行对应，
 * 窄屏 / 宽屏行为一致，也不依赖 VitePress 内部实现。
 */
import { onMounted, ref } from 'vue'

const KEY = 'dc-theme'
const LIGHT = '#f4ede0'
const DARK = '#17140f'

const isDark = ref(false)

function apply(t) {
  const root = document.documentElement
  root.dataset.theme = t
  root.classList.toggle('dark', t === 'dark')
  root.classList.toggle('light', t === 'light')
  isDark.value = t === 'dark'
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', t === 'dark' ? DARK : LIGHT)
}

onMounted(() => {
  let saved = null
  try {
    saved = localStorage.getItem(KEY)
  } catch (e) {
    /* 隐私模式下 localStorage 可能抛错，降级为跟随系统 */
  }
  if (!saved) {
    saved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  apply(saved)

  // 用户没手动选过之前，系统切换时跟随
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const onSys = e => {
    let s = null
    try {
      s = localStorage.getItem(KEY)
    } catch (err) {
      /* 同上 */
    }
    if (!s) apply(e.matches ? 'dark' : 'light')
  }
  if (mq.addEventListener) mq.addEventListener('change', onSys)
  else if (mq.addListener) mq.addListener(onSys)
})

function toggle() {
  const t = isDark.value ? 'light' : 'dark'
  try {
    localStorage.setItem(KEY, t)
  } catch (e) {
    /* 忽略 */
  }
  apply(t)
}
</script>

<template>
  <button
    class="dc-theme-btn"
    :aria-label="isDark ? '切换浅色模式' : '切换深色模式'"
    :title="isDark ? '切换浅色模式' : '切换深色模式'"
    @click="toggle"
  >
    <svg class="i-sun" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.4 5.4l1.6 1.6M17 17l1.6 1.6M18.6 5.4L17 7M7 17l-1.6 1.6" />
    </svg>
    <svg class="i-moon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20 14.2A8.2 8.2 0 0 1 9.8 4a8.4 8.4 0 1 0 10.2 10.2z" />
    </svg>
  </button>
</template>