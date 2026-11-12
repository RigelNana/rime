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
    print(f"已统一调整 {report['frequency_order']['phrase_reordered_codes']:,} 个编码的词序；"
          f"{report['frequency_order']['gb2312_promoted_rows']} 条 GB2312 单字最简码提至前三。"
          "有简码的长码仍在词后，同频词保持原序。")
    print(f"规范字分层调整 {report['charset_order']['changed_codes']:,} 组；"
          f"纯单字恢复表保护 {report['charset_order']['pure_order_restored_codes']} 组原字序。")
    print(f"另保留 {report['frequency_order']['manual_phrase_codes']} 组用户指定词序。")
    print(f"应用 {report['candidate_prefix_order']['changed_codes']} 组明确的字词优先例外；"
          "单字内部顺序和词组内部顺序保持不变。")

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
