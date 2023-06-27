import { createRequire } from "module";
import { defineConfig } from "vitepress";

const require = createRequire(import.meta.url);
const pkg = require("vitepress/package.json");

export default defineConfig({
  lang: "en-US",
  description: "A web framework for HTTP timed task automation.",

  themeConfig: {
    nav: nav(),

    logo: "/logo.png",

    lastUpdatedText: "last Updated",

    sidebar: {
      "/guide/": sidebarGuide(),
      "/toolbox/": sidebarGuide(),
    },

    socialLinks: [
      { icon: "github", link: "https://github.com/qd-today/qd" },
      {
        icon: {
          svg: '<svg t="1676552188859" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2069" width="200" height="200"><path d="M512 1024C230.4 1024 0 793.6 0 512S230.4 0 512 0s512 230.4 512 512-230.4 512-512 512z m259.2-569.6H480c-12.8 0-25.6 12.8-25.6 25.6v64c0 12.8 12.8 25.6 25.6 25.6h176c12.8 0 25.6 12.8 25.6 25.6v12.8c0 41.6-35.2 76.8-76.8 76.8h-240c-12.8 0-25.6-12.8-25.6-25.6V416c0-41.6 35.2-76.8 76.8-76.8h355.2c12.8 0 25.6-12.8 25.6-25.6v-64c0-12.8-12.8-25.6-25.6-25.6H416c-105.6 0-188.8 86.4-188.8 188.8V768c0 12.8 12.8 25.6 25.6 25.6h374.4c92.8 0 169.6-76.8 169.6-169.6v-144c0-12.8-12.8-25.6-25.6-25.6z" fill="#888888" p-id="2070"></path></svg>',
        },
        link: "https://gitee.com/qd-today/qd",
      },
    ],

    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2023-present QD Developers",
    },

    editLink: {
      pattern: "https://github.com/qd-today/qd/edit/master/web/docs/:path",
      text: "Edit this page on GitHub",
    },

    outline: {
      label: "On this page",
      level: [2, 3],
    },
  },
});

function nav() {
  return [
    { text: "Guide", link: "/guide/what-is-qd" },
    { text: "ToolBox", link: "/toolbox/pusher" },
];
}

function sidebarGuide() {
  return [
    {
      text: "Guide",
      items: [
        { text: "What is QD?", link: "/guide/what-is-qd" },
        { text: "Deployment", link: "/guide/deployment" },
        { text: "How to Use?", link: "/guide/how-to-use" },
        { text: "Update", link: "/guide/update" },
        { text: "FAQ", link: "/guide/faq" },
      ],
    },
    {
      text: "ToolBox",
      items: [{ text: "Pusher", link: "/toolbox/pusher" }],
    },
  ];
}
