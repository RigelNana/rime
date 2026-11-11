#!/usr/bin/env python3
"""补齐缺失的个人词库空模板，再生成蓝三合并词库。"""

import json
from pathlib import Path
import shutil
import subprocess
import sys


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


if __name__ == "__main__":
    main()
