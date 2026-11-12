#!/usr/bin/env python3
"""从固定版本的万象词库提取已有蓝三词组的权重；不修改编码或增加词组。"""

import argparse
import hashlib
import json
from pathlib import Path

from merge_lansan_dicts import SOURCES, read_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True,
                        help="万象数据仓库根目录，内含 dicts/；版本须与 wanxiang-source.json 一致")
    args = parser.parse_args()
    metadata = json.loads((SOURCES / "wanxiang-source.json").read_text(encoding="utf-8"))
    words = {row[0] for name in ("lansan_guanfang.dict.yaml", "ls_ci.dict.yaml")
             for row in read_rows(SOURCES / name) if len(row[0]) > 1}
    frequencies = {}
    for source in metadata["files"]:
        path = args.source_dir / source["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"来源文件校验失败：{path}")
        body = False
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not body:
                    body = line.strip() == "..."
                    continue
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                cells = line.rstrip("\r\n").split("\t")
                if cells[0] not in words or len(cells) < 3 or not cells[2]:
                    continue
                weight = int(cells[2])
                if weight < 0:
                    raise ValueError(f"{path}:{number}: 负权重")
                # 上游权重经过变换，不把不同读音的权重相加。
                frequencies[cells[0]] = max(frequencies.get(cells[0], 0), weight)
        if not body:
            raise ValueError(f"{path}: 缺少词典正文标记")

    output = SOURCES / metadata["output"]
    header = ("# 万象词频子集：词条\\t上游权重（不含拼音）\n"
              "# 来源：amzxyz/rime-wanxiang-data；CC-BY-4.0\n"
              f"# 固定版本：{metadata['revision']}\n"
              "# 提取与修改说明、许可证见本目录 README.md、LICENSE.wanxiang\n")
    output.write_text(header + "".join(f"{word}\t{frequencies[word]}\n"
                                      for word in sorted(frequencies)), encoding="utf-8")
    print(json.dumps({"output": str(output), "words": len(words),
                      "covered": len(frequencies), "missing": len(words) - len(frequencies),
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
