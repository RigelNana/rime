#!/usr/bin/env python3
"""从固定版本的社区码表提取小鹤缺失的扩展区单字；仅依赖标准库。"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shlex


EXTENSIONS = (
    ("A", 0x3400, 0x4DBF),
    ("B", 0x20000, 0x2A6DF),
    ("C", 0x2A700, 0x2B73F),
    ("D", 0x2B740, 0x2B81F),
    ("E", 0x2B820, 0x2CEAF),
    ("F", 0x2CEB0, 0x2EBEF),
    ("G", 0x30000, 0x3134F),
    ("H", 0x31350, 0x323AF),
    ("I", 0x2EBF0, 0x2EE5F),
    ("J", 0x323B0, 0x3347F),
)


def extension(char):
    return next((name for name, first, last in EXTENSIONS
                 if first <= ord(char) <= last), None)


def dictionary_rows(path):
    """读取现有 Rime 表的文本／编码及导入表；支持块列表与行内列表。"""
    header, separator, body = path.read_text(encoding="utf-8-sig").partition("\n...")
    if not separator:
        raise ValueError(f"词库缺少 YAML 结束标记：{path}")
    lists = {}
    current = None
    for line in header.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key = re.match(r"^(import_tables|columns):\s*(.*)$", line)
        if key:
            current, value = key.groups()
            lists[current] = []
            value = value.split("#", 1)[0].strip()
            if value:
                if not (value.startswith("[") and value.endswith("]")):
                    raise ValueError(f"不支持的 {current} 列表格式：{path}")
                lexer = shlex.shlex(value[1:-1], posix=True)
                lexer.whitespace += ","
                lexer.whitespace_split = True
                lists[current] = list(lexer)
                current = None
        elif current and line.lstrip().startswith("-"):
            value = shlex.split(line.lstrip()[1:], comments=True)
            if len(value) != 1:
                raise ValueError(f"不支持的 {current} 列表项：{path}: {line}")
            lists[current].extend(value)
        elif not line[0].isspace():
            current = None
        elif current:
            raise ValueError(f"不支持的 {current} 列表内容：{path}: {line}")
    columns = lists.get("columns", ["text", "code", "weight"])
    ti, ci = columns.index("text"), columns.index("code")
    rows = []
    for line in body.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) > max(ti, ci):
            rows.append((fields[ti], fields[ci]))
    return lists.get("import_tables", []), rows


def existing_characters(root, include_personal=False):
    seen, chars = set(), set()

    def visit(name):
        # 生成表不能成为自己的输入；首次部署时该文件尚不存在。
        if name == "flypy_ext" or name in seen:
            return
        seen.add(name)
        imports, rows = dictionary_rows(root / (name + ".dict.yaml"))
        chars.update(text for text, _ in rows if len(text) == 1)
        for child in imports:
            visit(child)

    visit("flypy")
    if include_personal:
        for name in ("flypy/flypy.user.top", "flypy/flypy.user"):
            if (root / (name + ".dict.yaml")).exists():
                visit(name)
    return chars


def build(root, include_personal=False):
    source = root / "sources" / "flypy" / "rare_chars.txt"
    existing = existing_characters(root, include_personal)
    rows, seen, skipped, normalized = [], set(), set(), []
    for number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 2 or len(fields[0]) != 1 or not re.fullmatch("[A-Za-z]{4}", fields[1]):
            raise ValueError(f"源码表第 {number} 行不是单字四码：{line!r}")
        char, raw_code = fields
        code = raw_code.lower()
        if code != raw_code:
            normalized.append({"line": number, "text": char, "from": raw_code, "to": code})
        if extension(char) is None:
            continue
        if char in existing:
            skipped.add(char)
            continue
        pair = (char, code)
        if pair not in seen:
            seen.add(pair)
            rows.append(pair)
    name = "flypy_ext.local" if include_personal else "flypy_ext"
    output = root / (name + ".dict.yaml")
    content = (
        "# 由 scripts/build_flypy_ext.py 生成；请勿直接编辑。\n"
        "# 来源与固定版本见 sources/flypy/README.md。\n"
        f"---\nname: {name}\nversion: \"1.0\"\nsort: original\n"
        "use_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n\n"
        + "".join(f"{char}\t{code}\t1\n" for char, code in rows)
    )
    if not output.exists() or output.read_text(encoding="utf-8") != content:
        temporary = output.with_suffix(".yaml.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(output)
    chars = {char for char, _ in rows}
    return {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "rows": len(rows),
        "characters": len(chars),
        "by_block": dict(sorted(Counter(extension(char) for char in chars).items())),
        "skipped_existing_characters": len(skipped),
        "normalized_codes": normalized,
    }


if __name__ == "__main__":
    print(json.dumps(build(Path(__file__).resolve().parent.parent), ensure_ascii=False, indent=2))
