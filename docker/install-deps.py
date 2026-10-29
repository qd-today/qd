#!/usr/bin/env python3
"""从 uv.lock 导出的清单里剔除「基座镜像已经提供」的包。

为什么需要这一步：基座（a76yyyy/pycurl）里有自编的 pycurl（带 curl-impersonate 补丁）、
自编的 Pillow（无 libimagequant）、源码安装的 ddddocr，以及 apk 提供的 numpy /
onnxruntime / OpenCV。这些包在 PyPI 上也有，uv.lock 里同样钉了版本——直接照单安装
会把基座里的版本覆盖成 PyPI 版：ja3 的 IMPERSONATE 会丢，Pillow 会重新链上 GPL-3 的
libimagequant，onnxruntime 在多数架构上根本没有 musllinux 轮子会直接编译失败。

判断「已提供」用两个信号，缺一不可：
  1) importlib.metadata 里有对应发行包（pip 装的）
  2) 顶层模块能 import（apk 装的 cv2、无 dist 元数据的包）

第二个信号必须存在：基座的 OpenCV 是 apk 提供的，importlib.metadata 里查不到，
只靠第 1 条会把 opencv-python 当成缺失，从而去 PyPI 拉一个不存在的 musllinux 轮子。

还有一层传递处理：只被「已跳过」的包依赖的包也一并跳过。基座的 onnxruntime 1.24.4
是自洽的，但 uv.lock 解析出的是 1.31.1，会带出 protobuf —— 装上去没有任何消费者，
在部分架构还会编译失败。所以只要一个包的依赖来源全在被跳过集合里，它也不装。

用法：
  install-deps.py <requirements> [--write-manifest <路径>]   构建期：现场探测基座提供了什么，
                                                             并把该清单落盘
  install-deps.py <requirements> --base-manifest <路径>      运行期：只按落盘清单跳过

为什么运行期不能现场探测：`update.sh` 在已经装好依赖的容器里跑，此时 aiohttp 这类
我们自己装的包也「能 import」了，现场探测会把它们全判成基座提供的 —— 锁里升级了版本
也不会被装上。所以构建期算一次、落盘，运行期只认这份清单。
"""

import importlib
import importlib.metadata as metadata
import re
import sys

# 发行包名与顶层模块名不一致的映射；未列出的按「- 换 _」猜测
MODULE_ALIAS = {
    "opencv-python": "cv2",
    "opencv-python-headless": "cv2",
    "pillow": "PIL",
    "python-dateutil": "dateutil",
    "u-msgpack-python": "umsgpack",
    "pycryptodome": "Crypto",
    "pyyaml": "yaml",
    "beautifulsoup4": "bs4",
}


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def provided_by_base(name, dists):
    if normalize(name) in dists:
        return True
    module = MODULE_ALIAS.get(normalize(name), normalize(name).replace("-", "_"))
    try:
        importlib.import_module(module)
    except Exception:
        return False
    return True


def requirement_name(line):
    # 形如 "aiohttp==3.14.5" / "sqlalchemy[asyncio]==1.4.54" / "x==1.0; sys_platform == 'win32'"
    return re.split(r"[=<>!~\[;(@ ]", line.strip(), maxsplit=1)[0]


def parse_export(path):
    """把 uv export 的产物解析成 [(name, 需求行, [via...])]。

    uv 的格式是「需求行 + 缩进的注释」：
        aiohttp==3.14.5
            # via qd
        markupsafe==3.0.4
            # via
            #   jinja2
            #   qd
    """
    packages = []
    current = None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            text = line.strip().lstrip("#").strip()
            if current is None:
                continue
            if text.startswith("via"):
                rest = text[3:].strip()
                if rest:
                    current[2].append(rest)
            elif current[2] is not None and text:
                # 「# via」换行后的续行（纯名字）
                current[2].append(text)
            continue
        name = requirement_name(line)
        current = [name, line.strip(), []]
        packages.append(current)
    return packages


def read_manifest(path):
    names = set()
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return names


def main(path, write_manifest=None, base_manifest=None):
    packages = parse_export(path)

    if base_manifest:
        known = {normalize(n) for n in read_manifest(base_manifest)}
        skipped = {name for name, _, _ in packages if normalize(name) in known}
    else:
        dists = {
            normalize(d.metadata["Name"])
            for d in metadata.distributions()
            if d.metadata["Name"]
        }
        skipped = {name for name, _, _ in packages if provided_by_base(name, dists)}

    # 传递闭包：只被「已跳过」的包依赖的，也跳过（直到不再变化）
    changed = True
    while changed:
        changed = False
        for name, _, vias in packages:
            if name in skipped:
                continue
            # 直接依赖（via 里出现 qd）不参与传递跳过
            if not vias or "qd" in vias:
                continue
            if all(normalize(v) in {normalize(s) for s in skipped} for v in vias):
                skipped.add(name)
                changed = True

    kept = [(n, l) for n, l, _ in packages if n not in skipped]

    print("跳过 %d 个（基座已提供或只服务于它们）: %s"
          % (len(skipped), ", ".join(sorted(skipped))), file=sys.stderr)
    print("由 uv 安装 %d 个: %s"
          % (len(kept), ", ".join(sorted(n for n, _ in kept))), file=sys.stderr)

    if write_manifest:
        with open(write_manifest, "w", encoding="utf-8") as fh:
            for name in sorted(skipped):
                print(name, file=fh)
        print("基座清单已写入 %s（%d 个）" % (write_manifest, len(skipped)), file=sys.stderr)

    for _, line in kept:
        print(line)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("requirements")
    ap.add_argument("--write-manifest", metavar="路径")
    ap.add_argument("--base-manifest", metavar="路径")
    args = ap.parse_args()
    main(args.requirements, args.write_manifest, args.base_manifest)
