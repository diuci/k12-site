<script setup>
/**
 * 繁简切换：本站的繁简是「换页」，不是就地转写。
 *
 * 简体页 ↔ /trad/ 下的同名页（build-site.py 两边都生成，繁体页由简体 md 派生）。
 * 没有繁体对应的页面——高考默写、打印版、家长指南、数据来源、内容准确性、版权与免责——
 * 不摆这枚钮：摆了就是点了没反应（规范 §3）。
 *
 * 状态键 dc-script 与主站同一个名字；这里记下的是「用户想要哪一种」，
 * 真正的繁简由落在哪一页决定。
 */
import { computed } from 'vue'
import { useRoute, withBase } from 'vitepress'

const route = useRoute()

function normalize(p) {
  return String(p || '').replace(/index\.html$/i, '').replace(/\.html$/i, '')
}

function counterpart(p) {
  const norm = normalize(p)
  if (norm === '/trad' || norm.startsWith('/trad/')) {
    const rest = norm.slice(5)
    return rest === '' ? '/' : '/' + rest
  }
  if (norm === '/') return '/trad/'
  if (norm.startsWith('/poems/') || norm.startsWith('/vol/')) return '/trad' + norm
  return null
}

const target = computed(() => counterpart(route.path))
const isTrad = computed(() => {
  const norm = normalize(route.path)
  return norm === '/trad' || norm.startsWith('/trad/')
})

function go() {
  if (!target.value) return
  try {
    localStorage.setItem('dc-script', isTrad.value ? 'hans' : 'hant')
  } catch (e) {
    /* 隐私模式下 localStorage 可能抛错：跳转照做，记住这一步放弃 */
  }
  window.location.href = withBase(target.value)
}
</script>

<template>
  <button
    v-if="target"
    class="dc-lang-btn"
    type="button"
    aria-label="繁简切换"
    title="繁简切换"
    @click="go"
  >{{ isTrad ? '简' : '繁' }}</button>
</template>
