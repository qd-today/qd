<p align="center">
   <a href="https://github.com/qd-today/qd">
   <img style="border-radius:50%" width="150" src="https://fastly.jsdelivr.net/gh/qd-today/qd@master/web/static/img/icon.png">
   </a>
</p>

<h1 align="center">QD for Python3</h1>

<div align="center">
QD —— 一个<b>HTTP请求定时任务自动执行框架</b> base on HAR Editor and Tornado Server

[![HomePage][HomePage-image]][HomePage-url]
[![Github][Github-image]][Github-url]
[![Gitee][Gitee-image]][Gitee-url]
[![license][github-license-image]][github-license-url]
[![QQ频道][QQPD-image]][QQPD-url]
[![Build Image][workflow-image]][workflow-url]
[![last commit][last-commit-image]][last-commit-url]
[![commit activity][commit-activity-image]][commit-activity-url]
![repo size][repo-size-image]
[![docker version][docker-version-image]][docker-version-url]
[![docker pulls][docker-pulls-image]][docker-pulls-url]
[![docker stars][docker-stars-image]][docker-stars-url]
[![docker image size][docker-image-size-image]][docker-image-size-url]
![python version][python-version-image]
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-24-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[HomePage-image]: https://img.shields.io/badge/HomePage-QD--Today-brightgreen
[HomePage-url]: https://qd.a76yyyy.cn
[Github-image]: https://img.shields.io/static/v1?label=Github&message=QD&color=brightgreen
[Github-url]: https://github.com/qd-today/qd/
[Gitee-image]: https://img.shields.io/static/v1?label=Gitee&message=QD&color=brightgreen
[Gitee-url]: https://gitee.com/qd-today/qd/
[github-license-image]: https://img.shields.io/github/license/qd-today/qd
[github-license-url]: https://github.com/qd-today/qd/blob/master/LICENSE
[QQPD-image]: https://img.shields.io/static/v1?label=QQ%E9%A2%91%E9%81%93&message=QD&color=brightgreen
[QQPD-url]: https://pd.qq.com/s/g9qaiue25
[workflow-image]: https://github.com/qd-today/qd/actions/workflows/Publish%20Package.yml/badge.svg
[workflow-url]: https://github.com/qd-today/qd/actions/workflows/Publish%20Package.yml
[last-commit-image]: https://img.shields.io/github/last-commit/qd-today/qd
[last-commit-url]: https://github.com/qd-today/qd/
[commit-activity-image]: https://img.shields.io/github/commit-activity/m/qd-today/qd
[commit-activity-url]: https://github.com/qd-today/qd/
[repo-size-image]: https://img.shields.io/github/repo-size/qd-today/qd
[docker-version-image]: https://img.shields.io/docker/v/qdtoday/qd/latest?style=flat
[docker-version-url]: https://hub.docker.com/r/qdtoday/qd/tags?latest
[docker-pulls-image]: https://img.shields.io/docker/pulls/qdtoday/qd?style=flat
[docker-pulls-url]: https://hub.docker.com/r/qdtoday/qd
[docker-stars-image]: https://img.shields.io/docker/stars/qdtoday/qd?style=flat
[docker-stars-url]: https://hub.docker.com/r/qdtoday/qd
[docker-image-size-image]: https://img.shields.io/docker/image-size/qdtoday/qd/latest?style=flat&arch=amd64
[docker-image-size-url]: https://hub.docker.com/r/qdtoday/qd
[python-version-image]: https://img.shields.io/github/pipenv/locked/python-version/qd-today/qd

</div>

<p align="center">
   <img width="45%" style="border:solid 1px #DCEBFB" src="https://fastly.jsdelivr.net/gh/qd-today/qd@master/web/docs/public/login.png" >
   <img width="45%" style="border:solid 1px #DCEBFB" src="https://fastly.jsdelivr.net/gh/qd-today/qd@master/web/docs/public/index.png">
</p>

操作说明
==========

