#!/usr/bin/env python3
"""把 StudyMate 工作区导成一份自包含、可打开的前端产物落盘。

课件 HTML 用相对路径引用共享层（../../../assets/ 的 learn-theme.css / KaTeX / sayo），
单独拷一个 html 会没样式。本脚本把整棵 <WS>（根 index.html + .learning/）原样拷到
目标目录，相对链接自然不失依；用户用 MT Manager / 浏览器从导出的根主页点进去即可。

用法：python3 scripts/deliver_subject.py <WS> [--dest <目录>] [--name <别名>]
  <WS>   学习工作区根（含 index.html 与 .learning/）
  --dest 落点目录，默认 /storage/emulated/0/Documents/studymate-deliver
  --name 目标子目录名，默认取 <WS> 的 basename + 日期

行为：整树拷贝，排除 _probe / .stage 等中间产物；打印目标路径、体积、打开入口。
不重排链接、不改资源 —— 保真搬运。
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

EXCLUDE = {".stage", "__pycache__", "_probe", ".git", "node_modules", "lab"}


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ws")
    p.add_argument("--dest", default="/storage/emulated/0/Documents/studymate-deliver")
    p.add_argument("--name")
    args = p.parse_args(argv)

    ws = Path(args.ws)
    if not (ws / "index.html").exists():
        raise SystemExit(f"FAIL {ws} 不是已渲染的工作区（没有 index.html），先跑 gen_home.py")

    name = args.name or f"{ws.name}-{datetime.now():%Y%m%d}"
    dest = Path(args.dest) / name

    def ignore(d, names):
        return {n for n in names if n in EXCLUDE}

    shutil.copytree(ws, dest, ignore=ignore, dirs_exist_ok=True,
                    symlinks=True, copy_function=shutil.copy2)
    dest.chmod(0o770) if hasattr(dest, "chmod") else None

    size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    n_subj = sum(1 for d in (dest / ".learning" / "subjects").glob("*")
                 if d.is_dir() and (d / "index.html").exists()) \
        if (dest / ".learning" / "subjects").is_dir() else 0

    print(f"OK   已导出: {dest}")
    print(f"      文件数 {sum(1 for _ in dest.rglob('*') if _.is_file())} · 体积 {size/1024:.0f} KB · 科目主页 {n_subj} 个")
    print(f"      入口: {dest}/index.html")
    print("      打开: MT Manager 或浏览器直接点根主页，课件相对链接不失依。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))