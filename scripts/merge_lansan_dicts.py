#!/usr/bin/env python3
"""合并蓝三字词表，固定词序后按简码和逐项评议调整字词关系。"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


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


def apply_legacy_order(official, characters, ranked_phrases):
    """重建 4e6fb8a 的排序基线，后续调整不得改变其中的词序、字序。"""
    original_groups, phrase_groups = defaultdict(list), defaultdict(list)
    for row in official:
        original_groups[row[1]].append(row)
    for row in ranked_phrases:
        phrase_groups[row[1]].append(row)

    overrides = {}
    stats = {"mixed_codes": 0, "old_mixed_codes": 0,
             "new_phrase_rows_after_characters": 0, "weighted_character_rows": 0}
    for code, phrase_rows in phrase_groups.items():
        original = original_groups[code]
        single_rows = [row for row in original if len(row[0]) == 1]
        if not single_rows:
            continue
        stats["mixed_codes"] += 1
        stats["weighted_character_rows"] += len(single_rows)
        slots = {}
        preceding_characters = 0
        for row in original:
            if len(row[0]) == 1:
                preceding_characters += 1
            else:
                slots[tuple(row[:2])] = preceding_characters
        stats["old_mixed_codes"] += bool(slots)
        buckets = [[] for _ in range(len(single_rows) + 1)]
        # phrase_rows 已按万象权重和原同频次序排列；分段时保留该次序。
        for row in phrase_rows:
            key = tuple(row[:2])
            slot = slots.get(key, len(single_rows))
            buckets[slot].append(row)
            stats["new_phrase_rows_after_characters"] += key not in slots

        ordered = []
        for index, row in enumerate(single_rows):
            ordered.extend(buckets[index])
            ordered.append(row)
        ordered.extend(buckets[-1])
        # 精确编码匹配时，单调递减的排序权重可落实旧字词关系。
        # 这是组内优先级，不再将混合编码的 weight 当作语料词频。
        for index, row in enumerate(ordered):
            overrides[tuple(row[:2])] = len(ordered) - index

    result = []
    for row in characters + ranked_phrases:
        weight = overrides.get(tuple(row[:2]))
        result.append([row[0], row[1], str(weight), *row[3:]] if weight is not None else row)
    return result, stats


def read_order_reviews(path):
    reviews = {}
    for review in json.loads(path.read_text(encoding="utf-8"))["reviews"]:
        code = review["code"]
        if code in reviews or not re.fullmatch(r"[a-z]+", code):
            raise ValueError(f"重复或无效的评议编码：{code!r}")
        pairs = set()
        for character, word, preference in review["relations"]:
            if (len(character) != 1 or len(word) < 2
                    or preference not in {"word", "character", "keep"}
                    or (character, word) in pairs):
                raise ValueError(f"{code}: 无效或重复的字词评议")
            pairs.add((character, word))
        reviews[code] = review["relations"]
    return reviews


def apply_char_word_order(rows, reviews):
    """只移动字词的相对位置；两类候选各自的内部次序保持不变。"""
    groups = defaultdict(list)
    shortest = {}
    for row in rows:
        text, code = row[:2]
        groups[code].append(row)
        if len(text) == 1 and re.fullmatch(r"[a-z]+", code):
            shortest[text] = min(shortest.get(text, len(code)), len(code))
    for code, relations in reviews.items():
        texts = {row[0] for row in groups.get(code, [])}
        if not relations or any(c not in texts or w not in texts for c, w, _ in relations):
            raise ValueError(f"{code}: 评议引用的字词不存在，请复核来源更新")

    overrides = {}
    stats = {"review_codes": len(reviews), "review_relations": sum(map(len, reviews.values())),
             "shortcode_character_rows": 0, "changed_codes": 0,
             "review_changed_codes": 0, "moved_character_rows": 0,
             "changed_char_word_pairs": 0}
    for code, group in groups.items():
        if not (any(len(row[0]) == 1 for row in group)
                and any(len(row[0]) > 1 for row in group)):
            continue
        ordered = sorted(group, key=lambda row: -int(row[2]))
        characters = [row for row in ordered if len(row[0]) == 1]
        words = [row for row in ordered if len(row[0]) > 1]
        char_index = {row[0]: i for i, row in enumerate(characters)}
        word_index = {row[0]: i for i, row in enumerate(words)}
        # 每个单字的位置用“它前面有几个词”表示；词序始终固定。
        original_slots, preceding_words = [], 0
        for row in ordered:
            if len(row[0]) == 1:
                original_slots.append(preceding_words)
            else:
                preceding_words += 1
        lower, upper = [0] * len(characters), [len(words)] * len(characters)
        shorthand = set()
        for i, row in enumerate(characters):
            if re.fullmatch(r"[a-z]+", code) and shortest[row[0]] < len(code):
                shorthand.add(row[0])
                lower[i] = len(words)
                stats["shortcode_character_rows"] += 1
        for character, word, preference in reviews.get(code, []):
            i, j = char_index[character], word_index[word]
            if preference == "word":
                lower[i] = max(lower[i], j + 1)
            elif preference == "character" and character not in shorthand:
                upper[i] = min(upper[i], j)
        # 单字也不能互相跨越：后一个字的槽位不能小于前一个字。
        for i in range(1, len(characters)):
            lower[i] = max(lower[i], lower[i - 1])
        for i in range(len(characters) - 2, -1, -1):
            upper[i] = min(upper[i], upper[i + 1])
        if any(lo > hi for lo, hi in zip(lower, upper)):
            raise ValueError(f"{code}: 字词评议与固定字序、词序冲突，请人工复核")
        # 在满足约束的可行区间内，尽量保留原位置，减少额外的字词跨越。
        slots = [max(lo, min(hi, old))
                 for lo, hi, old in zip(lower, upper, original_slots)]
        if slots == original_slots:
            continue
        buckets = [[] for _ in range(len(words) + 1)]
        for row, slot in zip(characters, slots):
            buckets[slot].append(row)
        adjusted = []
        for i, word in enumerate(words):
            adjusted.extend(buckets[i])
            adjusted.append(word)
        adjusted.extend(buckets[-1])
        for i, row in enumerate(adjusted):
            overrides[tuple(row[:2])] = len(adjusted) - i
        stats["changed_codes"] += 1
        stats["review_changed_codes"] += code in reviews
        stats["moved_character_rows"] += sum(a != b for a, b in zip(slots, original_slots))
        stats["changed_char_word_pairs"] += sum(abs(a - b) for a, b in zip(slots, original_slots))

    result = []
    for row in rows:
        weight = overrides.get(tuple(row[:2]))
        result.append([row[0], row[1], str(weight), *row[3:]] if weight is not None else row)
    return result, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "lansan_merged.dict.yaml")
    args = parser.parse_args()
    official = read_rows(SOURCES / "lansan_guanfang.dict.yaml")
    standard = read_rows(SOURCES / "ls_ci.dict.yaml")
    personal_path = ROOT / "lansan_user.dict.yaml"
    personal = read_rows(personal_path) if personal_path.exists() else []

    # 保留官方单字编码和单字间的原始次序；混合编码稍后写入排序权重。
    # 包括来源文件里含非字母符号的编码；此脚本不修订字表编码。
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
    rows, legacy_stats = apply_legacy_order(official, characters, ranked_phrases)
    review_path = SOURCES / "char_word_order.json"
    rows, order_stats = apply_char_word_order(rows, read_order_reviews(review_path))
    keys = [tuple(row[:2]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("合并结果仍包含重复的词＋编码")
    if set(keys) != {tuple(row[:2]) for row in official + standard}:
        raise ValueError("合并结果没有完整保留两份来源词表")

    header = """# Rime dictionary