请参阅 **[使用指南](https://qd-today.github.io/qd/zh_CN/)**

镜像
==========

| 标签 | 说明 |
|---|---|
| `latest` | 完整功能，含验证码识别 |
| `lite-latest` | 精简版，不含验证码识别 |
| `ja3-latest` | 含验证码识别，pycurl 带 TLS 指纹伪装 |
| `ja3-lite-latest` | 精简 + TLS 指纹伪装 |

`386` / `arm/v6` / `s390x` 上没有可用的 OCR 依赖轮子：这三个架构上 `latest` 仍可拉取，
但对应平台的内容等同于 `lite-latest`（不含验证码识别）；`ja3-latest` 在 `386` / `arm/v6`
上等同于 `ja3-lite-latest`，在 `s390x` 上不提供。需要验证码识别请使用 `amd64` / `arm64` /
`arm/v7` / `ppc64le` / `riscv64` / `loong64`。部署方式与配置见
[使用指南](https://qd-today.github.io/qd/zh_CN/)。

更新日志
===========

详见 **[CHANGELOG.md](./CHANGELOG.md)**

维护项目精力有限, 仅保证对 Chrome 浏览器的支持。如果测试了其他浏览器可以 Pull Request。

许可
===========

[MIT](https://fastly.jsdelivr.net/gh/qd-today/qd@master/LICENSE) 许可协议

[![FOSSA Status](https://app.fossa.com/api/projects/custom%2B38165%2Fqd.svg?type=large)](https://app.fossa.com/projects/custom%2B38165%2Fqd?ref=badge_large)

容器镜像内随附第三方许可证文书，路径 `/usr/share/doc/third-party/`（每个组件仓一个子目录，
含 `NOTICE.md`、`SOURCE-OFFER.md`、`licenses/`、`components.json`）。

合规检查分两层承担：本仓库的 FOSSA 项目是 autobuild，覆盖 `pyproject.toml` / `uv.lock`
这一层 Python 依赖；wheel 里由 auditwheel 收集进来的原生库（libcurl、libidn2、OpenCV 等）
在 Python 依赖图中不可见，由生产这些 wheel 的三个组件仓
（[onnxruntime](https://github.com/qd-today/onnxruntime-docker)、
[ddddocr](https://github.com/qd-today/ddddocr-docker)、
[pycurl](https://github.com/qd-today/pycurl-docker)）各自扫描并出具文书。

致谢
===========

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="12.5%"><a href="http://www.a76yyyy.cn"><img src="https://avatars.githubusercontent.com/u/56478790?v=4?s=100" width="100px;" alt="a76yyyy"/><br /><sub><b>a76yyyy</b></sub></a><br /><a href="#design-a76yyyy" title="Design">🎨</a> <a href="https://github.com/qd-today/qd/commits?author=a76yyyy" title="Code">💻</a> <a href="#maintenance-a76yyyy" title="Maintenance">🚧</a> <a href="https://github.com/qd-today/qd/commits?author=a76yyyy" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="12.5%"><a href="http://binux.me/"><img src="https://avatars.githubusercontent.com/u/646451?v=4?s=100" width="100px;" alt="Roy Binux"/><br /><sub><b>Roy Binux</b></sub></a><br /><a href="#design-Binux" title="Design">🎨</a> <a href="https://github.com/qd-today/qd/commits?author=Binux" title="Code">💻</a> <a href="#maintenance-Binux" title="Maintenance">🚧</a> <a href="https://github.com/qd-today/qd/commits?author=Binux" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/AragonSnow"><img src="https://avatars.githubusercontent.com/u/22835918?v=4?s=100" width="100px;" alt="AragonSnow"/><br /><sub><b>AragonSnow</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=AragonSnow" title="Code">💻</a> <a href="#design-AragonSnow" title="Design">🎨</a> <a href="#maintenance-AragonSnow" title="Maintenance">🚧</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://www.quchao.net"><img src="https://avatars.githubusercontent.com/u/36469805?v=4?s=100" width="100px;" alt="Mark"/><br /><sub><b>Mark</b></sub></a><br /><a href="#design-Mark-1215" title="Design">🎨</a> <a href="#blog-Mark-1215" title="Blogposts">📝</a> <a href="https://github.com/qd-today/qd/commits?author=Mark-1215" title="Documentation">📖</a> <a href="#maintenance-Mark-1215" title="Maintenance">🚧</a> <a href="https://github.com/qd-today/qd/commits?author=Mark-1215" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/cdpidan"><img src="https://avatars.githubusercontent.com/u/8141453?v=4?s=100" width="100px;" alt="pidan"/><br /><sub><b>pidan</b></sub></a><br /><a href="#design-cdpidan" title="Design">🎨</a> <a href="https://github.com/qd-today/qd/commits?author=cdpidan" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://buzhibujue.cf"><img src="https://avatars.githubusercontent.com/u/24644841?v=4?s=100" width="100px;" alt="buzhibujue"/><br /><sub><b>buzhibujue</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=buzhibujuelb" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/billypon"><img src="https://avatars.githubusercontent.com/u/1763302?v=4?s=100" width="100px;" alt="billypon"/><br /><sub><b>billypon</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=billypon" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="http://www.lingyan8.com"><img src="https://avatars.githubusercontent.com/u/19186382?v=4?s=100" width="100px;" alt="acooler15"/><br /><sub><b>acooler15</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=acooler15" title="Code">💻</a> <a href="#maintenance-acooler15" title="Maintenance">🚧</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/aa889788"><img src="https://avatars.githubusercontent.com/u/16019986?v=4?s=100" width="100px;" alt="shxyke"/><br /><sub><b>shxyke</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=aa889788" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/gxitm"><img src="https://avatars.githubusercontent.com/u/2405087?v=4?s=100" width="100px;" alt="xiaoxiao"/><br /><sub><b>xiaoxiao</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=gxitm" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://blog.hicasper.com"><img src="https://avatars.githubusercontent.com/u/25276620?v=4?s=100" width="100px;" alt="Casper"/><br /><sub><b>Casper</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=caspershw" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/ckx000"><img src="https://avatars.githubusercontent.com/u/5800591?v=4?s=100" width="100px;" alt="旋子"/><br /><sub><b>旋子</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=ckx000" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/chen8945"><img src="https://avatars.githubusercontent.com/u/44148812?v=4?s=100" width="100px;" alt="chen8945"/><br /><sub><b>chen8945</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=chen8945" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/seiuneko"><img src="https://avatars.githubusercontent.com/u/25706824?v=4?s=100" width="100px;" alt="seiuneko"/><br /><sub><b>seiuneko</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=seiuneko" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/powersee"><img src="https://avatars.githubusercontent.com/u/38074760?v=4?s=100" width="100px;" alt="powersee"/><br /><sub><b>powersee</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=powersee" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/Cirn09"><img src="https://avatars.githubusercontent.com/u/25722111?v=4?s=100" width="100px;" alt="Cirn09"/><br /><sub><b>Cirn09</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=Cirn09" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/Ovler-Young"><img src="https://avatars.githubusercontent.com/u/44089074?v=4?s=100" width="100px;" alt="Ovler"/><br /><sub><b>Ovler</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=Ovler-Young" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://www.lshell.com"><img src="https://avatars.githubusercontent.com/u/676412?v=4?s=100" width="100px;" alt="An"/><br /><sub><b>An</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=Ansen" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/Siman8"><img src="https://avatars.githubusercontent.com/u/32073730?v=4?s=100" width="100px;" alt="Siman8"/><br /><sub><b>Siman8</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=Siman8" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/uiolee"><img src="https://avatars.githubusercontent.com/u/22849383?v=4?s=100" width="100px;" alt="Uiolee"/><br /><sub><b>Uiolee</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=uiolee" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/OwnerCM"><img src="https://avatars.githubusercontent.com/u/22722811?v=4?s=100" width="100px;" alt="OwnerCM"/><br /><sub><b>OwnerCM</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=OwnerCM" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/jionkitten"><img src="https://avatars.githubusercontent.com/u/30788097?v=4?s=100" width="100px;" alt="jionkitten"/><br /><sub><b>jionkitten</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=jionkitten" title="Code">💻</a></td>
      <td align="center" valign="top" width="12.5%"><a href="https://github.com/Patrick-Ze"><img src="https://avatars.githubusercontent.com/u/19711799?v=4?s=100" width="100px;" alt="Patrick-Ze"/><br /><sub><b>Patrick-Ze</b></sub></a><br /><a href="https://github.com/qd-today/qd/commits?author=Patrick-Ze" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

Stargazers over time
===========

[![Stargazers over time](https://starchart.cc/qd-today/qd.svg)](https://starchart.cc/qd-today/qd)
