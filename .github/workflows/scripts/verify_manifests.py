#!/usr/bin/env python3
"""校验一个或多个镜像 tag 的平台集合是否与预期一致。

用法：
  python3 verify_manifests.py --expect "linux/amd64,linux/arm64,..." TAG [TAG ...]

TAG 可以是 registry/repo:tag 形式。任一 tag 不存在或平台集合不符即退出码 1。
"""
import argparse
import json
import subprocess
import sys


def platforms_of(ref):
    """读取 manifest index 里的平台列表；ref 不存在时抛 CalledProcessError。"""
    out = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", ref, "--raw"],
        capture_output=True, text=True, check=True,
    ).stdout
    got = set()
    for m in json.loads(out).get("manifests", []):
        p = m.get("platform") or {}
        if not p:
            continue
        arch, variant = p.get("architecture"), p.get("variant")
        got.add("linux/" + arch + (("/" + variant) if variant else ""))
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", required=True, help="逗号分隔的平台列表")
    ap.add_argument("refs", nargs="+", help="要校验的镜像引用")
    args = ap.parse_args()

    expect = {p.strip() for p in args.expect.split(",") if p.strip()}
    failed = False

    for ref in args.refs:
        try:
            got = platforms_of(ref)
        except subprocess.CalledProcessError:
            print(f"::error::{ref} 不存在或无法读取")
            failed = True
            continue
        missing, extra = expect - got, got - expect
        if missing or extra:
            print(f"::error::{ref} 平台集合不一致：缺 {missing or '无'}，多 {extra or '无'}")
            failed = True
        else:
            print(f"{ref} 平台集合一致（{len(got)} 个）")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
