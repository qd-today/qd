#!/usr/bin/env python3
"""根据平台输入生成构建矩阵与冒烟矩阵。

由 _image.yml 的 plan job 调用，环境变量：
  DEFAULT_PLATFORMS  该变体的默认平台集合（逗号分隔）
  PLATFORM_INPUT     调用方指定的平台子集（空 = 用 default）

输出（stdout，每行 key=value，直接追加到 $GITHUB_OUTPUT）：
  matrix        构建矩阵（每个架构组一项，含 group / runner / platforms）
  smoke_matrix  冒烟矩阵（每平台一项，runner 与构建时一致）
  expected      本次选中的平台全集
  groups        本次参与构建的组名（逗号分隔），供 merge job 组装 digest 清单
  full          是否等于该变体的默认全集（决定能否发布）
"""
import json, os, sys

default = [p.strip() for p in os.environ["DEFAULT_PLATFORMS"].split(",") if p.strip()]
raw = (os.environ.get("PLATFORM_INPUT") or "").strip()
plats = [p.strip() for p in raw.split(",") if p.strip()] if raw else default

allowed = {"linux/amd64", "linux/386", "linux/arm64", "linux/arm/v7",
           "linux/arm/v6", "linux/ppc64le", "linux/riscv64", "linux/s390x",
           "linux/loong64"}
bad = [p for p in plats if p not in allowed]
if bad:
    sys.exit("::error::未知平台: %s（可选: %s）" % (",".join(bad), ",".join(sorted(allowed))))

# 分组只影响并行度与缓存 scope，全部走 ubuntu-latest + QEMU：arm 三兄弟在原生
# arm64 runner 上会用内核 compat 模式，uv 在那里装 wheel 会卡住。
# 各组独立成 job 并行构建；合并成一组会让 QEMU 平台串行累加。
# 分组粒度还决定 merge 时能否按组挑选：386 与 arm/v6 只由 lite 线构建（它们没有
# OCR 的 wheelhouse），必须各自成组，否则会和 amd64 / arm64 混进同一个 digest。
GROUPS = [

    ("x86",     "ubuntu-latest", ["linux/amd64"]),

    ("x86-32",  "ubuntu-latest", ["linux/386"]),

    # arm 三兄弟都走 x86_64 + QEMU，不用原生 arm64 runner：qd 的 build 阶段是
    # 用 uv 装 wheel（runtime 行为），而 arm64 runner 上 32 位 ARM 容器走内核
    # compat 模式，uv 在那种环境里会卡住。三仓里只有 pycurl 的 wheel 阶段
    # （编译）用 arm_runner，它的 runtime 阶段同样统一 x86_64，理由相同。
    ("arm",     "ubuntu-latest", ["linux/arm64", "linux/arm/v7"]),

    ("armv6",   "ubuntu-latest", ["linux/arm/v6"]),
    ("ppc64le", "ubuntu-latest", ["linux/ppc64le"]),
    ("s390x",   "ubuntu-latest", ["linux/s390x"]),
    ("riscv64", "ubuntu-latest", ["linux/riscv64"]),
    ("loong64", "ubuntu-latest", ["linux/loong64"]),
]
include = []
for name, runner, group_plats in GROUPS:
    sel = [p for p in group_plats if p in plats]
    if sel:
        include.append({"group": name, "runner": runner, "platforms": ",".join(sel)})
if not include:
    sys.exit("::error::没有可构建的平台")

# 平台 → 组 的映射从 GROUPS 推导，不再手抄一份：
# 之前这里独立维护，改 GROUPS（把 386 拆成 x86-32）时漏改，
# smoke 的 group 名与缓存 scope 就对不上了。
GROUP_OF = {p: name for name, _runner, plats in GROUPS for p in plats}
smoke = []
for p in plats:
    smoke.append({
        "platform": p,
        "group": GROUP_OF[p],
        "runner": {p2: r2 for _n2, r2, ps2 in GROUPS for p2 in ps2}[p],
    })

print("matrix=" + json.dumps({"include": include}))
print("smoke_matrix=" + json.dumps({"include": smoke}))
print("expected=" + ",".join(sorted(plats)))
# 实际参与构建的组 → 平台列表；merge job 据此组装，不再在 workflow 里硬编码组名
print("groups=" + ",".join(g["group"] for g in include))
print("full=%s" % str(sorted(plats) == sorted(default)).lower())
