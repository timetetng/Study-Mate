---
name: material-retrieval
description: 本地资料检索协议：怎么查科目的「本地资料检索索引」（reference/INDEX/），把问题映射到资料原文的章节/行号/页码，并溯源回原始出处（数字 md 或扫描书的页）。由总控在课程设计与答疑路径按需加载；扫描资料的 OCR→索引输入来自 resource-scout。
---

# 本地资料检索协议

科目的本地资料被折算成两个层次，检索时都用它：

- **原文**：`<subject_path>/reference/<资料名>.md`（转换/OCR 后可检索的正文）
- **索引**：`<subject_path>/reference/INDEX/`（`build_material_index.py` 产出的检索索引）

**「本地资料」= 数字转 md（digital）或扫描 OCR 后 md（scan）两类**；scan 类还有一页 OCR 管线回填的 `pages.tsv` 可在溯源时换成页码。没有 `INDEX/` 就说明这科还没本地资料，别硬查，走全网检索。

## 怎么加载

- **由总控/讲解在写内容前按需加载**（`skill` 工具按名字读本文件）；它不是角色，不去派子 agent。
- 判定要不要用它：**科目有没有本地资料**——看 `reference/INDEX/library.tsv` 是否存在；存在就说明这科以本地材料为锚，设计大纲和答疑都应该先查本地库，搜不到需要的再补全网。

## 查：问题 → 原文位置

1. **定候选资料**：读 `reference/INDEX/library.tsv`，按科目主题筛出相关的那几份（`kind` 标注了 scan/digital）。
2. **定位章节**：读对应 `<名字>.toc.md`，把问题映射到 1-3 个最贴近的章节（大纲已带行号 `#L<行号>`）。
3. **取正文**：读 `reference/<名字>.md` 的相关行区间（`lines.tsv` 有 `标题\t行号`，按它切到章节边界），读够回答就行，别整本拖进来。
4. **溯源**（引用时必做）：
   - digital → 引用到 `<文件名>` + 章节标题即可，读者能自己定位。
   - scan → 行号经 `<名字>.pages.tsv` 换成**页码**再引用（如「课，§2.1，p.23」）；页码缺失就照实说「OCR 页码待回填」，用**章节标题**兜底，别编页码。
5. 查不到或资料太浅（覆盖不到问题）→ 明说「本地库无此内容」，交给总控走全网补收集，**不拿本地兜底硬凑**。

## 索引格式速查（build_material_index.py 产出）

| 文件 | 内容 | 取来干嘛 |
|---|---|---|
| `library.tsv` | name \t kind \t words \t heads \t lines | 筛候选、看是否 scan |
| `<名字>.toc.md` | 章节大纲 + `#L行号` | 问题→章节映射 |
| `<名字>.lines.tsv` | 标题 \t 源 md 行号 | 切正文行区间 |
| `<名字>.terms.md` | 高频词/标识符 Top60 | 快速判断某资料是否覆盖某概念 |
| `<名字>.pages.tsv` | 扫描资料 行号→页码（OCR 管线回填） | scan 溯源换页 |
| `offsets.tsv` | 各资料在库内字符偏移 | 全库拼接检索 |

## 新本地资料怎么进来（接 resource-scout）

扫描或数字资料进科目都走 `resource-scout` 这一步，产出后执行一次：

```
python3 <root>/scripts/build_material_index.py <subject_path>
```

它按 `reference/_sources.tsv` 记的 `kind` 区分两路：digital 直接索引；scan 再检查 `pages.tsv` 是否被 OCR 管线回填。**跑完报告规模**（资料份数 / scan 份数）。

## 边界

- 只查本科目的 `reference/`，不跨科目检索、不改资源清单。
- 扫码资料的页码诚实：`pages.tsv` 没有真实映射就写章节标题，不编页。
- 本地库是检索入口，不是知识源清单——回答仍以原文为准，讲不清的回原文读。