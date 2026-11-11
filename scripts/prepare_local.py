#!/usr/bin/env python3
"""生成可选的个人词库入口；公共源码在没有这些文件时也能部署。"""

from pathlib import Path

from build_flypy_ext import build


def write_if_changed(path, content):
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def prepare_local(root):
    report = build(root, include_personal=True)

    flypy = (root / "flypy.dict.yaml").read_text(encoding="utf-8")
    flypy = flypy.replace("name: flypy\n", "name: flypy.local\n", 1)
    flypy = flypy.replace("import_tables:\n", "import_tables:\n  - flypy/flypy.user.top\n", 1)
    flypy = flypy.replace("  - flypy_ext ", "  - flypy/flypy.user\n  - flypy_ext.local ", 1)
    write_if_changed(root / "flypy.local.dict.yaml", flypy)

    lansan = (root / "lansan_merged.dict.yaml").read_text(encoding="utf-8")
    lansan = lansan.replace("name: lansan_merged\n", "name: lansan.local\n", 1)
    lansan = lansan.replace("sort: by_weight\n", "sort: by_weight\nimport_tables:\n  - lansan_user\n", 1)
    write_if_changed(root / "lansan.local.dict.yaml", lansan)

    japanese = (root / "jaroomaji.dict.yaml").read_text(encoding="utf-8")
    japanese = japanese.replace("name: jaroomaji\n", "name: jaroomaji.local\n", 1)
    japanese = japanese.replace("import_tables:\n", "import_tables:\n  - jaroomaji.user\n", 1)
    write_if_changed(root / "jaroomaji.local.dict.yaml", japanese)

    write_if_changed(root / "local.yaml", """# 由 scripts/prepare.py 生成的本机词库入口；不上传 Git。
# schema 使用可选引用，缺少本文件时自动使用随源码提供的公共词库。
flypy:
  dictionary: flypy.local
flypy_ext:
  dictionary: flypy_ext.local
tiger:
  dictionary: tiger.extended
tigress:
  dictionary: tigress.extended
lansanguanfang:
  dictionary: lansan.local
jaroomaji:
  dictionary: jaroomaji.local
""")
    return report


if __name__ == "__main__":
    prepare_local(Path(__file__).resolve().parent.parent)
