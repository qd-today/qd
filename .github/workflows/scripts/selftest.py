#!/usr/bin/env python3
"""CI 脚本的本地自测：不依赖网络与 Docker。

跑法：python3 .github/workflows/scripts/selftest.py

三部分：
  1. assemble_manifests 的组装逻辑（假 digest，临时目录）
  2. plan.py 的输出键（必须是 matrix / smoke_matrix / expected / groups / full）
  3. workflow 的静态一致性检查
     —— plan job 必须声明 groups 输出；调用方 env 的变量名必须与脚本引用一致
        （这两处都曾因为「改了一半」导致 merge 在 CI 里拿到空值）
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(HERE, "..")
FAILURES = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(label)


def fake_digest(group):
    return "sha256:" + (group * 64)[:64]


def make_digests(root, variant, groups):
    for g in groups:
        d = os.path.join(root, variant, f"digests-{variant}-{g}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{g}.digest"), "w") as fh:
            fh.write(fake_digest(g) + "\n")


def test_assemble():
    print("assemble_manifests:")
    root = tempfile.mkdtemp()
    try:
        main_groups = ["x86", "arm", "ppc64le"]
        lite_groups = ["x86", "x86-32", "arm", "armv6", "ppc64le", "s390x"]
        make_digests(root, "latest", main_groups)
        make_digests(root, "lite", lite_groups)

        out = os.path.join(root, "srcs")
        rc = subprocess.run(
            [sys.executable, os.path.join(HERE, "assemble_manifests.py"),
             "--main-variant", "latest", "--lite-variant", "lite",
             "--main-groups", ",".join(main_groups),
             "--lite-groups", ",".join(lite_groups),
             "--digest-root", root, "--image", "ghcr.io/qd-today/qd",
             "--out", out],
            capture_output=True, text=True,
        )
        check("退出码为 0", rc.returncode == 0, rc.stderr.strip()[-200:])
        if rc.returncode != 0:
            return

        with open(f"{out}-latest.txt") as fh:
            latest = fh.read().split()
        with open(f"{out}-lite.txt") as fh:
            lite = fh.read().split()

        expect_latest = [fake_digest(g) for g in ("x86", "arm", "ppc64le", "x86-32", "armv6", "s390x")]
        expect_lite = [fake_digest(g) for g in lite_groups]

        check("latest 的来源数 = main 组 + lite 补位 = 6", len(latest) == 6, f"实际 {len(latest)}")
        check("lite 的来源数 = lite 组数 = 6", len(lite) == 6, f"实际 {len(lite)}")
        check("latest 的来源集合正确（补位组取自 lite）",
              sorted(latest) == sorted(f"ghcr.io/qd-today/qd@{d}" for d in expect_latest))
        check("lite 的来源集合正确",
              sorted(lite) == sorted(f"ghcr.io/qd-today/qd@{d}" for d in expect_lite))
        check("来源无重复", len(set(latest)) == len(latest) and len(set(lite)) == len(lite))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_missing_digest():
    print("assemble_manifests 缺 digest 时应报错:")
    root = tempfile.mkdtemp()
    try:
        rc = subprocess.run(
            [sys.executable, os.path.join(HERE, "assemble_manifests.py"),
             "--main-variant", "latest", "--lite-variant", "lite",
             "--main-groups", "x86", "--lite-groups", "x86",
             "--digest-root", root, "--image", "ghcr.io/qd-today/qd",
             "--out", os.path.join(root, "srcs")],
            capture_output=True, text=True,
        )
        check("退出码非 0", rc.returncode != 0, f"实际 {rc.returncode}")
        check("错误信息里指出缺失文件", "缺少 digest" in (rc.stdout + rc.stderr))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_plan_output_keys():
    print("plan.py 的输出键:")
    env = {"DEFAULT_PLATFORMS": "linux/amd64,linux/arm64,linux/arm/v7", "PLATFORM_INPUT": ""}
    rc = subprocess.run(
        [sys.executable, os.path.join(HERE, "plan.py")],
        capture_output=True, text=True, env={**os.environ, **env},
    )
    check("退出码为 0", rc.returncode == 0, rc.stderr.strip()[-200:])
    keys = {line.split("=", 1)[0] for line in rc.stdout.splitlines() if "=" in line}
    for k in ("matrix", "smoke_matrix", "expected", "groups", "full"):
        check(f"输出含 {k}", k in keys, f"实际 {sorted(keys)}")
    groups = next((l.split("=", 1)[1] for l in rc.stdout.splitlines() if l.startswith("groups=")), "")
    check("groups 是逗号分隔的组名", groups and " " not in groups, f"实际 {groups!r}")


def test_publish_tags():
    print("publish_tags.py 的标签分配:")
    script = os.path.join(HERE, "publish_tags.py")

    def run(*args):
        rc = subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
        assert rc.returncode == 0, rc.stderr
        out = {}
        for line in rc.stdout.splitlines():
            k, _, v = line.partition("=")
            # 值必须带引号，否则 eval 时含空格的值会被当成多条命令
            check(f"{k} 的值带引号", v.startswith('"') and v.endswith('"'), f"实际 {v!r}")
            out.setdefault(k, []).extend(v.strip('"').split())
        return out

    reg = "ghcr.io/qd-today/qd docker.io/qdtoday/qd docker.io/a76yyyy/qiandao"

    # master 推送：只推进 dev
    o = run("--is-tag", "false", "--version", "", "--a-prefix", "", "--a-tag", "latest",
            "--b-prefix", "lite-", "--b-tag", "latest", "--registries", reg)
    check("master 只写 dev", o["A_TAGS"] == ["dev"] and o["B_TAGS"] == ["lite-dev"],
          f"{o['A_TAGS']} / {o['B_TAGS']}")
    check("master 不写 latest", "latest" not in o["A_TAGS"] and "latest" not in o["B_TAGS"])

    # tag 推送：写 latest 与版本号，不写 dev
    o = run("--is-tag", "true", "--version", "20261104", "--a-prefix", "ja3-", "--a-tag", "latest",
            "--b-prefix", "ja3-lite-", "--b-tag", "latest", "--registries", reg)
    check("tag 写 ja3-latest 与版本号",
          o["A_TAGS"] == ["ja3-latest", "ja3-20261104"], f"{o['A_TAGS']}")
    check("tag 写 ja3-lite-latest 与版本号",
          o["B_TAGS"] == ["ja3-lite-latest", "ja3-lite-20261104"], f"{o['B_TAGS']}")
    check("tag 不写 dev", "dev" not in " ".join(o["A_TAGS"] + o["B_TAGS"]))
    check("前缀不重复", not any(t.count("ja3-") > 1 for t in o["A_TAGS"] + o["B_TAGS"]),
          f"{o['A_TAGS'] + o['B_TAGS']}")

    # tag 推送必须给版本号
    rc = subprocess.run([sys.executable, script, "--is-tag", "true", "--version", "",
                         "--a-prefix", "", "--a-tag", "latest",
                         "--b-prefix", "lite-", "--b-tag", "latest",
                         "--registries", reg], capture_output=True, text=True)
    check("tag 推送缺版本号时报错", rc.returncode != 0)


def test_workflow_wiring():
    print("workflow 静态一致性:")
    image = open(os.path.join(WF, "_image.yml")).read()
    plan_out = re.search(r"^  plan:\n(.*?)(?=^  \w+:)", image, re.S | re.M)
    body = plan_out.group(1) if plan_out else ""
    declared = set(re.findall(r"^      (\w+):\s*\$\{\{ steps\.plan\.outputs\.(\w+) \}\}", body, re.M))
    check("plan job 声明了 groups 输出", "groups" in {a for a, _ in declared},
          f"实际 {sorted(a for a, _ in declared)}")

    for wf in ("Publish Package.yml", "Publish Ja3 Package.yml"):
        text = open(os.path.join(WF, wf)).read()
        # assemble 写出的文件名，publish 必须读得到
        out = re.search(r"--out (\S+)", text)
        mv = re.search(r"--main-variant (\S+) --lite-variant (\S+)", text)
        if out and mv:
            produced = {f"{out.group(1)}-{mv.group(1)}.txt", f"{out.group(1)}-{mv.group(2)}.txt"}
            reads = set(re.findall(r"cat (/tmp/srcs[\w.-]*)", text))
            check(f"{wf}: publish 读取的文件与 assemble 产出一致", reads == produced,
                  f"产出 {sorted(produced)} vs 读取 {sorted(reads)}")
        # 任何跑仓库内脚本的 job 都必须先 checkout，否则脚本文件不存在
        for block in re.split(r"^  (?=\w)", text, flags=re.M):
            job = block.split("\n", 1)[0].rstrip(":").strip()
            if "scripts/" in block:
                check(f"{wf} / {job}: 跑脚本且有 checkout", "actions/checkout" in block)
        envs = set(re.findall(r"^\s+(\w+):\s*\$\{\{ needs\.[\w-]+\.outputs\.groups \}\}", text, re.M))
        # 脚本参数 --xxx-groups "$VAR" 里的 VAR 必须在 env 中定义
        used = re.findall(r"--(\w+)-groups\s+\"\$(\w+)\"", text)
        check(f"{wf}: 组名 env 已定义", len(envs) == 2, f"实际 {sorted(envs)}")
        for opt, var in used:
            check(f"{wf}: --{opt}-groups 引用的 ${var} 有定义", var in envs,
                  f"env 里只有 {sorted(envs)}")


def main():
    test_assemble()
    test_missing_digest()
    test_plan_output_keys()
    test_publish_tags()
    test_workflow_wiring()
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} 项 -> {FAILURES}")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
