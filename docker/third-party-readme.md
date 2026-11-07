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

分发义务以本目录随附的文书为准。
