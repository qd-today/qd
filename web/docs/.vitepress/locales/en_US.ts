import { createRequire } from 'module'
import { defineConfig } from 'vitepress'

const require = createRequire(import.meta.url)
const pkg = require('vitepress/package.json')

export default defineConfig({
  lang: 'en-US',
  description: 'A web framework for HTTP timed task automation.',

  themeConfig: {
    nav: nav(),

    lastUpdatedText: 'last Updated',

    sidebar: {
      '/guide/': sidebarGuide()
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/qiandao-today/qiandao' }
    ],

    footer: {
        message: 'Released under the MIT License.',
        copyright: 'Copyright © 2023-present QD Developers'
    },

    editLink: {
        pattern: 'https://github.com/qiandao-today/qiandao/edit/master/docs/:path',
        text: 'Edit this page on GitHub'
    },

    outline: {
      label: 'On this page',
    },

  }
})

function nav() {
  return [
    { text: 'Guide', link: '/guide/what-is-qd' },
    { text: 'Gitee', link: 'https://gitee.com/a76yyyy/qiandao' },
  ]
}

function sidebarGuide() {
  return [
    {
        text: 'Guide',
        items: [
            { text: 'What is QD?', link: '/guide/what-is-qd' },
            { text: 'Deployment', link: '/guide/deployment' },
            { text: 'How to Use?', link: '/guide/how-to-use' },
            { text: 'Update', link: '/guide/update' },
            { text: 'FAQ', link: '/guide/faq' },
        ]
    }
  ]
}
