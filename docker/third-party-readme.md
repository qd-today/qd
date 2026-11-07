# 第三方许可证文书（qd 镜像）

每个子目录对应一个 wheelhouse 组件仓，内容由该仓构建时的 `pack_wheel.py --compliance`
从 wheel 里实测生成，不是手工维护的清单：

| 文件 | 内容 |
| --- | --- |
| `NOTICE.md` | 随包组件、版本、许可证结论 |
| `SOURCE-OFFER.md` | copyleft 组件的源码获取途径 |
| `licenses/` | 许可证全文（LGPL / GPL 等），**只有含 copyleft 组件的仓才有此目录** |
| `components.json` | 机器可读的完整清单（含 `selfBuilt` 与 apk 出处） |

## 为什么这些文书在组件仓里生成

auditwheel 会把原生依赖收进 wheel 的 `.libs/`，这些库在 Python 依赖图里完全不可见——
`pip` / `uv.lock` / FOSSA 的 autobuild 都看不到它们。所以由生产这些 wheel 的仓在构建时
实测扫描，生成上述文书，再由本镜像原样随附。

## 范围（分层承担）

合规检查分两层，合起来才是完整视图：

- **本仓库（qd）**：FOSSA 项目是 autobuild，覆盖 `pyproject.toml` / `uv.lock` 这一层
  Python 依赖。
- **三个组件仓**（[onnxruntime](https://github.com/qd-today/onnxruntime-docker)、
  [ddddocr](https://github.com/qd-today/ddddocr-docker)、
  [pycurl](https://github.com/qd-today/pycurl-docker)）：负责 wheel 内随包的原生库。

分发义务以本目录随附的文书为准。
