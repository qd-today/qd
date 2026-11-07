#!/usr/bin/env python3
"""把多个 wheelhouse 的 fossa-deps.yml 合并成一份，写到仓库根目录。

CI 在 `fossa analyze .` 之前运行本脚本：CLI 默认读取项目根目录的 fossa-deps.yml，
并把它里面的依赖**追加**到自动发现的依赖（uv.lock / pnpm-lock.yaml）之上。

输入是各组件仓在构建时由 compliance.py 生成、并随 wheelhouse 镜像发布的
fossa-deps.yml。主线与 ja3 线随包的原生库不同，所以两线都取、按并集合并。
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

KINDS = (
    "referenced-dependencies",
    "custom-dependencies",
    "remote-dependencies",
    "vendored-dependencies",
)

HEADER = """# 由 .github/workflows/scripts/merge-fossa-deps.py 在 CI 中生成，不要手改、不要提交。
#
# 来源：qd 的 Dockerfile 里钉住的四个 wheelhouse 镜像各自随附的 fossa-deps.yml
# （onnxruntime / ddddocr / pycurl 主线 / pycurl ja3），按类型+名称+版本+架构去重取并集。
# 这些是 auditwheel 收进 wheel 的原生库，uv.lock 的依赖图里看不到；fossa analyze .
# 会把本文件的内容追加到自动扫描结果之上。
"""


def dedup_key(kind, item):
    if kind == "referenced-dependencies":
        return tuple(item.get(k) for k in
                     ("type", "name", "version", "arch", "os", "osVersion"))
    if kind == "custom-dependencies":
        return tuple(item.get(k) for k in ("name", "version", "license"))
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def sort_key(kind, item):
    return (str(item.get("name") or ""), str(item.get("version") or ""),
            str(item.get("arch") or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="各 wheelhouse 导出的 fossa-deps.yml")
    ap.add_argument("--output", default="fossa-deps.yml")
    args = ap.parse_args()

    merged = {k: {} for k in KINDS}
    for raw in args.inputs:
        p = Path(raw)
        if not p.is_file():
            print(f"::error::缺少输入文件 {p}", file=sys.stderr)
            return 1
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        counts = []
        for kind in KINDS:
            items = doc.get(kind) or []
            if not isinstance(items, list):
                print(f"::error::{p} 的 {kind} 不是列表", file=sys.stderr)
                return 1
            for item in items:
                if isinstance(item, dict):
                    merged[kind].setdefault(dedup_key(kind, item), item)
            counts.append(f"{kind}={len(items)}")
        print(f"{p.name}: " + " ".join(counts))

    out = {}
    for kind in KINDS:
        items = sorted(merged[kind].values(), key=lambda i, k=kind: sort_key(k, i))
        if items:
            out[kind] = items
            print(f"合并后 {kind}={len(items)}")

    if not out:
        print("::error::合并结果为空，wheelhouse 的 fossa-deps.yml 可能都没生成",
              file=sys.stderr)
        return 1

    Path(args.output).write_text(
        HEADER + "\n" + yaml.safe_dump(out, sort_keys=False, allow_unicode=True,
                                       default_flow_style=False, width=120),
        encoding="utf-8",
    )
    print(f"已写出 {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
