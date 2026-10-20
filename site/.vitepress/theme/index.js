import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import ThemeToggle from './ThemeToggle.vue'
import MenuToggle from './MenuToggle.vue'
import MobileTabBar from './MobileTabBar.vue'
import './custom.css'

// 明暗切换：与主站 diuci.com 同一套机制（core/theme 约定，v4 起写 cookie 跨站共享）。
// 挂到 nav-bar-content-after，窄屏宽屏都在；VitePress 自带那颗开关已在 CSS 里隐藏。
// 顶部菜单（v4.1）：菜单钮在明暗钮左边，小屏点开全部八站（含月冕/大作战）。
//
// 移动端底部标签栏：挂到 layout-bottom，只在窄屏显示（CSS 控制），
// 给 kids 一个 App 式的拇指可达导航。
const Layout = {
  render() {
    return h(DefaultTheme.Layout, null, {
      'nav-bar-content-after': () => h('span', { class: 'dc-nav-actions' }, [h(MenuToggle), h(ThemeToggle)]),
      'layout-bottom': () => h(MobileTabBar),
    })
  },
}

export default {
  extends: DefaultTheme,
  Layout,
}
