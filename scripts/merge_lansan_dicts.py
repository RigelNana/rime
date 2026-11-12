#!/usr/bin/env python3
"""合并蓝三字词表，使用固定版本的万象词频重排词组，不改动来源编码。"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources" / "lansan"


def read_rows(path):
    rows = []
    in_body = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not in_body:
            in_body = line.strip() == "..."
            continue
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if not 2 <= len(cells) <= 4 or not cells[0] or not cells[1]:
            raise ValueError(f"{path.name}:{number}: 无效词条")
        rows.append(cells)
    if not in_body:
        raise ValueError(f"{path.name}: 缺少词典正文标记")
    return rows


def read_frequencies(path):
    frequencies = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) != 2 or len(cells[0]) < 2 or not cells[1].isdigit():
            raise ValueError(f"{path.name}:{number}: 无效词频")
        if cells[0] in frequencies:
            raise ValueError(f"{path.name}:{number}: 重复词条")
        frequencies[cells[0]] = int(cells[1])
    return frequencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "lansan_merged.dict.yaml")
    args = parser.parse_args()
    official = read_rows(SOURCES / "lansan_guanfang.dict.yaml")
    standard = read_rows(SOURCES / "ls_ci.dict.yaml")
    personal_path = ROOT / "lansan_user.dict.yaml"
    personal = read_rows(personal_path) if personal_path.exists() else []

    # 保留官方单字记录的编码、原始顺序和未填写词频的状态。
    # 包括来源文件里含非字母符号的编码；此脚本只合并词组，不修订字表。
    characters = [row for row in official if len(row[0]) == 1]
    phrases = {}
    for row in standard:
        if len(row[0]) <= 1 or len(row) < 3 or int(row[2]) <= 1:
            raise ValueError(f"ls_ci 包含非词组或无有效词频的记录：{row!r}")
        key = tuple(row[:2])
        if key not in phrases or int(row[2]) > int(phrases[key][2]):
            phrases[key] = row

    standard_pairs = set(phrases)
    supplements = 0
    for row in official:
        key = tuple(row[:2])
        if len(row[0]) > 1 and key not in phrases:
            # 此处的旧权重仅用于万象权重相同时保持原有词组优先级。
            phrases[key] = [row[0], row[1], "1", *row[3:]]
            supplements += 1

    frequency_path = SOURCES / "wanxiang_frequency.txt"
    frequencies = read_frequencies(frequency_path)
    phrase_words = {row[0] for row in phrases.values()}
    if frequencies.keys() - phrase_words:
        raise ValueError("万象词频子集含当前蓝三词库之外的词，请重新提取子集")
    # 先固定旧权重的次序；同频时由稳定排序保留该次序。
    # 统一加 1 保留上游 0 与正权重的相对大小，并给未覆盖词留出兜底权重 1。
    ranked_phrases = sorted(phrases.values(), key=lambda row: -int(row[2]))
    ranked_phrases = [[row[0], row[1], str(frequencies.get(row[0], 0) + 1), *row[3:]]
                      for row in ranked_phrases]
    ranked_phrases.sort(key=lambda row: -int(row[2]))
    rows = characters + ranked_phrases
    keys = [tuple(row[:2]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("合并结果仍包含重复的词＋编码")
    if set(keys) != {tuple(row[:2]) for row in official + standard}:
        raise ValueError("合并结果没有完整保留两份来源词表")

    header = """# Rime dictionary
# encoding: utf-8
# 自动生成：python scripts/merge_lansan_dicts.py
# 官方单字表 + ls_ci 词组 + 官方独有词组；词组统一使用万象词频。
# 万象数据：amzxyz/rime-wanxiang-data，CC-BY-4.0；来源及修改见 sources/lansan/README.md。
# 词组权重 = 万象权重 + 1；未覆盖项为 1；同频沿用旧词组优先级。
# 按“词＋编码”去重；同词异码保留；个人词库由可选的本机入口接入。
# 原始词库不作修改。更新来源词库后重新生成并部署。
---
name: lansan_merged
version: "2026.11.12"
sort: by_weight
columns:
  - text
  - code
  - weight
  - stem
encoder:
  exclude_patterns:
    - "^z.*$"
  rules:
    - length_equal: 2
      formula: "AaAbBaBb"
    - length_equal: 3
      formula: "AaBaCaCb"
    - length_in_range: [4, 32]
      formula: "AaBaCaZa"
...
"""
    args.output.write_text(header + "".join("\t".join(row) + "\n" for row in rows), encoding="utf-8")

    official_codes, standard_codes = defaultdict(set), defaultdict(set)
    for row in official:
        if len(row[0]) > 1:
            official_codes[row[0]].add(row[1])
    for word, code in standard_pairs:
        standard_codes[word].add(code)
    conflicts = {
        word: {"official": sorted(official_codes[word]), "standard": sorted(standard_codes[word])}
        for word in sorted(official_codes.keys() & standard_codes.keys())
        if official_codes[word].isdisjoint(standard_codes[word])
    }
    code_counts = Counter(row[1] for row in phrases.values())
    report = {
        "output": str(args.output),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [SOURCES / "lansan_guanfang.dict.yaml", SOURCES / "ls_ci.dict.yaml",
                                       frequency_path]},
        "official_character_rows": len(characters),
        "standard_phrase_rows": len(standard_pairs),
        "official_supplement_rows": supplements,
        "duplicate_phrase_rows_removed": sum(len(row[0]) > 1 for row in official) + len(standard) - len(phrases),
        "merged_phrase_rows": len(phrases),
        "frequency_source": "wanxiang",
        "frequency_covered_words": len(phrase_words & frequencies.keys()),
        "frequency_missing_words": len(phrase_words - frequencies.keys()),
        "unique_phrases_including_personal": len({row[0] for row in rows + personal if len(row[0]) > 1}),
        "maximum_phrases_per_code": max(code_counts.values()),
        "different_codes_preserved": conflicts,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
