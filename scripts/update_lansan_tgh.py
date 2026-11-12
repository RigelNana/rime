#!/usr/bin/env python3
"""从固定版本的本地 Unihan.zip 提取 8105 字，不联网。"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unihan-zip", type=Path, required=True)
    args = parser.parse_args()
    sources = Path(__file__).resolve().parent.parent / "sources/lansan"
    metadata = json.loads((sources / "tgh-source.json").read_text(encoding="utf-8"))
    if hashlib.sha256(args.unihan_zip.read_bytes()).hexdigest() != metadata["sha256"]:
        raise ValueError("Unihan.zip 与固定版本校验值不符")
    indexed = []
    with zipfile.ZipFile(args.unihan_zip) as archive:
        for name in archive.namelist():
            if not name.endswith(".txt"):
                continue
            for line in archive.read(name).decode("utf-8").splitlines():
                if "\tkTGH\t" not in line:
                    continue
                cp, _, value = line.split("\t")
                year, index = value.split(":")
                if year != "2013":
                    raise ValueError(f"意外的规范字表年份：{year}")
                indexed.append((int(index), chr(int(cp[2:], 16))))
    indexed.sort()
    if [n for n, _ in indexed] != list(range(1, 8106)) or len({c for _, c in indexed}) != 8105:
        raise ValueError("规范字表序号或字符有遗漏、重复")
    content = ("".join(c for _, c in indexed) + "\n").encode("utf-8")
    if hashlib.sha256(content).hexdigest() != metadata["extract_sha256"]:
        raise ValueError("提取结果与规范字表校验值不符")
    (sources / "tgh2013.txt").write_bytes(content)
    print("已提取并核对 8105 个规范字。")


if __name__ == "__main__":
    main()
