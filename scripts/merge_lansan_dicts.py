#!/usr/bin/env python3
"""合并蓝三字词表：保护 GB2312 最简码，表外字后置，保留纯单字顺序。"""

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


def read_tgh_characters(path, manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["extract_sha256"]:
        raise ValueError("8105 规范字表校验失败，请复核来源")
    chars = path.read_text(encoding="utf-8").strip()
    if len(chars) != 8105 or len(set(chars)) != 8105:
        raise ValueError("规范字表必须恰好包含 8105 个不重复的汉字")
    return set(chars)


def apply_legacy_order(official, characters, ranked_phrases):
    """重建 4e6fb8a 的历史基线，供后续最小改动使用。"""
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
    """重建 705 组评议后的历史基线；最终词序不再受这些配对约束。"""
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


def is_gb2312_han(character):
    if len(character) != 1 or not "\u4e00" <= character <= "\u9fff":
        return False
    try:
        return len(character.encode("gb2312")) == 2
    except UnicodeEncodeError:
        return False


def apply_frequency_order(rows, frequencies, phrase_orders=None):
    """GB2312 最简码前三选优先；词频排序允许指定词序例外。"""
    phrase_orders = phrase_orders or {}
    groups = defaultdict(list)
    shortest = {}
    for row in rows:
        text, code = row[:2]
        groups[code].append(row)
        if len(text) == 1 and re.fullmatch(r"[a-z]+", code):
            shortest[text] = min(shortest.get(text, len(code)), len(code))

    for code, words in phrase_orders.items():
        current_words = [row[0] for row in groups.get(code, []) if len(row[0]) > 1]
        if (not re.fullmatch(r"[a-z]{1,4}", code) or not words
                or len(words) != len(set(words)) or set(words) != set(current_words)):
            raise ValueError(f"{code}: 手动词序必须完整列出该编码的全部词组，请复核来源更新")

    overrides = {}
    stats = {"changed_codes": 0, "phrase_reordered_codes": 0,
             "gb2312_protected_rows": 0, "gb2312_promoted_rows": 0,
             "moved_character_rows": 0, "manual_phrase_codes": len(phrase_orders)}
    for code, group in groups.items():
        ordered = sorted(group, key=lambda row: -int(row[2]) if len(row) > 2 else 0)
        characters = [row for row in ordered if len(row[0]) == 1]
        words = [row for row in ordered if len(row[0]) > 1]
        if not characters and code not in phrase_orders:
            # 纯词编码已在合并阶段统一按万象词频排序。
            continue
        original_slots, preceding_words = [], 0
        for row in ordered:
            if len(row[0]) == 1:
                original_slots.append(preceding_words)
            else:
                preceding_words += 1

        lower, upper = [0] * len(characters), [len(words)] * len(characters)
        protected = set()
        for i, row in enumerate(characters):
            text = row[0]
            if not re.fullmatch(r"[a-z]+", code):
                continue
            if shortest[text] < len(code):
                lower[i] = len(words)
            elif is_gb2312_han(text):
                # 总名次 = 前面的词数 + 本字在单字序列中的名次。
                # 按全字集约束，常用集过滤后也不会超过第三。
                protected.add(i)
                upper[i] = min(upper[i], 3 - (i + 1))
                stats["gb2312_protected_rows"] += 1
        for i in range(1, len(characters)):
            lower[i] = max(lower[i], lower[i - 1])
        for i in range(len(characters) - 2, -1, -1):
            upper[i] = min(upper[i], upper[i + 1])
        if any(lo > hi for lo, hi in zip(lower, upper)):
            raise ValueError(f"{code}: GB2312 最简码前三选与固定单字顺序、简码后置冲突")
        slots = [max(lo, min(hi, old))
                 for lo, hi, old in zip(lower, upper, original_slots)]

        # 稳定排序：旧官方的单字分段不再阻挡词频，同频词不额外换位。
        ranked_words = sorted(words, key=lambda row: -frequencies.get(row[0], 0))
        if code in phrase_orders:
            by_text = {row[0]: row for row in words}
            ranked_words = [by_text[text] for text in phrase_orders[code]]
        buckets = [[] for _ in range(len(words) + 1)]
        for row, slot in zip(characters, slots):
            buckets[slot].append(row)
        adjusted = []
        for i, word in enumerate(ranked_words):
            adjusted.extend(buckets[i])
            adjusted.append(word)
        adjusted.extend(buckets[-1])
        if adjusted == ordered:
            continue
        for i, row in enumerate(adjusted):
            overrides[tuple(row[:2])] = len(adjusted) - i
        stats["changed_codes"] += 1
        stats["phrase_reordered_codes"] += ranked_words != words
        stats["gb2312_promoted_rows"] += sum(slots[i] < original_slots[i] for i in protected)
        stats["moved_character_rows"] += sum(a != b for a, b in zip(slots, original_slots))

    result = []
    for row in rows:
        weight = overrides.get(tuple(row[:2]))
        result.append([row[0], row[1], str(weight), *row[3:]] if weight is not None else row)
    return result, stats


def apply_charset_order(rows, tgh_characters):
    """混输中表外字置于全部词后；GB2312 最简码保留现有位置。"""
    groups, shortest = defaultdict(list), {}
    for row in rows:
        text, code = row[:2]
        groups[code].append(row)
        if len(text) == 1 and re.fullmatch(r"[a-z]+", code):
            shortest[text] = min(shortest.get(text, len(code)), len(code))
    overrides, pure_orders = {}, {}
    stats = {"changed_codes": 0, "demoted_character_rows": 0,
             "promoted_phrase_rows": 0, "pure_order_restored_codes": 0}
    for code, group in groups.items():
        if not re.fullmatch(r"[a-z]{1,4}", code) or not any(len(r[0]) > 1 for r in group):
            continue
        ordered = sorted(group, key=lambda r: -int(r[2]) if len(r) > 2 else 0)
        cold = {r[0] for r in ordered if len(r[0]) == 1 and r[0] not in tgh_characters
                and not (is_gb2312_han(r[0]) and len(code) == shortest[r[0]])}
        adjusted = [r for r in ordered if r[0] not in cold] + [r for r in ordered if r[0] in cold]
        if adjusted == ordered:
            continue
        old_chars = [r[0] for r in ordered if len(r[0]) == 1]
        new_chars = [r[0] for r in adjusted if len(r[0]) == 1]
        if old_chars != new_chars:
            pure_orders[code] = "".join(old_chars)
        old_ranks = {r[0]: i for i, r in enumerate(ordered)}
        for i, row in enumerate(adjusted):
            text = row[0]
            if len(text) == 1 and is_gb2312_han(text) and len(code) == shortest[text] and i >= 3:
                raise ValueError(f"{code}: 表外字后置后 {text} 超出前三选")
            overrides[tuple(row[:2])] = len(adjusted) - i
            stats["demoted_character_rows"] += len(text) == 1 and i > old_ranks[text]
            stats["promoted_phrase_rows"] += len(text) > 1 and i < old_ranks[text]
        stats["changed_codes"] += 1
    stats["pure_order_restored_codes"] = len(pure_orders)
    result = []
    for row in rows:
        weight = overrides.get(tuple(row[:2]))
        result.append([row[0], row[1], str(weight), *row[3:]] if weight is not None else row)
    return result, pure_orders, stats


def apply_candidate_prefixes(rows, prefixes, tgh_characters):
    """应用明确的字词优先例外，保持字序、词序和既有保护约束。"""
    groups, shortest = defaultdict(list), {}
    for row in rows:
        text, code = row[:2]
        groups[code].append(row)
        if len(text) == 1 and re.fullmatch(r"[a-z]+", code):
            shortest[text] = min(shortest.get(text, len(code)), len(code))
    overrides = {}
    stats = {"configured_codes": len(prefixes), "changed_codes": 0,
             "new_phrase_first_codes": 0, "new_character_first_codes": 0}
    for code, prefix in prefixes.items():
        if (not re.fullmatch(r"[a-z]{1,4}", code) or not isinstance(prefix, list)
                or not prefix or any(not isinstance(t, str) or not t for t in prefix)
                or len(prefix) != len(set(prefix))):
            raise ValueError(f"{code}: 无效或重复的手动候选前缀")
        ordered = sorted(groups.get(code, []), key=lambda r: -int(r[2]) if len(r) > 2 else 0)
        by_text = {r[0]: r for r in ordered}
        if any(t not in by_text for t in prefix):
            raise ValueError(f"{code}: 手动前缀引用不存在的候选，请复核来源更新")
        adjusted = [by_text[t] for t in prefix] + [r for r in ordered if r[0] not in prefix]
        for single, label in [(True, "单字"), (False, "词组")]:
            if ([r[0] for r in ordered if (len(r[0]) == 1) == single]
                    != [r[0] for r in adjusted if (len(r[0]) == 1) == single]):
                raise ValueError(f"{code}: 手动前缀改变了{label}内部顺序，请复核")
        last_word = max((i for i, r in enumerate(adjusted) if len(r[0]) > 1), default=-1)
        for i, row in enumerate(adjusted):
            text = row[0]
            if len(text) != 1:
                continue
            shortest_code = len(code) == shortest[text]
            protected = is_gb2312_han(text) and shortest_code
            if protected and i >= 3:
                raise ValueError(f"{code}: 手动前缀使 GB2312 最简码 {text} 超出前三选")
            if i < last_word and (not shortest_code or (text not in tgh_characters and not protected)):
                raise ValueError(f"{code}: 手动前缀违反简码长码后置或表外字后置规则")
        if adjusted == ordered:
            continue
        for i, row in enumerate(adjusted):
            overrides[tuple(row[:2])] = len(adjusted) - i
        stats["changed_codes"] += 1
        if adjusted[0][0] != ordered[0][0]:
            stats["new_phrase_first_codes"] += len(adjusted[0][0]) > 1
            stats["new_character_first_codes"] += len(adjusted[0][0]) == 1
    result = []
    for row in rows:
        weight = overrides.get(tuple(row[:2]))
        result.append([row[0], row[1], str(weight), *row[3:]] if weight is not None else row)
    return result, stats


def apply_reviewed_priorities(rows, priorities, tgh_characters):
    """按人工字/词优先评议重排；GB2312 前三选只是上限，不固定旧名次。"""
    groups, shortest = defaultdict(list), {}
    for row in rows:
        text, code = row[:2]
        groups[code].append(row)
        if len(text) == 1 and re.fullmatch(r"[a-z]+", code):
            shortest[text] = min(shortest.get(text, len(code)), len(code))
    prefixes = {}
    for code, review in priorities.items():
        if (not re.fullmatch(r"[a-z]{1,4}", code) or not isinstance(review, dict)
                or review.get("priority") not in ("word", "character")
                or not isinstance(review.get("character"), str)
                or len(review["character"]) != 1):
            raise ValueError(f"{code}: 无效的字词优先评议")
        ordered = sorted(groups.get(code, []), key=lambda r: -int(r[2]) if len(r) > 2 else 0)
        characters = [r for r in ordered if len(r[0]) == 1]
        words = [r for r in ordered if len(r[0]) > 1]
        if not characters or characters[0][0] != review["character"]:
            raise ValueError(f"{code}: 评议首字不存在或单字顺序已改变，请复核来源更新")
        if review["priority"] == "word" and not words:
            raise ValueError(f"{code}: 词优先评议已无词组，请复核来源更新")

        # 尽量让全部词在字前，仅为受保护字预留前三选的位置。
        # 保持字序时，后面受保护字的限制也约束前面的字。
        slots = [len(words)] * len(characters)
        for i, row in enumerate(characters):
            if is_gb2312_han(row[0]) and len(code) == shortest[row[0]]:
                slots[i] = min(slots[i], 2 - i)
        for i in range(len(characters) - 2, -1, -1):
            slots[i] = min(slots[i], slots[i + 1])
        if any(slot < 0 for slot in slots):
            raise ValueError(f"{code}: 字序与 GB2312 最简码前三选冲突")
        if review["priority"] == "character":
            slots[0] = 0
        elif slots[0] == 0:
            raise ValueError(f"{code}: 词首选与 GB2312 最简码前三选冲突")
        buckets = [[] for _ in range(len(words) + 1)]
        for row, slot in zip(characters, slots):
            buckets[slot].append(row[0])
        prefix = []
        for i, row in enumerate(words):
            prefix.extend(buckets[i])
            prefix.append(row[0])
        prefix.extend(buckets[-1])
        prefixes[code] = prefix

    # 复用完整约束检查，拒绝破坏词序、字序、长码及表外字后置规则。
    return apply_candidate_prefixes(rows, prefixes, tgh_characters)


def write_pure_orders(path, orders):
    lines = ["-- 自动生成：scripts/merge_lansan_dicts.py；仅用于纯单字恢复原顺序。", "return {"]
    for code, chars in sorted(orders.items()):
        lines.append(f"  [{json.dumps(code)}] = {json.dumps(chars, ensure_ascii=False)},")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "lansan_merged.dict.yaml")
    parser.add_argument("--single-order-output", type=Path,
                        help="纯单字顺序恢复表；自定义词库输出时默认写在该输出旁边")
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
    # 先重建完整历史基线，再移除用户排除的词，避免改动其余编码的位置。
    exclusion_path = SOURCES / "phrase_exclusions.json"
    excluded_words = set(json.loads(exclusion_path.read_text(encoding="utf-8"))["words"])
    if any(len(word) < 2 for word in excluded_words):
        raise ValueError("排除项必须为多字词组，不能删除单字")
    source_phrase_rows = len(phrases)
    phrases = {key: row for key, row in phrases.items() if key[0] not in excluded_words}
    rows = [row for row in rows if row[0] not in excluded_words]
    phrase_words -= excluded_words
    phrase_order_path = SOURCES / "phrase_order_overrides.json"
    phrase_orders = json.loads(phrase_order_path.read_text(encoding="utf-8"))["orders"]
    rows, frequency_order_stats = apply_frequency_order(rows, frequencies, phrase_orders)
    tgh_path, tgh_manifest = SOURCES / "tgh2013.txt", SOURCES / "tgh-source.json"
    tgh_characters = read_tgh_characters(tgh_path, tgh_manifest)
    rows, pure_orders, charset_order_stats = apply_charset_order(
        rows, tgh_characters)
    priority_path = SOURCES / "mixed_priority_reviews.json"
    priorities = json.loads(priority_path.read_text(encoding="utf-8"))["groups"]
    rows, priority_stats = apply_reviewed_priorities(rows, priorities, tgh_characters)
    candidate_prefix_path = SOURCES / "candidate_prefix_overrides.json"
    candidate_prefixes = json.loads(candidate_prefix_path.read_text(encoding="utf-8"))["prefixes"]
    rows, candidate_prefix_stats = apply_candidate_prefixes(rows, candidate_prefixes, tgh_characters)
    keys = [tuple(row[:2]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("合并结果仍包含重复的词＋编码")
    if set(keys) != {tuple(row[:2]) for row in official + standard if row[0] not in excluded_words}:
        raise ValueError("合并结果与来源词表及词组排除项不符")

    header = """# Rime dictionary
# encoding: utf-8
# 自动生成：python scripts/merge_lansan_dicts.py
# 官方单字表 + ls_ci 词组 + 官方独有词组。
# 万象数据：amzxyz/rime-wanxiang-data，CC-BY-4.0；来源及修改见 sources/lansan/README.md。
# GB2312 单字的最短字母编码保证前三选；有简码的长码仍在全部同码词后。
# 同码词组默认按万象词频排序，可跨过单字；同频保持历史基线次序。
# 用户指定词序优先于词频，见 sources/lansan/phrase_order_overrides.json。
# 用户排除词组的全部编码不导出，见 sources/lansan/phrase_exclusions.json。
# 705 组评议只用于重建基线位置，最终排序不强制保留旧字词配对关系。
# 8105 规范字表之外的单字排在全部词后，GB2312 最简码例外。
# 用户明确的字词优先例外见 sources/lansan/candidate_prefix_overrides.json。
# 字词优先评议见 sources/lansan/mixed_priority_reviews.json；前三选不固定旧名次。
# 纯单字原顺序由 lua/lansan_single_order.lua 和对应过滤器恢复。
# 混合编码使用组内排序权重；纯词编码使用万象权重 + 1，未覆盖项为 1。
# 按“词＋编码”去重；同词异码保留；个人词库由可选的本机入口接入。
# 原始词库不作修改。更新来源词库后重新生成并部署。
---
name: lansan_merged
version: "2026.11.13.3"
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
    single_output = args.single_order_output or (
        ROOT / "lua/lansan_single_order.lua" if args.output.resolve() == ROOT / "lansan_merged.dict.yaml"
        else args.output.with_suffix(".single_order.lua"))
    write_pure_orders(single_output, pure_orders)

    official_codes, standard_codes = defaultdict(set), defaultdict(set)
    for row in official:
        if len(row[0]) > 1:
            official_codes[row[0]].add(row[1])
    for word, code in standard_pairs:
        standard_codes[word].add(code)
    conflicts = {
        word: {"official": sorted(official_codes[word]), "standard": sorted(standard_codes[word])}
        for word in sorted((official_codes.keys() & standard_codes.keys()) - excluded_words)
        if official_codes[word].isdisjoint(standard_codes[word])
    }
    code_counts = Counter(row[1] for row in phrases.values())
    report = {
        "output": str(args.output),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [SOURCES / "lansan_guanfang.dict.yaml", SOURCES / "ls_ci.dict.yaml",
                                       frequency_path, review_path, phrase_order_path, exclusion_path,
                                       tgh_path, tgh_manifest, priority_path, candidate_prefix_path]},
        "official_character_rows": len(characters),
        "standard_phrase_rows": len(standard_pairs),
        "official_supplement_rows": supplements,
        "duplicate_phrase_rows_removed": sum(len(row[0]) > 1 for row in official) + len(standard) - source_phrase_rows,
        "excluded_phrase_rows": source_phrase_rows - len(phrases),
        "excluded_words": sorted(excluded_words),
        "merged_phrase_rows": len(phrases),
        "frequency_source": "wanxiang",
        "frequency_covered_words": len(phrase_words & frequencies.keys()),
        "frequency_missing_words": len(phrase_words - frequencies.keys()),
        "legacy_order": legacy_stats,
        "char_word_order": order_stats,
        "frequency_order": frequency_order_stats,
        "charset_order": charset_order_stats,
        "reviewed_priority_order": priority_stats,
        "candidate_prefix_order": candidate_prefix_stats,
        "single_order_output": str(single_output),
        "unique_phrases_including_personal": len({row[0] for row in rows + personal if len(row[0]) > 1}),
        "maximum_phrases_per_code": max(code_counts.values()),
        "different_codes_preserved": conflicts,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
