import { defineConfig } from 'vitepress'

// 部署到 GitHub Pages 项目页时 base 为 /<repo>/；
// 若绑定了自定义域名 k12.diuci.com，则改为 '/'。
const base = process.env.SITE_BASE || '/k12-chinese-poetry/'

// 印章「词」：主站与本站同一枚 SVG，导航与 favicon 共用
const SEAL =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23c8442e'/%3E%3Ctext x='32' y='45' font-size='40' text-anchor='middle' fill='%23f7f1e3' font-family='serif'%3E%E8%AF%8D%3C/text%3E%3C/svg%3E"

// VitePress 切主题只改<html> 上的 class，不会同步 theme-color，
// 这里用 MutationObserver 跟随，让手机浏览器地址栏跟着换色。
const THEME_COLOR = `(function(){var m=document.querySelector('meta[name="theme-color"]');if(!m)return;var set=function(){m.setAttribute('content',document.documentElement.classList.contains('dark')?'#17140f':'#f4ede0')};set();new MutationObserver(set).observe(document.documentElement,{attributes:true,attributeFilter:['class']})})();`

export default defineConfig({
  base,
  lang: 'zh-CN',
  title: '丢词夺理',
  titleTemplate: ':title | 丢词夺理',
  description:
    '小学到高中必背古诗文，按义务教育与高中课程标准收录。原文公有领域，注释译文赏析 CC BY 4.0。',

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
    logo: { src: SEAL, alt: '丢词夺理' },

    nav: [
      { text: '总览', link: '/' },
      { text: '按学段', link: '/poems/小学/一年级上册/咏鹅' },
      { text: '打印版', link: '/print' },
      { text: '家长指南', link: '/guide' },
      { text: '数据来源', link: '/sources' },
      {
        text: '丢词夺理',
        items: [
          { text: '主站首页', link: 'https://diuci.com/' },
          { text: '古诗文', link: 'https://k12.diuci.com/' },
          { text: '丢词大作战', link: 'https://ink.diuci.com/' },
          { text: '遗失月冕', link: 'https://moon.diuci.com/' },
          { text: '内容仓库', link: 'https://github.com/diuci/k12-chinese-poetry' },
        ],
      },
    ],

    sidebar: [
      {
        text: '开始',
        items: [
          { text: '总览', link: '/' },
          { text: '打印版', link: '/print' },
          { text: '家长指南', link: '/guide' },
          { text: '数据来源与版权', link: '/sources' },
        ],
      },
      {
        text: '小学',
        collapsed: false,
        items: [
          { text: '一年级上册', link: '/poems/小学/一年级上册/咏鹅' },
          { text: '一年级下册', link: '/poems/小学/一年级下册/静夜思' },
          { text: '二年级上册', link: '/poems/小学/二年级上册/敕勒歌' },
          { text: '二年级下册', link: '/poems/小学/二年级下册/咏柳' },
          { text: '三年级上册', link: '/poems/小学/三年级上册/望天门山' },
          { text: '三年级下册', link: '/poems/小学/三年级下册/元日' },
          { text: '四年级上册', link: '/poems/小学/四年级上册/鹿柴' },
          { text: '四年级下册', link: '/poems/小学/四年级下册/芙蓉楼送辛渐' },
          { text: '五年级上册', link: '/poems/小学/五年级上册/山居秋暝' },
          { text: '五年级下册', link: '/poems/小学/五年级下册/凉州词' },
          { text: '六年级上册', link: '/poems/小学/六年级上册/宿建德江' },
          { text: '六年级下册', link: '/poems/小学/六年级下册/竹石' },
        ],
      },
      {
        text: '初中',
        collapsed: true,
        items: [
          { text: '七年级', link: '/poems/初中/七年级上册/观沧海' },
          { text: '八年级', link: '/poems/初中/八年级上册/三峡' },
          { text: '九年级', link: '/poems/初中/九年级上册/水调歌头' },
        ],
      },
      {
        text: '高中',
        collapsed: true,
        items: [
          { text: '必修上册', link: '/poems/高中/必修上册/劝学' },
          { text: '必修下册', link: '/poems/高中/必修下册/赤壁赋' },
          { text: '选择性必修', link: '/poems/高中/选择性必修上册/过秦论' },
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

    socialLinks: [
      { icon: 'github', link: 'https://github.com/diuci/k12-chinese-poetry' },
    ],

    footer: {
      message:
        '诗文原文属公有领域；注释、译文、赏析与选篇编排 © 丢词夺理，采用 CC BY 4.0。' +
        '<br />丢词夺理：' +
        '<a href="https://diuci.com/">主站首页</a> ·' +
        '<a href="https://k12.diuci.com/">古诗文</a> ·' +
        '<a href="https://ink.diuci.com/">丢词大作战</a> ·' +
        '<a href="https://moon.diuci.com/">遗失月冕</a>',
      copyright: '内容来源与授权说明见「数据来源与版权」。',
    },

    lastUpdated: true,
    docFooter: { prev: '上一篇', next: '下一篇' },
  },
})
