import { createRequire } from 'module'
import { defineConfig } from 'vitepress'

const require = createRequire(import.meta.url)
const pkg = require('vitepress/package.json')

export default defineConfig({
  lang: 'zh-CN',
  description: '一个HTTP定时任务自动执行Web框架。',

  themeConfig: {
    nav: nav(),

    lastUpdatedText: '最后更新',

    sidebar: {
      '/zh_CN/guide/': sidebarGuide()
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/qiandao-today/qiandao' }
    ],

    footer: {
        message: '基于 MIT 许可证发布.',
        copyright: 'Copyright © 2023-当前 QD 开发者'
    },

    editLink: {
        pattern: 'https://github.com/qiandao-today/qiandao/edit/master/docs/:path',
        text: '在 GitHub 中编辑此页面'
    },

    outline: {
        label: '页面导航',
    },

  }
})

function nav() {
  return [
    { text: '指南', link: '/zh_CN/guide/what-is-qd' },
    { text: 'Gitee', link: 'https://gitee.com/a76yyyy/qiandao' },
  ]
}

function sidebarGuide() {
  return [
    {
        text: '指南',
        items: [
            { text: '什么是 QD?', link: '/zh_CN/guide/what-is-qd' },
            { text: '部署', link: '/zh_CN/guide/deployment' },
            { text: '如何使用?', link: '/zh_CN/guide/how-to-use' },
            { text: '更新', link: '/zh_CN/guide/update' },
            { text: '常见问题', link: '/zh_CN/guide/faq' },
        ]
    }
  ]
}
