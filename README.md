# k12-site

K12 中文古诗文站点，构建产物发布到 <https://k12.diuci.com>。

本仓只存放**站点呈现层**：页面骨架、样式、主题与部署流程。
所有诗文内容来自 [diuci/k12-chinese-poetry](https://github.com/diuci/k12-chinese-poetry)，由 CI 在构建时检出。

## 架构

```
k12-chinese-poetry          k12-site（本仓）
├── poems/    252 篇 md  →   ├── site/            站点骨架（手写）
├── data/     poems.json     ├── site/.vitepress/ 配置与主题
├── tools/    内容工具       ├── tools/build-site.py  编译脚本
└── LICENSE / PROVENANCE    └── .github/workflows/deploy.yml
```

`site/poems/`、`site/print.md`、`site/public/catalog.json` 都是
`tools/build-site.py` 在 CI 中生成的产物，不入库。

## 本地开发

需要本机已 checkout 内容仓（默认同级目录 `../k12-chinese-poetry`）：

```bash
npm install
CONTENT_ROOT=../k12-chinese-poetry npm run dev
```

## 构建

```bash
CONTENT_ROOT=../k12-chinese-poetry SITE_BASE=/ npm run build
```

`CONTENT_ROOT` 指向内容仓根目录（需含 `poems/` 与 `data/`）；
`SITE_BASE` 在绑定自定义域名时为 `/`。

## 许可

站点代码采用 CC BY 4.0。诗文内容版权归原作者所有（公有领域），
注释、译文、赏析的授权见内容仓 `PROVENANCE.md`。
