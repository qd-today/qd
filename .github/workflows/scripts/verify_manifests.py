#!/usr/bin/env python3
"""校验镜像 tag 的平台集合，以及 index 引用的每个子清单是否真的能取到。

用法：
  python3 verify_manifests.py --expect "linux/amd64,linux/arm64,..." TAG [TAG ...]

TAG 可以是 registry/repo:tag 形式。任一 tag 不存在、平台集合不符、
或 index 里的子清单读不出来（MANIFEST_UNKNOWN / 404）即退出码 1。

为什么必须逐个取子清单：imagetools inspect <tag> --raw 只返回 index 本身，
index 里列了哪些平台，不代表那些 manifest 还在注册表里。GHCR 上出现过
tagged index 还在、所有 child 被清理掉的空壳 tag（issue #642）——
只读平台列表会给出「校验通过」的假绿，用户 docker pull 才撞上 404。
"""
import argparse
import json
import subprocess
import sys


def index_of(ref):
    """读取 manifest index；ref 不存在时抛 CalledProcessError。"""
    out = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", ref, "--raw"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def platforms_of(index):
    got = set()
    for m in index.get("manifests", []):
        p = m.get("platform") or {}
        if not p:
            continue
        arch, variant = p.get("architecture"), p.get("variant")
        got.add("linux/" + arch + (("/" + variant) if variant else ""))
    return got


def repo_of(ref):
    """ghcr.io/qd-today/qd:latest -> ghcr.io/qd-today/qd（保留 registry 的端口）。"""
    base = ref.split("@", 1)[0]
    head, sep, tail = base.rpartition("/")
    if ":" in tail:
        base = (head + sep if sep else "") + tail.rsplit(":", 1)[0]
    return base


def missing_children(ref, index):
    """逐个取 index 里的子清单，返回读不出来的 digest 列表。"""
    repo = repo_of(ref)
    bad = []
    for m in index.get("manifests", []):
        digest = m.get("digest")
        if not digest:
            continue
        try:
            subprocess.run(
                ["docker", "buildx", "imagetools", "inspect",
                 f"{repo}@{digest}", "--raw"],
                capture_output=True, text=True, check=True,
            )
        except subprocess.CalledProcessError:
            bad.append(digest)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", required=True, help="逗号分隔的平台列表")
    ap.add_argument("refs", nargs="+", help="要校验的镜像引用")
    args = ap.parse_args()

    expect = {p.strip() for p in args.expect.split(",") if p.strip()}
    failed = False

    for ref in args.refs:
        try:
            index = index_of(ref)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            print(f"::error::{ref} 不存在或无法读取")
            failed = True
            continue

        total = len(index.get("manifests", []))

        got = platforms_of(index)
        missing, extra = expect - got, got - expect
        if missing or extra:
            print(f"::error::{ref} 平台集合不一致：缺 {missing or '无'}，多 {extra or '无'}")
            failed = True
        else:
            print(f"{ref} 平台集合一致（{len(got)} 个）")

        bad = missing_children(ref, index)
        if bad:
            print(f"::error::{ref} 有 {len(bad)}/{total} 个子清单读不出来"
                  f"（index 是空壳，docker pull 会失败）：" + ", ".join(bad))
            failed = True
        else:
            print(f"{ref} 子清单可读取（{total} 个）")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
