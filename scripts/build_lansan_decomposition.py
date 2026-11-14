#!/usr/bin/env python3
"""导入用户拆分附件，或离线生成蓝三 OpenCC 拆分注释表。"""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from merge_lansan_dicts import is_gb2312_han, read_rows

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources/lansan"
FIELDS = ["text", "code", "roots", "root_ids", "suffix", "source"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dictionary_codes(path):
    codes = defaultdict(set)
    for row in read_rows(path):
        if len(row[0]) == 1:
            codes[row[0]].add(row[1])
    return codes


def read_root_keys(path):
    """只读取工作簿字根键位表；不执行公式、链接或工作簿中的说明。"""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as book:
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        rels = {r.attrib["Id"]: r.attrib["Target"] for r in
                ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))}
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            shared = ["".join(t.text or "" for t in si.findall(".//s:t", ns))
                      for si in ET.fromstring(book.read("xl/sharedStrings.xml"))]
        sheet = next(s for s in workbook.find("s:sheets", ns) if s.attrib["name"] == "字根键位")
        target = rels[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        keys = {}
        for row in ET.fromstring(book.read(target)).find("s:sheetData", ns):
            cells = {}
            for cell in row:
                column = re.sub(r"\d", "", cell.attrib["r"])
                value = cell.find("s:v", ns)
                if cell.attrib.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in cell.findall(".//s:t", ns))
                elif cell.attrib.get("t") == "s" and value is not None:
                    text = shared[int(value.text)]
                else:
                    text = value.text if value is not None else ""
                cells[column] = text
            if cells.get("A") == "字根ID":
                continue
            root, key = cells.get("A", ""), cells.get("D", "")
            if not root or not re.fullmatch("[a-z]", key) or root in keys:
                raise ValueError(f"工作簿字根键位无效或重复：{root!r} {key!r}")
            keys[root] = key
        return keys


def derive_code(row, root_keys):
    ids = row["root_ids"].split()
    if not ids:
        raise ValueError(f"{row['text']}: 没有字根 ID")
    keys = [root_keys[root] for root in ids]
    if row["text"] == "一" and ids == ["1"]:
        return "fjj"  # 附件“结果与规则”A31 指明的一字补 j 例外。
    if len(keys) >= 4:
        return "".join(keys[:3] + keys[-1:])
    return "".join(keys) + row["suffix"]


