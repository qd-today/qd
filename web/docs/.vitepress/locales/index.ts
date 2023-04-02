import { defineConfig } from 'vitepress'
import en_US from './en_US'
import zh_CN from './zh_CN'

export default defineConfig({
  locales: {
    root: {
      label: 'English',
      lang: en_US.lang,
      themeConfig: en_US.themeConfig,
      description: en_US.description
    },
    zh_CN: {
      label: '简体中文',
      lang: zh_CN.lang,
      themeConfig: zh_CN.themeConfig,
      description: zh_CN.description
    }
  }
})