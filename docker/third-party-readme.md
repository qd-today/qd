# 第三方许可证文书（qd 镜像）

每个子目录对应一个 wheelhouse 组件仓，内容由该仓构建时的 `pack_wheel.py --compliance`
从 wheel 里实测生成，不是手工维护的清单：

| 文件 | 内容 |
| --- | --- |
| `NOTICE.md` | 随包组件、版本、许可证结论 |
| `SOURCE-OFFER.md` | copyleft 组件的源码获取途径 |
| `licenses/` | 许可证全文（LGPL / GPL 等）；无 copyleft 组件的仓里放一份 `README.md` 说明情况 |
| `components.json` | 机器可读的完整清单（含 `selfBuilt` 与 apk 出处） |

## 为什么这些文书在组件仓里生成

auditwheel 会把原生依赖收进 wheel 的 `.libs/`，这些库不在 `uv.lock` 的依赖图里，
Python 包管理器看不到它们。所以由生产这些 wheel 的组件仓在构建时实测扫描并出具文书，
本镜像原样随附。

## 合规范围

qd 的 FOSSA 项目由 `fossa analyze` 上传，一个项目同时覆盖：

- `uv.lock` / `pnpm-lock.yaml` 的 Python 与前端依赖（CLI 自动发现）；
- 四个 Docker 变体随包分发的原生库（CI 汇总各 wheelhouse 的 `fossa-deps.yml` 后追加）。

## Python / 前端依赖的许可声明

这部分**不需要在本目录复制一份全文**：PEP 639 要求每个 wheel 把许可文本放进
`.dist-info/licenses/`，它们随包一起装进镜像，位于
`/usr/src/app/.venv/lib/python*/site-packages/<包>-*.dist-info/licenses/`。
本文件是这些声明的索引与判定说明。

需要留意的几条：

| 包 | 许可 | 处理 |
| --- | --- | --- |
| `certifi` | MPL-2.0 | 未修改任何文件，MPL-2.0 只需保留声明；包内 `licenses/LICENSE` 已随附 |
| `pycurl` | `LGPL-2.1-only OR MIT` | **本项目采用 MIT 条款**；包内 `COPYING-MIT` 与 `COPYING-LGPL` 均随附 |
| 其余 Python / 前端包 | MIT / MIT-CMU / Apache-2.0 | 上游声明与 FOSSA 元数据不一致的条目已在 FOSSA 中带理由 ignore |

源码获取途径：各包的 PyPI 项目页与上游仓库（`uv.lock` / `pnpm-lock.yaml` 锁定了精确版本），
也可在本仓库提 issue 索取与所分发二进制完全对应的源码。

完整的依赖清单、许可结论与逐条 ignore 理由见 FOSSA 项目 `custom+38165/qd`
（README 的 FOSSA badge 指向该项目）。

分发义务以本目录随附的文书及各 wheel 自带的 `.dist-info/licenses/` 为准。