def write_tsv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def import_attachments(table, workbook, codes):
    root_keys = read_root_keys(workbook)
    selected, unmatched, seen = [], [], set()
    unmatched_fields = ["汉字", "当前编码", "修正版全码", "修正版纯字根",
                        "扩展试验版全码", "扩展版纯字根", "问题定位"]
    with table.open(encoding="utf-8-sig", newline="") as f:
        for source in csv.DictReader(f, delimiter="\t"):
            char = source["汉字"]
            if len(char) != 1 or char in seen:
                raise ValueError(f"附件存在无效或重复汉字：{char!r}")
            seen.add(char)
            if set(source["附件全部编码"].split(" / ")) != codes.get(char, set()):
                raise ValueError(f"{char}: 附件编码与当前字表不一致，请复核")
            # 修正版优先，扩展版只补充全码实际相符的字，不覆盖修正版。
            for prefix, code_column, label in [("修正版", "修正版全码", "修正版"),
                                               ("扩展版", "扩展试验版全码", "扩展试验版")]:
                code = source[code_column]
                roots = source[prefix + "纯字根"]
                if code not in codes[char] or not re.fullmatch("[a-z]{1,4}", code) or roots in ("", "—"):
                    continue
                ids = source[prefix + "原始根ID"]
                suffix_column = "单根双小码键位" if len(ids.split()) == 1 else "识别码键位"
                suffix = source[prefix + suffix_column].replace(" + ", "").replace("—", "")
                row = dict(text=char, code=code, roots=roots, root_ids=ids, suffix=suffix, source=label)
                if derive_code(row, root_keys) != code:
                    raise ValueError(f"{char}: 字根键位及补码无法还原附件全码")
                selected.append(row)
                break
            else:
                unmatched.append({k: (" / ".join(sorted(codes[char])) if k == "当前编码" else source[k])
                                  for k in unmatched_fields})
    if seen != codes.keys():
        raise ValueError("附件未覆盖当前全部单字，请复核来源版本")
    selected.sort(key=lambda r: r["text"])
    unmatched.sort(key=lambda r: r["汉字"])
    data_path = SOURCES / "decomposition.tsv"
    roots_path = SOURCES / "decomposition_roots.json"
    unmatched_path = SOURCES / "decomposition_unmatched.tsv"
    write_tsv(data_path, FIELDS, selected)
    roots_path.write_text(json.dumps(root_keys, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_tsv(unmatched_path, unmatched_fields, unmatched)
    metadata = {
        "description": "用户提供的拆分分析结果；按当前编码筛选并用附件字根键位复算，不代表官方审定拆分。",
        "inputs": [{"filename": p.name, "sha256": digest(p)} for p in [table, workbook]],
        "selection": "修正版全码相符优先；仅用全码相符的扩展试验版补缺；其余不显示拆分。",
        "display": "字根＋全码；保留命名字根，不显示小码和识别码数字。",
        "dictionary_characters": len(codes), "matched_characters": len(selected),
        "matched_gb2312": sum(is_gb2312_han(r["text"]) for r in selected),
        "unmatched_characters": len(unmatched), "selected_variants": dict(Counter(r["source"] for r in selected)),
        "files": {p.name: digest(p) for p in [data_path, roots_path, unmatched_path]},
    }
    (SOURCES / "decomposition-source.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_table(rows, codes, root_keys):
    lines, seen = [], set()
    for row in rows:
        text, code, roots = row["text"], row["code"], row["roots"]
        if len(text) != 1 or text in seen or code not in codes.get(text, set()):
            raise ValueError(f"{text}: 拆分重复或全码已不匹配，请重新核对来源")
        if not roots or roots == "—" or any(c in roots for c in "\t\r\n"):
            raise ValueError(f"{text}: 无效字根文本")
        if not re.fullmatch("[a-z]{1,4}", code) or derive_code(row, root_keys) != code:
            raise ValueError(f"{text}: 拆分与全码不符")
        seen.add(text)
        # OpenCC 用空白分隔多值；HTML 空格占位由拆分过滤器还原。
        compact = "".join(roots.split())
        if "&" in compact:
            raise ValueError(f"{text}: 字根包含保留的 OpenCC 空格转义符")
        lines.append(f"{text}\t〔{compact}&nbsp;·&nbsp;{code}〕\n")
    return "".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-tsv", type=Path)
    parser.add_argument("--root-workbook", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "opencc/lansan_cf.txt")
    args = parser.parse_args()
    if bool(args.import_tsv) != bool(args.root_workbook):
        parser.error("导入时须同时提供 --import-tsv 和 --root-workbook")
    codes = dictionary_codes(SOURCES / "lansan_guanfang.dict.yaml")
    if args.import_tsv:
        import_attachments(args.import_tsv, args.root_workbook, codes)
    metadata = json.loads((SOURCES / "decomposition-source.json").read_text(encoding="utf-8"))
    for name, expected in metadata["files"].items():
        if digest(SOURCES / name) != expected:
            raise ValueError(f"拆分来源校验不符：{name}")
    root_keys = json.loads((SOURCES / "decomposition_roots.json").read_text(encoding="utf-8"))
    with (SOURCES / "decomposition.tsv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    content = render_table(rows, codes, root_keys)
    if len(rows) != metadata["matched_characters"]:
        raise ValueError("拆分条数与来源记录不一致")
    args.output.write_text(content, encoding="utf-8")
    print(json.dumps({"characters": len(rows), "gb2312": metadata["matched_gb2312"],
                      "unmatched": metadata["unmatched_characters"], "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
