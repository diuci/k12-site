import { defineConfig } from 'vitepress'

// 部署到 GitHub Pages 项目页时 base 为 /<repo>/；
// 若绑定了自定义域名 k12.diuci.com，则改为 '/'。
const base = process.env.SITE_BASE || '/k12-chinese-poetry/'

// 印章「诗」：本站自己的字。主站是「词」、连词成句是「连」、汉兜是「兜」，
// 四个站四枚字，一眼分得清。顶栏那枚印章由 CSS 画（要用圆体字体），
// 这里这份 SVG 只当 favicon 用。
const SEAL =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23c8442e'/%3E%3Ctext x='32' y='45' font-size='40' text-anchor='middle' fill='%23f7f1e3' font-family='serif'%3E%E8%AF%97%3C/text%3E%3C/svg%3E"

// 主题色跟随 <html data-theme>：切主题时同步手机浏览器地址栏。
// 首帧先按 localStorage / 系统偏好定好，避免地址栏和页面颜色不一致。
const THEME_COLOR = `(function(){var m=document.querySelector('meta[name="theme-color"]');if(!m)return;var d=document.documentElement;var sys=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;var s=null;try{s=localStorage.getItem('dc-theme')}catch(e){}var t=s||(sys?'dark':'light');d.setAttribute('data-theme',t);d.classList.toggle('dark',t==='dark');d.classList.toggle('light',t==='light');var set=function(){m.setAttribute('content',d.getAttribute('data-theme')==='dark'?'#17140f':'#f4ede0')};set();new MutationObserver(set).observe(d,{attributes:true,attributeFilter:['data-theme']})})();`

