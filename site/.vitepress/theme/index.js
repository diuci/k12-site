import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import ThemeToggle from './ThemeToggle.vue'
import './custom.css'

// 明暗切换：与主站 diuci.com 同一套机制（data-theme + localStorage）。
// 挂到 nav-bar-content-after，窄屏宽屏都在；VitePress 自带那颗开关已在 CSS 里隐藏。
const Layout = {
  render() {
    return h(DefaultTheme.Layout, null, {
      'nav-bar-content-after': () => h(ThemeToggle),
    })
  },
}

export default {
  extends: DefaultTheme,
  Layout,
}