# encoding: utf-8
# 自动生成：python scripts/merge_lansan_dicts.py
# 官方单字表 + ls_ci 词组 + 官方独有词组。
# 万象数据：amzxyz/rime-wanxiang-data，CC-BY-4.0；来源及修改见 sources/lansan/README.md。
# 先重建旧官方位置及万象词频基线，再固定词序、字序调整字词关系。
# 有简码的单字长码置于同码词组之后；其余按 char_word_order.json 评议。
# 混合编码使用组内排序权重；不改变词组之间或单字之间的次序。
# 纯词编码：权重 = 万象权重 + 1，未覆盖项为 1；同频沿用旧词组优先级。
# 按“词＋编码”去重；同词异码保留；个人词库由可选的本机入口接入。
# 原始词库不作修改。更新来源词库后重新生成并部署。
---
name: lansan_merged
version: "2026.11.12.3"
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
                                       frequency_path, review_path]},
        "official_character_rows": len(characters),
        "standard_phrase_rows": len(standard_pairs),
        "official_supplement_rows": supplements,
        "duplicate_phrase_rows_removed": sum(len(row[0]) > 1 for row in official) + len(standard) - len(phrases),
        "merged_phrase_rows": len(phrases),
        "frequency_source": "wanxiang",
        "frequency_covered_words": len(phrase_words & frequencies.keys()),
        "frequency_missing_words": len(phrase_words - frequencies.keys()),
        "legacy_order": legacy_stats,
        "char_word_order": order_stats,
        "unique_phrases_including_personal": len({row[0] for row in rows + personal if len(row[0]) > 1}),
        "maximum_phrases_per_code": max(code_counts.values()),
        "different_codes_preserved": conflicts,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