export default defineConfig({
  base,
  lang: 'zh-CN',
  title: '学古诗',
  titleTemplate: ':title | 学古诗',
  description:
    '小学到高中必背古诗文，按义务教育与高中课程标准收录。原文公有领域，注释译文赏析 CC BY 4.0。',

  // 刻意不声明 appearance：主题由 ThemeToggle.vue 通过 data-theme 接管，
  // 与主站 diuci.com 同一套机制。声明appearance 会让 VitePress 自带的
  // 开关重新出现（它只在 >=1280px 显示，且窄屏无入口）。

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: SEAL }],
    ['meta', { name: 'theme-color', content: '#f4ede0' }],
    ['script', {}, THEME_COLOR],
    // 与主站同一套字体：圆体标题、楷体译文、衬线正文
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    [
      'link',
      { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
    ],
    [
      'link',
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=ZCOOL+KuaiLe&family=ZCOOL+XiaoWei&display=swap',
      },
    ],
  ],

  // 搜索：内置 minisearch，中文按字切分，无需额外分词库
  themeConfig: {
    // 顶栏的印章实际由 custom.css 画（img 被隐藏）：SVG 里的文字用不到本站的圆体。
    logo: { src: SEAL, alt: '学古诗' },

    // 侧栏抽屉的折叠按钮文案，VitePress 默认硬编码英文 Menu。
    // 官方提供的配置项，直接中文化，比覆盖 CSS 干净。
    sidebarMenuLabel: '目录',

    // 顶部导航与主站 diuci.com 同一组、同一顺序、同一措辞。
    // 之前这里放着 8 个站内项 + 一个「丢词夺理」下拉：站内项侧栏里都有
    // （「开始」组 + 三个学段组），摆在顶栏只是把乐园入口挤进了下拉里。
    // 现在顶栏就是六个乐园，本站那一项标成当前页。
    nav: [
      { text: '首页', link: 'https://diuci.com/' },
      { text: '学古诗', link: '/', activeMatch: '^/$|^/vol/|^/poems/' },
      { text: '连词成句', link: 'https://lian.diuci.com/' },
      { text: '丢词大作战', link: 'https://ink.diuci.com/' },
      { text: '遗失月冕', link: 'https://moon.diuci.com/' },
      { text: '汉兜', link: 'https://handle.diuci.com/' },
      { text: '内容仓库', link: 'https://github.com/diuci/k12-chinese-poetry' },
    ],
    sidebar: [
      {
        text: '开始',
        items: [
          { text: '总览', link: '/' },
          { text: '打印版', link: '/print' },
          { text: '家长指南', link: '/guide' },
          { text: '数据来源与版权', link: '/sources' },
          { text: '版权与免责', link: '/legal' },
        ],
      },
      // 分类项一律指向册次列表页，页内列出该册全部篇目，
      // 不再直接跳到某一首诗。
      {
        text: '小学',
        collapsed: false,
        items: [
          { text: '一年级上册', link: '/vol/小学/一年级上册' },
          { text: '一年级下册', link: '/vol/小学/一年级下册' },
          { text: '二年级上册', link: '/vol/小学/二年级上册' },
          { text: '二年级下册', link: '/vol/小学/二年级下册' },
          { text: '三年级上册', link: '/vol/小学/三年级上册' },
          { text: '三年级下册', link: '/vol/小学/三年级下册' },
          { text: '四年级上册', link: '/vol/小学/四年级上册' },
          { text: '四年级下册', link: '/vol/小学/四年级下册' },
          { text: '五年级上册', link: '/vol/小学/五年级上册' },
          { text: '五年级下册', link: '/vol/小学/五年级下册' },
          { text: '六年级上册', link: '/vol/小学/六年级上册' },
          { text: '六年级下册', link: '/vol/小学/六年级下册' },
        ],
      },
      {
        text: '初中',
        collapsed: false,
        items: [
          { text: '七年级上册', link: '/vol/初中/七年级上册' },
          { text: '七年级下册', link: '/vol/初中/七年级下册' },
          { text: '七年级课外诵读', link: '/vol/初中/七年级课外诵读' },
          { text: '八年级上册', link: '/vol/初中/八年级上册' },
          { text: '八年级下册', link: '/vol/初中/八年级下册' },
          { text: '八年级上册课外诵读', link: '/vol/初中/八年级上册课外诵读' },
          { text: '八年级下册课外诵读', link: '/vol/初中/八年级下册课外诵读' },
          { text: '九年级上册', link: '/vol/初中/九年级上册' },
          { text: '九年级下册', link: '/vol/初中/九年级下册' },
        ],
      },
      {
        text: '高中',
        collapsed: false,
        items: [
          { text: '必修上册', link: '/vol/高中/必修上册' },
          { text: '必修下册', link: '/vol/高中/必修下册' },
          { text: '选择性必修上册', link: '/vol/高中/选择性必修上册' },
          { text: '选择性必修中册', link: '/vol/高中/选择性必修中册' },
          { text: '选择性必修下册', link: '/vol/高中/选择性必修下册' },
          { text: '选修（2026起默写）', link: '/vol/高中/选修（2026起默写）' },
        ],
      },
    ],

    search: {
      provider: 'local',
      options: {
        detailedView: true,
        miniSearch: {
          searchOptions: {
            fuzzy: 0.2,
            prefix: true,
            boost: { title: 4, author: 2, lines: 2 },
          },
        },
      },
    },

    outline: { level: [2, 3], label: '本页目录' },

    // socialLinks 去掉：乐园那组里已经有「内容仓库」这条文字链，
    // 顶栏再挂一枚 GitHub 图标就是同一个去处出现两种长相。

    // 页脚与主站 diuci.com 同一块结构：左边三行（牌子 / 篇数 / 许可），
    // 右边同一组六个乐园链接。牌子那行本身就是回主站的入口，
    // 所以不再单独列「主站首页」。
    footer: {
      message:
        '<a href="https://diuci.com/">丢词夺理 diuci.com</a> · 给孩子的古诗文' +
        '<br />共 253 篇 · 课标要求的 207 篇全部收录' +
        '<br />原文公有领域 · 注释 CC BY 4.0 · 代码 MIT · <a href="/legal">版权与免责</a>',
      copyright:
        '<a href="https://k12.diuci.com/">学古诗</a> ·' +
        '<a href="https://lian.diuci.com/">连词成句</a> ·' +
        '<a href="https://ink.diuci.com/">丢词大作战</a> ·' +
        '<a href="https://moon.diuci.com/">遗失月冕</a> ·' +
        '<a href="https://handle.diuci.com/">汉兜</a> ·' +
        '<a href="https://github.com/diuci/k12-chinese-poetry">内容仓库</a>' +
        '<br /><a href="/sources">数据来源</a> · <a href="mailto:hi@diuci.com">hi@diuci.com</a>',
    },

    lastUpdated: true,
    docFooter: { prev: '上一篇', next: '下一篇' },
  },
})
