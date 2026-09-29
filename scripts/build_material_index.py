#!/usr/bin/env python3
"""构建科目的「本地资料检索索引」输出到 reference/INDEX/。

inputs:  <subject_path>/reference/<资料名>.md   （resource-scout 转换/OCR 后的 markdown）
         <subject_path>/reference/_sources.tsv  （可选，资料来源登记：名字<TAB>digital|scan<TAB>页码基数）
outputs: <subject_path>/reference/INDEX/
         library.tsv          资料清单：名字、来源(digital|scan)、页数、字数
         <名字>.toc.md        标题大纲（章节 → 行号）
         <名字>.lines.tsv     标题<TAB>在源 md 的行号
         <名字>.terms.md      高频词/标识符 Top60（供语义检索参考）
         <名字>.pages.tsv     扫描资料的行号→页码映射（由 OCR 管线回传，本脚本只校验保留）
         offsets.tsv          各资料在库内的字符偏移（拼接检索用）

用法：python3 scripts/build_material_index.py <subject_path>
设计对齐：同手机侧 math-ocr 的 build_index.py 产出形态，但只吃已经成 md 的资料，
OCR 那半边（扫描 PDF→可检索文本+pages.tsv）由外部管线回填，本脚本不碰 GPU。
"""

import re
import sys
from collections import Counter
from pathlib import Path

REF = "INDEX"
HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
# 中文词/标识符粗分词：连续 CJK 单字簇、连续 [A-Za-z0-9_]+ 各算一个 token
_TOKEN = re.compile(r'([\u4e00-\u9fff]{2,4})|([A-Za-z][A-Za-z0-9_]{1,})')
_BAD_HEADING = {"目 录", "目录", "contents", "table of contents"}
_SOURCE_LINE = re.compile(r'^(.+?)\t(digital|scan)(?:\t(\d+))?$')


def load_sources(reference_dir: Path) -> dict:
    """name.md -> {kind, page_base}。读 _sources.tsv；缺该行按 digital 兜底。"""
    src_file = reference_dir / "_sources.tsv"
    out = {}
    if src_file.exists():
        for line in src_file.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            m = _SOURCE_LINE.match(line)
            if not m:
                print(f"WARN  _sources.tsv 行无法解析，跳过: {line!r}", file=sys.stderr)
                continue
            name, kind, base = m.groups()
            out[name if name.endswith(".md") else name + ".md"] = {
                "kind": kind,
                "page_base": int(base) if base else 0,
            }
    return out


def tokenize(text: str) -> list:
    toks = _TOKEN.findall(text)
    # 只保留取出的一部分（去掉空匹配），全转小写
    return [(a or b).lower() for a, b in toks]


def build_toc(lines: list) -> list:
    """返回 [(level, title, line_no)]，过滤版式噪音（纯数字卷标、分隔线）。"""
    toc = []
    for i, raw in enumerate(lines):
        m = HEADING.match(raw.strip())
        if not m:
            continue
        level, title = len(m.group(1)), m.group(2).strip()
        title = title.rstrip("#").strip()
        if not title or title.lower() in _BAD_HEADING:
            continue
        toc.append((level, title, i + 1))  # 1-based 行号
    return toc


def count_words(text: str) -> int:
    return sum(len(t) for t in tokenize(text)) or 0


def index_one(md_file: Path, sources: dict, index_dir: Path) -> dict:
    text = md_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    toc = build_toc(lines)
    name = md_file.name
    kind = sources.get(name, {}).get("kind", "digital")
    page_base = sources.get(name, {}).get("page_base", 0)

    # toc.md
    (index_dir / f"{name}.toc.md").write_text(
        f"# {name} 大纲（{kind}）\n\n"
        + "".join(f"{'  ' * (level - 1)}- [{title}](#L{ln})\n" for level, title, ln in toc),
        encoding="utf-8",
    )
    # lines.tsv
    (index_dir / f"{name}.lines.tsv").write_text(
        "\n".join(f"{title}\t{ln}" for _, title, ln in toc), encoding="utf-8",
    )
    # terms.md
    freq = Counter(tokenize(text))
    top = freq.most_common(60)
    (index_dir / f"{name}.terms.md").write_text(
        f"# {name} 高频词\n\n" + "".join(f"{w}\t{c}\n" for w, c in top), encoding="utf-8",
    )
    # pages.tsv：扫描资料的 行号→页码 由 OCR 管线回传；digital 无页概念。
    if kind == "scan":
        pfile = index_dir / f"{name}.pages.tsv"
        if not pfile.exists():
            # 管线没回传时给个按平均行密的占位，标注待回填
            n_lines = len(lines)
            n_pages = max(1, n_lines // 40)
            pfile.write_text(
                f"# 待 OCR 管线回填真实页码映射；当前按 {n_lines} 行 / ~{n_pages} 页占位\n",
                encoding="utf-8",
            )
    return {
        "name": name, "kind": kind, "words": count_words(text),
        "char_len": len(text), "n_lines": len(lines), "n_heads": len(toc),
    }


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    subject = Path(argv[0])
    reference = subject / "reference"
    if not reference.is_dir():
        raise SystemExit(f"FAIL 没有 reference/ 目录: {reference}")
    index_dir = reference / REF
    index_dir.mkdir(parents=True, exist_ok=True)

    sources = load_sources(reference)
    rows, offset = [], 0
    for md in sorted(reference.glob("*.md")):
        if md.name == "_sources.tsv":
            continue
        meta = index_one(md, sources, index_dir)
        rows.append(meta)
        offset += meta["char_len"]

    # library.tsv
    (index_dir / "library.tsv").write_text(
        "name\tkind\twords\theads\tlines\n"
        + "\n".join(
            f"{m['name']}\t{m['kind']}\t{m['words']}\t{m['n_heads']}\t{m['n_lines']}"
            for m in rows
        ),
        encoding="utf-8",
    )
    # offsets.tsv
    acc, off_lines = 0, []
    for m in rows:
        off_lines.append(f"{m['name']}\t{acc}\t{acc + m['char_len']}")
        acc += m["char_len"]
    (index_dir / "offsets.tsv").write_text("\n".join(off_lines), encoding="utf-8")

    scan_notes = [f"{m['name']}" for m in rows if m["kind"] == "scan"]
    print(f"OK   索引已建: {index_dir}")
    print(f"      资料 {len(rows)} 份, 扫描 {len(scan_notes) or 0} 份, 总字符 {acc}")
    for m in rows:
        print(f"      {m['name']:<28} {m['kind']:<7} {m['words']} 词 / {m['n_heads']} 节")
    if scan_notes:
        print("NOTE  以下扫描资料页码映射待 OCR 管线回填(见 pages.tsv): " + ", ".join(scan_notes))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))