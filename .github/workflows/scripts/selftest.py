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
    test_workflow_wiring()
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} 项 -> {FAILURES}")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
