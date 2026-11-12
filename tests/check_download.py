#!/usr/bin/env python3
"""验证 Git 源码可直接部署；不运行 prepare.py，不借用系统共享配置。"""

import argparse
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--index", action="store_true", help="检查暂存区，否则检查 HEAD")
    source_group.add_argument("--worktree", action="store_true", help="检查工作区公共文件，排除 Git 忽略的本机数据")
    parser.add_argument("--lua-library", type=Path, help="librime-lua.so 路径")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    library = args.lua_library
    if library is None:
        candidates = [Path("/usr/lib/rime-plugins/librime-lua.so")]
        candidates += sorted(Path("/usr/lib").glob("*/rime-plugins/librime-lua.so"))
        library = next((path for path in candidates if path.is_file()), None)
    if library is None or not library.is_file():
        parser.error("找不到 librime-lua；请用 --lua-library 指定动态库路径")
    library = library.resolve()

    with tempfile.TemporaryDirectory(prefix="rime-download-test-") as temporary:
        work = Path(temporary)
        source, shared = work / "source", work / "shared"
        source.mkdir()
        shared.mkdir()
        if args.worktree:
            paths = subprocess.check_output(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root)
            for name in set(paths.decode().split("\0")) - {""}:
                original = root / name
                if not original.is_file():
                    continue
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
        elif args.index:
            subprocess.run(["git", "checkout-index", "--all", "--prefix=" + str(source) + "/"],
                           cwd=root, check=True)
        else:
            archive = subprocess.check_output(["git", "archive", "HEAD"], cwd=root)
            with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
                stream.extractall(source, filter="data")
        private = ["local.yaml", "tiger.extended.dict.yaml", "tigress.extended.dict.yaml",
                   "lansan_user.dict.yaml", "jaroomaji.user.dict.yaml",
                   "flypy/flypy.user.dict.yaml", "flypy/flypy.user.top.dict.yaml"]
        if any((source / name).exists() for name in private):
            raise RuntimeError("公开源码意外包含个人词库或本机入口")
        deploy = subprocess.run(["rime_deployer", "--build", str(source), str(shared)],
                                text=True, capture_output=True)
        if deploy.returncode:
            raise RuntimeError("源码直接部署失败：\n" + deploy.stdout + deploy.stderr)
        binary = work / "download-smoke"
        subprocess.run(["c++", "-std=c++17", str(source / "tests/download_smoke.cc"),
                        "-Wl,--no-as-needed", "-Wl,-rpath," + str(library.parent),
                        str(library), "-lrime", "-o", str(binary)], check=True)
        subprocess.run([str(binary), str(source), str(shared)], check=True)
        print("通过：源码原样部署，无需个人文件、Python 准备步骤或系统共享配置。")


if __name__ == "__main__":
    main()
