#!/usr/bin/env python3
"""补齐缺失的个人词库空模板，再生成蓝三合并表和小鹤扩展表。"""

import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_local import prepare_local


def main():
    root = Path(__file__).resolve().parent.parent
    templates = root / "templates" / "local"
    for template in sorted(templates.rglob("*.dict.yaml")):
        relative = template.relative_to(templates)
        destination = root / relative
        if destination.exists() or destination.is_symlink():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template, destination)
        print(f"已创建个人词库空模板：{relative}", flush=True)

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "merge_lansan_dicts.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    print(f"蓝三合并完成：{report['merged_phrase_rows']:,} 条词组编码记录；"
          f"{report['unique_phrases_including_personal']:,} 个不同词组（含本机个人词库）。")
    print(f"万象词频覆盖 {report['frequency_covered_words']:,} 个公共词组；"
          f"{report['frequency_missing_words']:,} 个未覆盖词使用低权重兜底。")
    print(f"已在原排序基线上调整 {report['char_word_order']['changed_codes']:,} 个混合编码；"
          "有简码的单字长码后置，并应用逐项评议，词序和字序保持不变。")

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "build_flypy_ext.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    print(f"小鹤扩展表完成：{report['characters']:,} 个新增扩展字；"
          f"{report['rows']:,} 条编码记录；跳过原库已有的 "
          f"{report['skipped_existing_characters']:,} 个字。")
    prepare_local(root)
    print("已生成本机个人词库入口 local.yaml；公共词库可以独立部署。")


if __name__ == "__main__":
    main()
