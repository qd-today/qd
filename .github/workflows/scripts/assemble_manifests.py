#!/usr/bin/env python3
"""把两批构建产出的 digest 组装成 manifest 来源清单。

用法：
  python3 assemble_manifests.py \
      --main-variant latest --lite-variant lite \
      --main-groups "x86,arm,ppc64le,riscv64,loong64" \
      --lite-groups "x86,x86-32,arm,armv6,ppc64le,riscv64,s390x,loong64" \
      --digest-root /tmp/d --image ghcr.io/qd-today/qd \
      --out /tmp/srcs

digest 从 <digest-root>/<variant>/digests-<variant>-<group>/<group>.digest 读，
这是 actions/download-artifact 按 pattern 解包后的目录结构。

输出两个文件：
  <out>-<main>.txt   主线内容 + lite 补位的组
  <out>-lite.txt     lite 的全部组
每行一个「registry/repo@digest」，可直接喂给 docker buildx imagetools create。
"""
import argparse
import os
import sys


def read_digest(root, variant, group):
    path = os.path.join(root, variant, f"digests-{variant}-{group}", f"{group}.digest")
    if not os.path.isfile(path):
        sys.exit(f"::error::缺少 digest 文件: {path}")
    with open(path) as fh:
        value = fh.read().strip()
    if not value.startswith("sha256:"):
        sys.exit(f"::error::digest 内容异常: {path} -> {value!r}")
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main-variant", required=True)
    ap.add_argument("--lite-variant", required=True)
    ap.add_argument("--main-groups", required=True, help="主线变体参与的组，逗号分隔")
    ap.add_argument("--lite-groups", required=True, help="lite 变体参与的组，逗号分隔")
    ap.add_argument("--digest-root", required=True)
    ap.add_argument("--image", required=True, help="来源镜像前缀")
    ap.add_argument("--out", required=True, help="输出文件前缀")
    args = ap.parse_args()

    main_groups = [g.strip() for g in args.main_groups.split(",") if g.strip()]
    lite_groups = [g.strip() for g in args.lite_groups.split(",") if g.strip()]
    lite_only = [g for g in lite_groups if g not in main_groups]

    print(f"main 组: {','.join(main_groups)}")
    print(f"lite 组: {','.join(lite_groups)}")
    print(f"lite 补位: {','.join(lite_only)}")

    def sources(variant, groups):
        return " ".join(
            f"{args.image}@{read_digest(args.digest_root, variant, g)}" for g in groups
        )

    main_src = f"{sources(args.main_variant, main_groups)} {sources(args.lite_variant, lite_only)}"
    lite_src = sources(args.lite_variant, lite_groups)

    for name, content in ((args.main_variant, main_src), (args.lite_variant, lite_src)):
        path = f"{args.out}-{name}.txt"
        with open(path, "w") as fh:
            fh.write(content + "\n")
        n = len(content.split())
        print(f"{path}: {n} 个来源")
        print(f"  {content}")


if __name__ == "__main__":
    main()
