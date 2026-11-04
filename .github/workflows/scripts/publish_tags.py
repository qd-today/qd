#!/usr/bin/env python3
"""算出这一轮要写哪些 tag。

用法：
  python3 publish_tags.py --is-tag true --version 20261104 \
      --a-prefix ""     --a-tag latest \
      --b-prefix "lite-" --b-tag latest \
      --registries "ghcr.io/qd-today/qd docker.io/qdtoday/qd docker.io/a76yyyy/qiandao"

规则（标签归属，两族互斥）：
  master 推送 → 只推进 dev：<a-prefix>dev / <b-prefix>dev
  tag 推送    → 只写 latest 与版本号：
                <a-prefix>latest / <a-prefix><版本> / <b-prefix>latest / <b-prefix><版本>

输出两行：
  A_TAGS=...   变体 A 的 tag（空格分隔）
  B_TAGS=...   变体 B 的 tag
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-tag", choices=["true", "false"], required=True)
    ap.add_argument("--version", default="")
    ap.add_argument("--a-prefix", default="")
    ap.add_argument("--a-tag", default="latest", help="基础 tag 名，前缀由 --a-prefix 提供")
    ap.add_argument("--b-prefix", default="")
    ap.add_argument("--b-tag", default="latest", help="基础 tag 名，前缀由 --b-prefix 提供")
    ap.add_argument("--registries", required=True)
    args = ap.parse_args()

    if args.is_tag == "true":
        if not args.version:
            sys.exit("::error::tag 推送必须给出版本号")
        a_tags = [args.a_prefix + args.a_tag, args.a_prefix + args.version]
        b_tags = [args.b_prefix + args.b_tag, args.b_prefix + args.version]
    else:
        a_tags = [args.a_prefix + "dev"]
        b_tags = [args.b_prefix + "dev"]

    # 值里有空格，必须加引号：脚本的输出被 shell 用 eval 读取，
    # 不加引号会被当成多条命令（bash: xxx: No such file or directory）
    print(f'A_TAGS="{" ".join(a_tags)}"')
    print(f'B_TAGS="{" ".join(b_tags)}"')
    print(f'REGISTRIES="{args.registries}"')


if __name__ == "__main__":
    main()
