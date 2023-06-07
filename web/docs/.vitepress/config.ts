import { createRequire } from "module";
import { defineConfig } from "vitepress";
import locales from "./locales";

const require = createRequire(import.meta.url);
const pkg = require("vitepress/package.json");

export default defineConfig({
  title: "QD",
  locales: locales.locales,
  base: "/qd/",
  head: [["link", { rel: "icon", href: "/qd/favicon.ico" }]],
  themeConfig: {
    search: {
      provider: "local",
      options: {
        locales: {
          zh_CN: {
            translations: {
              button: {
                buttonText: "搜索文档",
                buttonAriaLabel: "搜索文档",
              },
              modal: {
                noResultsText: "无法找到相关结果",
                resetButtonTitle: "清除查询条件",
                footer: {
                  selectText: "选择",
                  navigateText: "切换",
                },
              },
            },
          },
        },
      },
    },
  },
});
